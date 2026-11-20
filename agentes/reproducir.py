"""Reproduce todas las trayectorias grabadas y verifica que cada una resuelve su issue (Lab 10).

Uso, desde la raíz del repositorio:  python agentes/reproducir.py
Para cada ejecución grabada: corre el orquestador con ModeloGrabado (las herramientas se ejecutan
de verdad en el sandbox), ejecuta la prueba del issue en el sandbox resultante y regenera la traza,
el diagrama Mermaid y las métricas. Termina con código 1 si alguna no resuelve su issue.
"""
import pathlib, subprocess, sys

AGENTES = pathlib.Path(__file__).resolve().parent
REPO = AGENTES.parent
EJECUCIONES = [  # (issue, carpeta, argumentos del orquestador, ¿debe resolver el issue?)
    (1, "unico", ["--variante", "unico"], True),
    # El humano rechazó a propósito la única edición (prueba de E6): el issue queda sin resolver.
    (1, "unico-extendidas", ["--variante", "unico", "--herramientas", "extendidas", "--aprobacion",
                             "--etiqueta", "unico-extendidas"], False),
    (2, "unico", ["--variante", "unico", "--aprobacion"], True),
    (2, "multi", ["--variante", "multi", "--aprobacion"], True),
    (3, "unico", ["--variante", "unico", "--herramientas", "extendidas", "--aprobacion"], True),
]


def main() -> int:
    fallas = 0
    for issue, carpeta, extra, resuelve in EJECUCIONES:
        if not (AGENTES / "trayectorias" / f"issue{issue:02d}" / carpeta).exists():
            print(f"issue{issue:02d}/{carpeta}: sin trayectoria grabada (se omite)")
            continue
        r = subprocess.run([sys.executable, str(AGENTES / "orquestador.py"), "--issue", str(issue), *extra,
                            "--modelo", "grabado"], cwd=REPO, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        prueba = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                 f"tests/test_issue_{issue:02d}.py"], cwd=AGENTES / "trabajo",
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(AGENTES / "agente" / "traza.py"),
                        str(AGENTES / "trazas" / f"issue{issue:02d}" / carpeta)], capture_output=True)
        resumen = (prueba.stdout.strip().splitlines() or ["(sin salida)"])[-1]
        ok = r.returncode == 0 and (prueba.returncode == 0) == resuelve
        fallas += not ok
        print(f"issue{issue:02d}/{carpeta}: {'OK' if ok else 'FALLA'} - prueba del issue: {resumen}"
              f" (esperado: {'resuelto' if resuelve else 'sin resolver'})"
              + ("" if r.returncode == 0 else f" - orquestador: {r.stderr.strip().splitlines()[-1:]}"))
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
