"""Humano en el circuito (Lab 10, E6): un integrante aprueba o rechaza cada edición del ejecutor.

- Modo interactivo: muestra el diff de la edición propuesta y pide "s" o "n"; cualquier otra
  respuesta se rechaza y se vuelve a preguntar (patrón "validar la entrada humana", Tabla 8).
- Modo grabado: reproduce las respuestas grabadas, para que la ejecución sea reproducible.
Cada respuesta se graba en trayectorias/.../aprobaciones_<agente>.json.
"""
import difflib, json, pathlib


class AprobacionHumana:
    def __init__(self, archivo, modo="interactivo", entrada=input, salida=print):
        self.archivo, self.modo = pathlib.Path(archivo), modo
        self._input, self._print = entrada, salida
        self.respuestas = json.loads(self.archivo.read_text(encoding="utf-8")) if modo == "grabado" else []
        self._i = 0

    def _preguntar(self, args) -> tuple[str, int]:
        antes, despues = str(args.get("antes", "")), str(args.get("despues", ""))
        diff = difflib.unified_diff(antes.splitlines(), despues.splitlines(), "antes", "despues", lineterm="", n=2)
        self._print(f"\n===== APROBACIÓN HUMANA: el agente quiere editar {args.get('ruta')} =====")
        self._print("\n".join(list(diff)[2:]) or "(sin diferencias visibles)")
        invalidas = 0
        while True:
            r = self._input("¿Aprueba la edición? (s/n): ").strip().lower()
            if r in ("s", "n"):
                return r, invalidas
            invalidas += 1
            self._print("Respuesta no válida: escriba solo s o n.")

    def __call__(self, args) -> bool:
        if self.modo == "grabado":
            if self._i >= len(self.respuestas):
                raise RuntimeError(f"{self.archivo} no tiene más aprobaciones grabadas")
            r = self.respuestas[self._i]["respuesta"]
            self._i += 1
            return r == "s"
        r, invalidas = self._preguntar(args)
        self.respuestas.append({"ruta": args.get("ruta"), "respuesta": r, "respuestas_invalidas": invalidas})
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self.archivo.write_text(json.dumps(self.respuestas, ensure_ascii=False, indent=1), encoding="utf-8")
        return r == "s"
