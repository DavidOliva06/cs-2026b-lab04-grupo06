"""Guardrails: qué puede hacer el agente, cuántas veces y con qué aprobación.

Adaptación a SismoReporta (Lab 10, E2): la ruta protegida se compara ya normalizada, así que
"tests\\x.py", "./tests/x.py" o "src/../tests/x.py" también quedan bloqueadas.
"""
import posixpath, re
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Decision:
    permitido: bool
    motivo: str = ""
    aprobacion: Optional[str] = None                # E6: "s" o "n" si la edición pasó por el humano


@dataclass
class Politica:
    herramientas_permitidas: set = field(default_factory=lambda: {
        "listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas", "editar_archivo", "ejecutar_comando"})
    comandos_permitidos: tuple = (r"^python -m pytest\b", r"^radon cc\b", r"^lint-imports\b", r"^git (status|diff)\b")
    rutas_protegidas: tuple = ("tests/",)          # el agente no puede "arreglar" las pruebas para que pasen
    max_pasos: int = 15
    # E6: en el original era un atributo de clase y no se podía pasar al crear la política.
    aprobar_edicion: Optional[Callable[[dict], bool]] = None   # humano en el circuito (human-in-the-loop)

    def evaluar(self, accion: str, args: dict, paso: int) -> Decision:
        if paso > self.max_pasos:
            return Decision(False, f"Se alcanzó el máximo de {self.max_pasos} pasos")
        if accion not in self.herramientas_permitidas:
            return Decision(False, f"Herramienta no permitida: {accion}")
        if accion == "ejecutar_comando":
            cmd = str(args.get("comando", ""))
            if re.search(r"[;&|`$<>\n\r]", cmd):          # E3: sin encadenar, redirigir ni sustituir comandos
                return Decision(False, f"Comando con operadores de shell no permitidos: {cmd!r}")
            if not any(re.search(p, cmd) for p in self.comandos_permitidos):
                return Decision(False, f"Comando fuera de la lista permitida: {cmd!r}")
        if accion == "editar_archivo":
            ruta = posixpath.normpath(str(args.get("ruta", "")).replace("\\", "/")).lstrip("/")
            if (ruta + "/").startswith(self.rutas_protegidas):
                return Decision(False, f"Ruta protegida: {ruta}")
            if self.aprobar_edicion:                                  # ESPERANDO_APROBACION
                if not self.aprobar_edicion(args):
                    return Decision(False, "El revisor humano rechazó la edición", aprobacion="n")
                return Decision(True, aprobacion="s")
        return Decision(True)
