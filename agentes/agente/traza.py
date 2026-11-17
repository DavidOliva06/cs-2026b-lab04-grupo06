"""Observabilidad: convierte las trazas JSONL en un diagrama de secuencia (Mermaid) y en métricas."""
import json, collections, pathlib

ORDEN = ["planificador", "ejecutor", "revisor", "ejecutor_r2", "revisor_r2", "ejecutor_r3", "revisor_r3"]

def cargar(carpeta="trazas"):
    eventos = []
    for n in ORDEN:
        f = pathlib.Path(carpeta) / f"{n}.jsonl"
        if f.exists():
            ronda = int(n.split("_r")[1]) if "_r" in n else 1
            eventos += [dict(json.loads(l), ronda=ronda) for l in open(f, encoding="utf-8")]
    return eventos

def resumir(e) -> str:
    obs, acc, args = e["observacion"], e["accion"], e["args"]
    if acc == "leer_archivo": return f"contenido de {args['ruta'].split('/')[-1]}"
    if acc == "buscar": return "sin resultados" if "sin resultados" in obs else f"{len(obs.splitlines())} coincidencia(s)"
    if acc == "ver_cambios": return f"diff de {len(obs.splitlines())} líneas"
    if acc == "ejecutar_comando" and args.get("comando", "").startswith("radon"): return "complejidad A"
    if acc == "editar_archivo" and obs.startswith("OK"): return "OK, archivo modificado"
    return (obs.strip().splitlines() or [""])[-1].replace(";", ",").replace("#", "N.")[:40]

def a_mermaid(eventos) -> str:
    alias = {"planificador": "PL", "ejecutor": "EJ", "revisor": "RV"}
    l = ["sequenceDiagram", "    autonumber", "    actor U as Humano", "    participant PL as Planificador",
         "    participant EJ as Ejecutor (actor)", "    participant RV as Revisor (crítico)",
         "    participant P as Política", "    participant H as Herramientas"]
    ronda_actual = 1
    for e in eventos:
        a = alias[e["agente"]]
        if e["ronda"] != ronda_actual:
            ronda_actual = e["ronda"]
            l.append(f"    Note over EJ,RV: Ronda {ronda_actual} del bucle actor-crítico")
        if e["tipo"] == "objetivo":
            origen = "U" if a == "PL" else ("PL" if a == "EJ" and e["ronda"] == 1 else ("RV" if a == "EJ" else "EJ"))
            l.append(f"    {origen}->>{a}: " + ("objetivo" if a == "PL" else "plan" if origen == "PL" else "cambios solicitados" if origen == "RV" else "resumen + diff"))
        elif e["tipo"] == "accion":
            if e["bloqueada"]:
                l += [f"    {a}-xP: {e['accion']}", f"    P--x{a}: BLOQUEADO"]
            else:
                l += [f"    {a}->>H: {e['accion']}", f"    H-->>{a}: {resumir(e)}"]
        elif e["tipo"] == "final":
            if a == "RV" and not e["texto"].startswith("CAMBIOS"):
                l.append(f"    RV-->>U: {e['texto'].split('.')[0]}")
    return "\n".join(l)

def metricas(eventos) -> dict:
    m = collections.defaultdict(collections.Counter)
    for e in eventos:
        if e["tipo"] == "accion":
            m[e["agente"]]["bloqueadas" if e["bloqueada"] else "permitidas"] += 1
            m[e["agente"]][e["accion"]] += 1
    return {k: dict(v) for k, v in m.items()}

if __name__ == "__main__":
    ev = cargar()
    pathlib.Path("trazas/trayectoria.mmd").write_text(a_mermaid(ev), encoding="utf-8")
    print(json.dumps(metricas(ev), ensure_ascii=False, indent=1))
