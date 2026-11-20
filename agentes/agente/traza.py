"""Observabilidad: convierte las trazas JSONL en un diagrama de secuencia (Mermaid) y en métricas.

Adaptaciones a SismoReporta (Lab 10, E2):
- Recibe la carpeta de un issue y una variante: python agentes/agente/traza.py agentes/trazas/issue01/unico
- Incluye el agente único ("agente") y solo dibuja los participantes que aparecen.
- Las métricas incluyen pasos, decisiones rechazadas por el contrato, acciones bloqueadas por la
  política y contexto final, y se guardan en metricas.json junto al diagrama.
"""
import json, collections, pathlib, sys

ORDEN = ["planificador", "agente", "ejecutor", "revisor", "ejecutor_r2", "revisor_r2", "ejecutor_r3", "revisor_r3"]
NOMBRES = {"planificador": ("PL", "Planificador"), "agente": ("AG", "Agente único"),
           "ejecutor": ("EJ", "Ejecutor (actor)"), "revisor": ("RV", "Revisor (crítico)")}


def cargar(carpeta="trazas"):
    eventos = []
    for n in ORDEN:
        f = pathlib.Path(carpeta) / f"{n}.jsonl"
        if f.exists():
            ronda = int(n.split("_r")[1]) if "_r" in n else 1
            eventos += [dict(json.loads(l), ronda=ronda) for l in open(f, encoding="utf-8")]
    return eventos


def _texto(s, n=45):
    return str(s).replace(";", ",").replace("#", "N.").replace("\n", " ")[:n]


def resumir(e) -> str:
    obs, acc, args = e["observacion"], e["accion"], e["args"]
    if acc == "leer_archivo": return f"contenido de {str(args.get('ruta', '')).split('/')[-1]}"
    if acc == "buscar": return "sin resultados" if "sin resultados" in obs else f"{len(obs.splitlines())} coincidencia(s)"
    if acc == "ver_cambios": return f"diff de {len(obs.splitlines())} líneas"
    if acc == "listar_archivos": return f"{len(obs.splitlines())} archivos"
    if acc == "editar_archivo" and obs.startswith("OK"): return "OK, archivo modificado"
    if acc == "ejecutar_pruebas": return _texto((obs.strip().splitlines() or [""])[0], 40)
    return _texto((obs.strip().splitlines() or [""])[-1], 40)


def a_mermaid(eventos) -> str:
    presentes = [a for a in NOMBRES if any(e["agente"] == a for e in eventos)]
    l = ["sequenceDiagram", "    autonumber", "    actor U as Humano"]
    l += [f"    participant {NOMBRES[a][0]} as {NOMBRES[a][1]}" for a in presentes]
    l += ["    participant P as Política", "    participant H as Herramientas"]
    ronda_actual = 1
    for e in eventos:
        a = NOMBRES[e["agente"]][0]
        if e["ronda"] != ronda_actual:
            ronda_actual = e["ronda"]
            l.append(f"    Note over EJ,RV: Ronda {ronda_actual} del bucle actor-crítico")
        if e["tipo"] == "objetivo":
            if a in ("PL", "AG"):
                origen, txt = "U", "objetivo"
            elif a == "EJ":
                origen, txt = ("PL", "plan") if e["ronda"] == 1 else ("RV", "cambios solicitados")
            else:
                origen, txt = "EJ", "resumen + diff"
            l.append(f"    {origen}->>{a}: {txt}")
        elif e["tipo"] == "accion":
            if e["estado"] == "CONTRATO_INVALIDO":
                l.append(f"    Note right of {a}: decisión rechazada por el contrato")
            elif e["bloqueada"]:
                motivo = "LÍMITE DE PASOS" if e["estado"] == "LIMITE_ALCANZADO" else "BLOQUEADO"
                l += [f"    {a}-xP: {e['accion']}", f"    P--x{a}: {motivo}"]
            else:
                l += [f"    {a}->>H: {e['accion']}", f"    H-->>{a}: {resumir(e)}"]
        elif e["tipo"] == "final":
            if a == "RV" and not e["texto"].startswith("CAMBIOS"):
                l.append(f"    RV-->>U: {_texto(e['texto'].split('.')[0])}")
            elif a == "AG":
                l.append(f"    AG-->>U: {_texto(e['texto'])}")
        elif e["tipo"] == "aprobacion":
            l += [f"    {a}->>U: ¿aprobar edición de {str(e['ruta']).split('/')[-1]}?",
                  f"    U-->>{a}: {'s (aprueba)' if e['respuesta'] == 's' else 'n (rechaza)'}"]
        elif e["tipo"] == "limite":
            l.append(f"    Note right of {a}: LÍMITE DE PASOS ALCANZADO")
    return "\n".join(l)


def metricas(eventos) -> dict:
    m = collections.defaultdict(collections.Counter)
    for e in eventos:
        clave = e["agente"] + ("" if e["ronda"] == 1 else f"_r{e['ronda']}")
        if e["tipo"] == "accion":
            if e["estado"] == "CONTRATO_INVALIDO":
                m[clave]["rechazadas_contrato"] += 1
            else:
                m[clave]["bloqueadas" if e["bloqueada"] else "permitidas"] += 1
                m[clave][("bloqueada:" if e["bloqueada"] else "herramienta:") + e["accion"]] += 1
        elif e["tipo"] == "aprobacion":
            m[clave]["aprobaciones_" + e["respuesta"]] += 1
        elif e["tipo"] == "fin":
            m[clave]["pasos"] = e["pasos"]
            m[clave]["contexto_caracteres"] = e["contexto_caracteres"]
            m[clave]["estado_final"] = e["estado"]
    return {k: dict(v) for k, v in m.items()}


if __name__ == "__main__":
    carpeta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "trazas")
    ev = cargar(carpeta)
    (carpeta / "trayectoria.mmd").write_text(a_mermaid(ev), encoding="utf-8")
    m = metricas(ev)
    (carpeta / "metricas.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=1))
