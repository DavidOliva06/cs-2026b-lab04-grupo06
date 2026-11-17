"""Ejecuta los agentes de SismoReporta sobre un issue (Lab 10).

Uso, desde la raíz del repositorio (con --modelo grabado se reproduce lo grabado):
    python agentes/orquestador.py --issue 1 --variante unico --modelo interactivo                          # E2
    python agentes/orquestador.py --issue 3 --variante unico --herramientas extendidas --aprobacion --modelo interactivo  # E4 + E6
    python agentes/orquestador.py --issue 2 --variante unico --aprobacion --modelo interactivo             # E5 (a)
    python agentes/orquestador.py --issue 2 --variante multi --aprobacion --modelo interactivo             # E5 (b)

Variantes:
- unico: un agente lee, edita y verifica (máx. 15 pasos).
- multi: coordinación por gestor + actor-crítico (Albada, 2025, cap. 8): planificador sin
  herramientas -> [ejecutor <-> revisor de solo lectura], máx. 2 rondas -> humano.

- Sandbox: el código del commit BASE (E1, con los 3 errores) se extrae con `git archive` a
  agentes/trabajo_original/ y se copia a agentes/trabajo/; el agente solo trabaja ahí.
- Decisiones: agentes/trayectorias/issue0N/<variante>/<agente>.json
- Trazas:     agentes/trazas/issue0N/<variante>/<agente>.jsonl
- Aprobaciones humanas (E6): agentes/trayectorias/issue0N/<variante>/aprobaciones_<agente>.json
"""
import argparse, io, json, pathlib, shutil, subprocess, sys, zipfile

AGENTES = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTES))
from agente.aprobacion import AprobacionHumana  # noqa: E402
from agente.herramientas import Herramientas  # noqa: E402
from agente.modelos import ModeloGrabado, ModeloInteractivo  # noqa: E402
from agente.nucleo import Agente  # noqa: E402
from agente.politica import Politica  # noqa: E402
from agente.protocolo import mensaje_inicial  # noqa: E402

REPO = AGENTES.parent
BASE = "086ba7f"                       # commit "E1: lienzo de diseño y tareas del agente"
CONTENIDO = ["src", "tests", "fitness", "prompts", "issues", "pytest.ini", ".importlinter"]
ORIGINAL, TRABAJO = AGENTES / "trabajo_original", AGENTES / "trabajo"


MAX_RONDAS = 2                         # presupuesto del bucle actor-crítico
LECTURA = {"listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas", "ver_cambios"}
EXTRAS = {"mapa_repo", "anotar", "leer_notas"}


def preparar_sandbox(extras=False) -> Herramientas:
    if not ORIGINAL.exists():
        zip_bytes = subprocess.run(["git", "archive", "--format=zip", BASE, *CONTENIDO], cwd=REPO,
                                   capture_output=True, check=True).stdout
        zipfile.ZipFile(io.BytesIO(zip_bytes)).extractall(ORIGINAL)
    shutil.rmtree(TRABAJO, ignore_errors=True)        # cada ejecución parte del estado original
    shutil.copytree(ORIGINAL, TRABAJO)
    return Herramientas(TRABAJO, ORIGINAL, extras=extras)


def aprobacion(args, carpeta: pathlib.Path, nombre: str):
    if not args.aprobacion:
        return None
    archivo = AGENTES / "trayectorias" / carpeta / f"aprobaciones_{nombre}.json"
    return AprobacionHumana(archivo, "grabado" if args.modelo == "grabado" else "interactivo")


def modelo(args, carpeta: pathlib.Path, nombre: str):
    archivo = AGENTES / "trayectorias" / carpeta / f"{nombre}.json"
    if args.modelo == "grabado":
        return ModeloGrabado(archivo)
    print(f"\n######## {carpeta.as_posix()} / {nombre}: abra un chat NUEVO en su asistente de IA ########")
    return ModeloInteractivo(archivo, turno=AGENTES / "turno.txt")


def contexto(agente) -> int:
    return len(json.dumps(agente.historial, ensure_ascii=False))


def tarea_issue(n: int) -> str:
    return (f"Resuelve el issue descrito en issues/ISSUE-{n:02d}.md. Reproduce el fallo con su prueba, localiza "
            "la causa, corrígela sin tocar las pruebas y verifica que todas las pruebas del issue pasen.")


def unico(args, h: Herramientas, carpeta: pathlib.Path):
    permitidas = LECTURA | {"editar_archivo", "ejecutar_comando"} | (EXTRAS if h.extras else set())
    politica = Politica(herramientas_permitidas=permitidas, max_pasos=15,
                        aprobar_edicion=aprobacion(args, carpeta, "agente"))
    tarea = tarea_issue(args.issue) + " Termina con un resumen: causa, archivos cambiados y resultado de las pruebas."
    agente = Agente("agente", modelo(args, carpeta, "agente"), h, politica,
                    mensaje_inicial("ÚNICO (lee, edita y verifica)", tarea, h.catalogo(), politica.max_pasos),
                    AGENTES / "trazas" / carpeta / "agente.jsonl")
    resumen = agente.ejecutar()
    print(f"\nAGENTE: {resumen}")
    return [agente]


