"""Herramientas del agente. Cada una es una función pequeña, con descripción y parámetros explícitos.
Todas operan DENTRO del directorio de trabajo (sandbox).

Adaptaciones a SismoReporta (Lab 10, E2):
- Las rutas aceptan "\\" o "/" y se devuelven siempre con "/", para que una trayectoria grabada
  en Windows se reproduzca igual en Linux (integración continua).
- ejecutar_pruebas(ruta=None) puede limitarse a un archivo o carpeta de pruebas y usa el mismo
  intérprete de Python que ejecuta el agente.
- ver_cambios compara con la copia original que crea el orquestador (trabajo_original).

Herramientas nuevas (Lab 10, E4), solo si se crea con extras=True:
- mapa_repo(carpeta='src'): estructura y firmas obtenidas con ast, sin leer cada archivo entero.
- anotar(texto) y leer_notas(): memoria de notas (pizarra) en notas.md dentro del sandbox.
"""
import ast, os, pathlib, subprocess, re, sys


class Herramientas:
    NOTAS = "notas.md"

    def __init__(self, raiz, original=None, extras=False):
        self.raiz = pathlib.Path(raiz).resolve()
        self.original = pathlib.Path(original).resolve() if original else self.raiz.parent / "trabajo_original"
        self.extras = extras

    # --- utilidades ---
    def _ruta(self, ruta: str) -> pathlib.Path:
        p = (self.raiz / str(ruta).replace("\\", "/")).resolve()
        if self.raiz not in p.parents and p != self.raiz:
            raise PermissionError(f"Ruta fuera del sandbox: {ruta}")
        return p

    def _rel(self, p: pathlib.Path) -> str:
        return p.relative_to(self.raiz).as_posix()

    def catalogo(self) -> dict:
        """Descripción de las herramientas que se envía al modelo (como en un MCP server)."""
        return {
            "listar_archivos": "listar_archivos(carpeta='.'): lista los archivos .py y .md de la carpeta (rutas con /)",
            "leer_archivo": "leer_archivo(ruta): devuelve el contenido con números de línea",
            "buscar": "buscar(patron): busca una expresión regular en los archivos .py; devuelve ruta:línea: texto",
            "ejecutar_pruebas": "ejecutar_pruebas(ruta=None): ejecuta pytest (todo, o solo un archivo o carpeta de pruebas) y devuelve las fallas y el resumen",
            "editar_archivo": "editar_archivo(ruta, antes, despues): reemplaza un fragmento exacto, que debe aparecer una sola vez",
            "ver_cambios": "ver_cambios(): muestra el diff de los .py respecto de la copia original",
            "ejecutar_comando": "ejecutar_comando(comando): ejecuta un comando de shell; solo se permiten python -m pytest, radon cc, lint-imports y git status/diff",
        } | ({
            "mapa_repo": "mapa_repo(carpeta='src'): por cada archivo .py, sus clases, métodos y funciones con parámetros y la línea donde empiezan; más barato que leer cada archivo",
            "anotar": "anotar(texto): guarda una nota corta (hipótesis, archivo revisado, decisión) en notas.md; devuelve cuántas notas hay",
            "leer_notas": "leer_notas(): devuelve las notas guardadas, numeradas",
        } if self.extras else {})

    # --- herramientas ---
    def listar_archivos(self, carpeta="."):
        base = self._ruta(carpeta)
        return "\n".join(sorted(self._rel(p) for p in base.rglob("*")
                                if p.suffix in (".py", ".md") and "__pycache__" not in p.parts))

    def leer_archivo(self, ruta):
        lineas = self._ruta(ruta).read_text(encoding="utf-8").splitlines()
        return "\n".join(f"{i:3d}| {l}" for i, l in enumerate(lineas, 1))

    def buscar(self, patron):
        rx, hallazgos = re.compile(patron), []
        for p in sorted(self.raiz.rglob("*.py")):
            for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if rx.search(l):
                    hallazgos.append(f"{self._rel(p)}:{i}: {l.strip()}")
        return "\n".join(hallazgos[:40]) or "(sin resultados)"

    def ejecutar_pruebas(self, ruta=None):
        objetivo = [self._rel(self._ruta(ruta))] if ruta else []
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *objetivo],
                           cwd=self.raiz, capture_output=True, text=True, timeout=180,
                           stdin=subprocess.DEVNULL)
        salida = (r.stdout + r.stderr).strip().splitlines()
        fallos = [l for l in salida if l.startswith(("FAILED", "ERROR"))][:8]
        detalle = [l for l in salida if l.startswith("E ")][:4]
        return "\n".join(salida[-1:] + fallos + detalle)      # el resumen primero: sobrevive al recorte de la traza

    def editar_archivo(self, ruta, antes, despues):
        p = self._ruta(ruta)
        texto = p.read_text(encoding="utf-8")
        if texto.count(antes) != 1:
            return f"ERROR: el fragmento aparece {texto.count(antes)} veces; debe aparecer exactamente 1"
        p.write_text(texto.replace(antes, despues), encoding="utf-8")
        return f"OK: {ruta} modificado"

    def ver_cambios(self):
        import difflib
        salida = []
        for p in sorted(self.raiz.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            rel = self._rel(p); q = self.original / rel
            a = q.read_text(encoding="utf-8").splitlines() if q.exists() else []
            salida += difflib.unified_diff(a, p.read_text(encoding="utf-8").splitlines(),
                                           f"a/{rel}", f"b/{rel}", lineterm="", n=1)
        return "\n".join(salida) or "(sin cambios)"

    # --- herramientas nuevas (E4) ---
    @staticmethod
    def _firma(nodo) -> str:
        a = nodo.args
        nombres = [x.arg for x in a.posonlyargs + a.args]
        nombres += [f"*{a.vararg.arg}"] if a.vararg else []
        nombres += [x.arg for x in a.kwonlyargs] + ([f"**{a.kwarg.arg}"] if a.kwarg else [])
        return f"{nodo.name}({', '.join(nombres)})"

    def mapa_repo(self, carpeta="src"):
        lineas = []
        for p in sorted(self._ruta(carpeta).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            try:
                arbol = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError as e:
                lineas.append(f"{self._rel(p)}: ERROR DE SINTAXIS en la línea {e.lineno}")
                continue
            elementos = []
            for nodo in arbol.body:
                if isinstance(nodo, ast.ClassDef):
                    metodos = [f"{self._firma(m)}@{m.lineno}" for m in nodo.body
                               if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    elementos.append(f"  class {nodo.name}@{nodo.lineno}: " + "; ".join(metodos))
                elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    elementos.append(f"  def {self._firma(nodo)}@{nodo.lineno}")
            if elementos:
                lineas += [self._rel(p)] + elementos
        return "\n".join(lineas) or "(sin archivos .py)"

    def anotar(self, texto):
        texto = " ".join(str(texto).split())
        if not texto:
            return "ERROR: la nota está vacía"
        if len(texto) > 300:
            return "ERROR: la nota tiene más de 300 caracteres; resúmela"
        notas = self.raiz / self.NOTAS
        previas = notas.read_text(encoding="utf-8").splitlines() if notas.exists() else []
        notas.write_text("\n".join(previas + [f"- {texto}"]) + "\n", encoding="utf-8")
        return f"OK: {len(previas) + 1} nota(s) en {self.NOTAS}"

    def leer_notas(self):
        notas = self.raiz / self.NOTAS
        if not notas.exists():
            return "(sin notas)"
        return "\n".join(f"{i}. {l[2:]}" for i, l in enumerate(notas.read_text(encoding="utf-8").splitlines(), 1))

    def ejecutar_comando(self, comando):
        # E7 (hallazgo de las trazas): "lint-imports" no se encontraba en Windows (el directorio Scripts no
        # estaba en el PATH) y en Linux fallaba sin PYTHONPATH; en ambos casos el agente concluyó que "no está
        # instalado" y revisó ADR-005 a mano. Ahora lint-imports y python usan el mismo intérprete del agente,
        # con PYTHONPATH=src:src/modulo como en el CI. La política ya evaluó el comando original.
        partes = str(comando).split()
        if partes and partes[0] == "lint-imports":
            comando = (f'"{sys.executable}" -c "from importlinter.cli import lint_imports_command; '
                       f'lint_imports_command()" ' + " ".join(partes[1:]))
        elif partes and partes[0] == "python":
            comando = f'"{sys.executable}" ' + " ".join(partes[1:])
        entorno = dict(os.environ, PYTHONPATH=os.pathsep.join(["src", os.path.join("src", "modulo")]))
        # stdin=DEVNULL: en Windows, bajo pytest, heredar la entrada estándar da WinError 6.
        r = subprocess.run(comando, shell=True, cwd=self.raiz, capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL, env=entorno)
        salida = (r.stdout + r.stderr).strip()[-2000:]
        # Una observación vacía no le dice nada al modelo (ver orquestador.preparar_sandbox).
        return salida or f"(el comando terminó sin salida; código de salida {r.returncode})"
