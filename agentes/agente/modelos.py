"""El 'cerebro' del agente es intercambiable (patrón Strategy del Lab 07).

Protocolo: el modelo recibe el historial y devuelve un JSON con
  {"pensamiento": "...", "accion": "<herramienta>", "args": {...}}   o
  {"pensamiento": "...", "final": "<respuesta para el usuario>"}

Adaptaciones a SismoReporta (Lab 10, E2):
- ModeloInteractivo acepta una respuesta de varias líneas (se termina con una línea vacía), copia
  el texto al portapapeles cuando puede y lo deja en agentes/turno.txt.
- Si la respuesta no es JSON, NO se corrige a mano: se graba tal cual y el contrato la rechaza
  (guía, E2.3). ModeloGrabado la reproduce igual.
"""
import json, pathlib, platform, shutil, subprocess


class ModeloGrabado:
    """Reproduce decisiones grabadas de un asistente de IA (trayectoria JSON).
    Las herramientas se ejecutan de verdad; solo las decisiones vienen de la grabación."""
    def __init__(self, archivo):
        self.archivo = archivo
        self._decisiones = json.load(open(archivo, encoding="utf-8"))
        self._i = 0

    def decidir(self, historial: list):
        if self._i >= len(self._decisiones):
            raise RuntimeError(f"La trayectoria {self.archivo} no tiene más decisiones ({self._i} usadas)")
        d = self._decisiones[self._i]
        self._i += 1
        return d


class ModeloAnthropic:
    """Proveedor real (opcional). Requiere ANTHROPIC_API_KEY y el paquete anthropic."""
    def __init__(self, modelo="claude-sonnet-4-5", sistema=""):
        import anthropic
        self._cliente, self._modelo, self._sistema = anthropic.Anthropic(), modelo, sistema

    def decidir(self, historial: list) -> dict:
        r = self._cliente.messages.create(model=self._modelo, max_tokens=1024, system=self._sistema,
                                          messages=historial, temperature=0)
        return json.loads(r.content[0].text)


def copiar_al_portapapeles(texto: str) -> bool:
    """Intenta copiar al portapapeles del sistema; devuelve False si no hay cómo."""
    try:
        sistema = platform.system()
        if sistema == "Windows":
            subprocess.run(["clip"], input=texto.encode("utf-16"), check=True)
        elif sistema == "Darwin":
            subprocess.run(["pbcopy"], input=texto.encode("utf-8"), check=True)
        elif shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=texto.encode("utf-8"), check=True)
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=texto.encode("utf-8"), check=True)
        else:
            return False
        return True
    except Exception:
        return False


class ModeloInteractivo:
    """Sin clave de API: el estudiante copia el contexto a su asistente de IA (Claude.ai, ChatGPT,
    Gemini, Copilot Chat), pega aquí la respuesta JSON y la decisión se graba para reproducirla.
    Use un chat NUEVO por agente: el primer mensaje trae el protocolo y el objetivo, y los
    siguientes solo la observación del paso anterior."""
    def __init__(self, grabar_en, turno="turno.txt", entrada=input):
        self._archivo, self._decisiones = grabar_en, []
        self._turno, self._input = pathlib.Path(turno), entrada
        pathlib.Path(grabar_en).parent.mkdir(parents=True, exist_ok=True)

    def _leer_respuesta(self) -> str:
        lineas = []
        while True:
            linea = self._input("> " if not lineas else "")
            if not linea.strip() and lineas:
                break
            if linea.strip():
                lineas.append(linea)
        return "\n".join(lineas).strip()

    def decidir(self, historial: list):
        texto = historial[0]["content"] if len(historial) == 1 else historial[-1]["content"]
        self._turno.write_text(texto, encoding="utf-8")
        copiado = copiar_al_portapapeles(texto)
        print(f"\n===== PASO {len(self._decisiones) + 1}: COPIE ESTO EN SU ASISTENTE DE IA "
              f"({'ya está en el portapapeles' if copiado else 'también está en ' + str(self._turno)}) =====")
        print(texto)
        print("===== PEGUE LA RESPUESTA JSON Y PRESIONE ENTER EN UNA LÍNEA VACÍA =====")
        bruto = self._leer_respuesta()
        try:
            d = json.loads(bruto)
        except json.JSONDecodeError:
            d = bruto            # no se corrige a mano: el contrato lo rechazará
        self._decisiones.append(d)
        json.dump(self._decisiones, open(self._archivo, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return d
