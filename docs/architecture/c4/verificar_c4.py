"""Comprobaciones automáticas del modelo C4 (Lab 06) sobre la exportación JSON de Structurizr.

Uso (desde la raíz del repositorio):
    structurizr.sh export -w docs/architecture/c4/workspace.dsl -f json -o /tmp/c4
    python docs/architecture/c4/verificar_c4.py /tmp/c4/workspace.json docs/design/paquetes.puml

Comprueba:
1. Por vista: elementos y relaciones, y cuántos no tienen descripción o tecnología.
2. Componentes de la API = paquetes de paquetes.puml, con las mismas dependencias.
3. Las dependencias entre componentes no tienen ciclos (regla C4 del Lab 05).
4. Cada contenedor tiene al menos una instancia en el entorno "Producción".
Devuelve código de salida 1 si falla alguna de las comprobaciones 2 a 4.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata


def normalizar(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def recorrer(workspace: dict):
    """Devuelve (elementos por id, relaciones por id)."""
    elementos, relaciones = {}, {}

    tipos = {"people": "Person", "softwareSystems": "SoftwareSystem", "containers": "Container",
             "components": "Component", "deploymentNodes": "DeploymentNode", "children": "DeploymentNode",
             "infrastructureNodes": "InfrastructureNode", "containerInstances": "ContainerInstance",
             "softwareSystemInstances": "SoftwareSystemInstance"}

    def agregar(e, padre=None, clave_padre=None):
        e["_padre"] = padre
        e["type"] = tipos[clave_padre]
        elementos[e["id"]] = e
        for r in e.get("relationships", []):
            relaciones[r["id"]] = r
        for clave in ("containers", "components", "children", "infrastructureNodes",
                      "containerInstances", "softwareSystemInstances"):
            for hijo in e.get(clave, []):
                agregar(hijo, e["id"], clave)

    modelo = workspace["model"]
    for clave in ("people", "softwareSystems", "deploymentNodes"):
        for e in modelo.get(clave, []):
            agregar(e, None, clave)
    return elementos, relaciones


def tiene_ciclo(grafo: dict[str, set[str]]) -> list[str] | None:
    estado: dict[str, int] = {}
    camino: list[str] = []

    def visitar(n):
        estado[n] = 1
        camino.append(n)
        for m in grafo.get(n, ()):
            if estado.get(m) == 1:
                return camino[camino.index(m):] + [m]
            if m not in estado:
                c = visitar(m)
                if c:
                    return c
        estado[n] = 2
        camino.pop()
        return None

    for n in grafo:
        if n not in estado:
            c = visitar(n)
            if c:
                return c
    return None


def main(ruta_json: str, ruta_paquetes: str) -> int:
    ws = json.load(open(ruta_json, encoding="utf-8"))
    elementos, relaciones = recorrer(ws)
    fallos = 0

    # 1. Conteos por vista
    print("## 1. Elementos y relaciones por vista\n")
    print("| Vista | Elementos | Sin descripción | Relaciones | Sin descripción | Sin tecnología |")
    print("|---|---|---|---|---|---|")
    vistas = ws["views"]
    for tipo in ("systemContextViews", "containerViews", "componentViews", "dynamicViews", "deploymentViews"):
        for v in vistas.get(tipo, []):
            ids_e = [e["id"] for e in v.get("elements", [])]
            ids_r = [r["id"] for r in v.get("relationships", [])]
            # Las instancias de despliegue muestran la descripción de su contenedor o sistema.
            descr_e = [i for i in ids_e if not elementos[i].get("description")
                       and elementos[i]["type"] not in ("ContainerInstance", "SoftwareSystemInstance")]
            # En la vista dinámica la descripción es la del paso; la tecnología viene del modelo.
            descr_r = [r for r in v.get("relationships", [])
                       if not (r.get("description") or relaciones[r["id"]].get("description"))]
            tecn_r = [i for i in ids_r if not relaciones[i].get("technology")]
            print(f"| {v['key']} | {len(ids_e)} | {len(descr_e)} | {len(ids_r)} | {len(descr_r)} | {len(tecn_r)} |")

    # 2. Componentes frente a paquetes
    print("\n## 2. Componentes de la API frente a paquetes.puml\n")
    texto = open(ruta_paquetes, encoding="utf-8").read()
    paquetes = {normalizar(n) for n in re.findall(r'^package\s+"([^"]+)"', texto, re.M)}
    alias = dict(re.findall(r'^package\s+"([^"]+)"\s+as\s+(\w+)', texto, re.M))
    alias = {a: normalizar(n) for n, a in alias.items()}
    deps_paquetes = {(alias[a], alias[b]) for a, b in re.findall(r"^(\w+)\s+\.\.>\s+(\w+)\s*:", texto, re.M)
                     if a in alias and b in alias}

    api = next(e for e in elementos.values() if e.get("type") == "Container" and e["name"] == "API")
    componentes = {c["id"]: normalizar(c["name"]) for c in api.get("components", [])}
    deps_componentes = {(componentes[r["sourceId"]], componentes[r["destinationId"]])
                        for r in relaciones.values()
                        if r["sourceId"] in componentes and r["destinationId"] in componentes}

    iguales = paquetes == set(componentes.values())
    print(f"- Paquetes: {sorted(paquetes)}")
    print(f"- Componentes: {sorted(componentes.values())}")
    print(f"- ¿Mismos nombres? {'Sí' if iguales else 'NO'}")
    faltan = deps_paquetes - deps_componentes
    sobran = deps_componentes - deps_paquetes
    print(f"- Dependencias: {len(deps_paquetes)} en paquetes.puml, {len(deps_componentes)} en el modelo; "
          f"faltan {sorted(faltan) or 0}, sobran {sorted(sobran) or 0}")
    fallos += (not iguales) + bool(faltan) + bool(sobran)

    # 3. Ciclos
    grafo: dict[str, set[str]] = {}
    for a, b in deps_componentes:
        grafo.setdefault(a, set()).add(b)
    ciclo = tiene_ciclo(grafo)
    print(f"\n## 3. Ciclos entre componentes\n\n- {'Ciclo: ' + ' -> '.join(ciclo) if ciclo else 'Sin ciclos'}")
    fallos += bool(ciclo)

    # 4. Instancias de despliegue
    print("\n## 4. Instancias de cada contenedor en Producción\n")
    print("| Contenedor | Instancias | Nodo |")
    print("|---|---|---|")
    contenedores = [e for e in elementos.values() if e.get("type") == "Container"]
    for c in contenedores:
        inst = [e for e in elementos.values() if e.get("type") == "ContainerInstance"
                and e.get("containerId") == c["id"] and e.get("environment") == "Producción"]
        nodos = ", ".join(elementos[i["_padre"]]["name"] for i in inst)
        print(f"| {c['name']} | {len(inst)} | {nodos} |")
        fallos += not inst

    print(f"\nComprobaciones fallidas: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
