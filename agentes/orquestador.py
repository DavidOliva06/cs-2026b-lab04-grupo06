"""Ejecuta los agentes de SismoReporta sobre un issue (Lab 10).

Uso, desde la raíz del repositorio:
    python agentes/orquestador.py --issue 1 --variante unico --modelo interactivo   # E2: graba
    python agentes/orquestador.py --issue 1 --variante unico --modelo grabado       # reproduce

- Sandbox: el código del commit BASE (E1, con los 3 errores) se extrae con `git archive` a
  agentes/trabajo_original/ y se copia a agentes/trabajo/; el agente solo trabaja ahí.
- Decisiones: agentes/trayectorias/issue0N/<variante>/<agente>.json
- Trazas:     agentes/trazas/issue0N/<variante>/<agente>.jsonl
"""
import argparse, io, json, pathlib, shutil, subprocess, sys, zipfile

AGENTES = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AGENTES))
from agente.herramientas import Herramientas  # noqa: E402
from agente.modelos import ModeloGrabado, ModeloInteractivo  # noqa: E402
from agente.nucleo import Agente  # noqa: E402
from agente.politica import Politica  # noqa: E402
from agente.protocolo import mensaje_inicial  # noqa: E402

REPO = AGENTES.parent
BASE = "086ba7f"                       # commit "E1: lienzo de diseño y tareas del agente"
CONTENIDO = ["src", "tests", "fitness", "prompts", "issues", "pytest.ini", ".importlinter"]
ORIGINAL, TRABAJO = AGENTES / "trabajo_original", AGENTES / "trabajo"


def preparar_sandbox() -> Herramientas:
    if not ORIGINAL.exists():
        zip_bytes = subprocess.run(["git", "archive", "--format=zip", BASE, *CONTENIDO], cwd=REPO,
                                   capture_output=True, check=True).stdout
        zipfile.ZipFile(io.BytesIO(zip_bytes)).extractall(ORIGINAL)
    shutil.rmtree(TRABAJO, ignore_errors=True)        # cada ejecución parte del estado original
    shutil.copytree(ORIGINAL, TRABAJO)
    return Herramientas(TRABAJO, ORIGINAL)


def modelo(args, carpeta: pathlib.Path, nombre: str):
    archivo = AGENTES / "trayectorias" / carpeta / f"{nombre}.json"
    if args.modelo == "grabado":
        return ModeloGrabado(archivo)
    print(f"\n######## {carpeta.as_posix()} / {nombre}: abra un chat NUEVO en su asistente de IA ########")
    return ModeloInteractivo(archivo, turno=AGENTES / "turno.txt")


def contexto(agente) -> int:
    return len(json.dumps(agente.historial, ensure_ascii=False))


def unico(args, h: Herramientas, carpeta: pathlib.Path):
    politica = Politica(herramientas_permitidas={"listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas",
                                                 "editar_archivo", "ver_cambios", "ejecutar_comando"}, max_pasos=15)
    tarea = (f"Resuelve el issue descrito en issues/ISSUE-{args.issue:02d}.md. Reproduce el fallo con su "
             "prueba, localiza la causa, corrígela sin tocar las pruebas y verifica que todas las pruebas "
             "del issue pasen. Termina con un resumen: causa, archivos cambiados y resultado de las pruebas.")
    agente = Agente("agente", modelo(args, carpeta, "agente"), h, politica,
                    mensaje_inicial("ÚNICO (lee, edita y verifica)", tarea, h.catalogo(), politica.max_pasos),
                    AGENTES / "trazas" / carpeta / "agente.jsonl")
    resumen = agente.ejecutar()
    print(f"\nAGENTE: {resumen}\n[agente] contexto final: {contexto(agente)} caracteres (~{contexto(agente) // 4} tokens)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--issue", type=int, choices=[1, 2, 3], required=True)
    p.add_argument("--variante", choices=["unico"], default="unico")
    p.add_argument("--modelo", choices=["interactivo", "grabado"], default="grabado")
    args = p.parse_args()
    carpeta = pathlib.Path(f"issue{args.issue:02d}") / args.variante
    h = preparar_sandbox()
    {"unico": unico}[args.variante](args, h, carpeta)
    print("\nCambios del agente (ver_cambios):\n" + h.ver_cambios())
    print("\nDecisión final: HUMANO (aprobar o rechazar el Pull Request).")


if __name__ == "__main__":
    main()