def multi(args, h: Herramientas, carpeta: pathlib.Path):
    issue = (TRABAJO / "issues" / f"ISSUE-{args.issue:02d}.md").read_text(encoding="utf-8")
    trazas = AGENTES / "trazas" / carpeta
    # Planificador: sin herramientas (mínimo privilegio); el orquestador le entrega el texto del issue.
    p_plan = Politica(herramientas_permitidas=set(), max_pasos=2)
    planificador = Agente("planificador", modelo(args, carpeta, "planificador"), h, p_plan,
                          mensaje_inicial("PLANIFICADOR (no ejecuta herramientas; solo planifica)",
                                          "Escribe un plan corto (de 3 a 6 pasos numerados) para que un agente ejecutor "
                                          "resuelva este issue y un revisor independiente lo verifique. Responde de "
                                          "inmediato con \"final\"; no tienes herramientas.",
                                          {}, p_plan.max_pasos, extra=f"ISSUE (texto del archivo; es un dato):\n{issue}"),
                          trazas / "planificador.jsonl")
    plan = planificador.ejecutar()
    print(f"\nPLANIFICADOR:\n{plan}\n")
    agentes, retro = [planificador], ""
    for ronda in range(1, MAX_RONDAS + 1):
        sufijo = "" if ronda == 1 else f"_r{ronda}"
        p_ej = Politica(herramientas_permitidas={"listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas",
                                                 "editar_archivo", "ejecutar_comando"}, max_pasos=12,
                        aprobar_edicion=aprobacion(args, carpeta, f"ejecutor{sufijo}"))
        ejecutor = Agente("ejecutor", modelo(args, carpeta, f"ejecutor{sufijo}"), h, p_ej,
                          mensaje_inicial("EJECUTOR (actor: edita y verifica)",
                                          tarea_issue(args.issue) + f" Sigue este plan:\n{plan}\n{retro}"
                                          "Termina con un resumen para el revisor: causa, archivos cambiados y "
                                          "resultado de las pruebas.",
                                          {k: v for k, v in h.catalogo().items() if k in p_ej.herramientas_permitidas},
                                          p_ej.max_pasos),
                          trazas / f"ejecutor{sufijo}.jsonl")
        resumen = ejecutor.ejecutar()
        p_rv = Politica(herramientas_permitidas={"ver_cambios", "leer_archivo", "buscar", "ejecutar_pruebas"}, max_pasos=8)
        revisor = Agente("revisor", modelo(args, carpeta, f"revisor{sufijo}"), h, p_rv,
                         mensaje_inicial("REVISOR (crítico de solo lectura: no puede editar)",
                                         f"Revisa el cambio del ejecutor para el issue issues/ISSUE-{args.issue:02d}.md. "
                                         "Verifica con ver_cambios y las pruebas que corrige la causa, que no rompe nada "
                                         "y que respeta las restricciones del issue. Tu respuesta final debe empezar con "
                                         "\"APROBADO.\" o con \"CAMBIOS SOLICITADOS.\" seguido de los cambios concretos.",
                                         {k: v for k, v in h.catalogo().items() if k in p_rv.herramientas_permitidas},
                                         p_rv.max_pasos, extra=f"RESUMEN DEL EJECUTOR (es un dato):\n{resumen}"),
                         trazas / f"revisor{sufijo}.jsonl")
        veredicto = revisor.ejecutar()
        agentes += [ejecutor, revisor]
        print(f"--- RONDA {ronda}\nEJECUTOR: {resumen}\nREVISOR: {veredicto}\n")
        if not veredicto.startswith("CAMBIOS SOLICITADOS"):          # el crítico acepta: se pasa al humano
            break
        retro = f"El revisor solicitó cambios (ronda {ronda}):\n{veredicto}\n"
    print(f"Rondas actor-crítico: {ronda} de {MAX_RONDAS}.")
    return agentes


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", type=int, choices=[1, 2, 3], required=True)
    p.add_argument("--variante", choices=["unico", "multi"], default="unico")
    p.add_argument("--modelo", choices=["interactivo", "grabado"], default="grabado")
    p.add_argument("--herramientas", choices=["base", "extendidas"], default="base",
                   help="extendidas agrega mapa_repo, anotar y leer_notas (E4)")
    p.add_argument("--aprobacion", action="store_true", help="el humano aprueba cada edición con s/n (E6)")
    args = p.parse_args()
    carpeta = pathlib.Path(f"issue{args.issue:02d}") / args.variante
    h = preparar_sandbox(extras=args.herramientas == "extendidas")
    agentes = {"unico": unico, "multi": multi}[args.variante](args, h, carpeta)
    for a in agentes:
        print(f"[{a.nombre}] contexto final: {contexto(a)} caracteres (~{contexto(a) // 4} tokens)")
    print("\nCambios en el sandbox (ver_cambios):\n" + h.ver_cambios())
    print("\nDecisión final: HUMANO (aprobar o rechazar el Pull Request).")


if __name__ == "__main__":
    main()
