"""Bucle del agente: pensar -> actuar -> observar (ReAct), modelado como máquina de estados.

Estados: DECIDIENDO -> VALIDANDO_CONTRATO -> EVALUANDO_POLITICA -> EJECUTANDO -> OBSERVANDO -> DECIDIENDO ...
Estados finales: FINALIZADO (respuesta final) o LIMITE_ALCANZADO (presupuesto de pasos agotado).

Adaptaciones a SismoReporta (Lab 10, E2):
- Si el presupuesto se agota sin una respuesta final (por ejemplo, por decisiones que no cumplen
  el contrato), también se registra LIMITE_ALCANZADO: ningún camino termina sin estado final.
- Al terminar se registra un evento "fin" con los pasos usados y el contexto final (caracteres
  del historial), que agente/traza.py usa para las métricas de E5 y E7.
- La carpeta de la traza se crea si no existe.
"""
import json, pathlib, time
from agente.contrato import validar_decision


class Agente:
    def __init__(self, nombre, modelo, herramientas, politica, objetivo, traza_archivo):
        self.nombre, self.modelo, self.h, self.politica = nombre, modelo, herramientas, politica
        self.historial = [{"role": "user", "content": objetivo}]       # memoria de corto plazo
        self.traza_archivo, self.eventos = traza_archivo, []

    def _registrar(self, **evento):
        evento["t"] = round(time.perf_counter() - self._t0, 3)
        evento["agente"] = self.nombre
        self.eventos.append(evento)

    def ejecutar(self) -> str:
        self._t0 = time.perf_counter()
        self._registrar(tipo="objetivo", estado="INICIO", texto=self.historial[0]["content"])
        conocidas = set(self.h.catalogo())
        for paso in range(1, self.politica.max_pasos + 2):
            d = self.modelo.decidir(self.historial)                       # DECIDIENDO
            self.historial.append({"role": "assistant", "content": json.dumps(d, ensure_ascii=False)})
            ok, motivo = validar_decision(d, conocidas)                   # VALIDANDO_CONTRATO
            if not ok:
                obs = f"ERROR DE CONTRATO: {motivo}. Responda solo con el JSON del protocolo."
                self._registrar(tipo="accion", estado="CONTRATO_INVALIDO", paso=paso, pensamiento=str(d)[:200],
                                accion="(ninguna)", args={}, observacion=obs, bloqueada=True)
            elif "final" in d:
                self._registrar(tipo="final", estado="FINALIZADO", paso=paso, pensamiento=d["pensamiento"], texto=d["final"])
                break
            else:
                accion, args = d["accion"], d.get("args", {})
                veredicto = self.politica.evaluar(accion, args, paso)     # EVALUANDO_POLITICA
                if veredicto.permitido:
                    try:
                        obs = getattr(self.h, accion)(**args)             # EJECUTANDO
                    except Exception as e:                                # el error también es una observación
                        obs = f"ERROR: {type(e).__name__}: {e}"
                    self._registrar(tipo="accion", estado="OBSERVANDO", paso=paso, pensamiento=d["pensamiento"],
                                    accion=accion, args=args, observacion=obs[:600], bloqueada=False)
                else:
                    obs = f"BLOQUEADO POR LA POLÍTICA: {veredicto.motivo}"
                    limite = "máximo" in veredicto.motivo
                    self._registrar(tipo="accion", estado="LIMITE_ALCANZADO" if limite else "BLOQUEADO", paso=paso,
                                    pensamiento=d["pensamiento"], accion=accion, args=args, observacion=obs, bloqueada=True)
                    if limite:
                        break
            self.historial.append({"role": "user", "content": f"Observación: {obs}"})   # OBSERVANDO -> DECIDIENDO
        if self.eventos[-1]["estado"] not in ("FINALIZADO", "LIMITE_ALCANZADO"):
            self._registrar(tipo="limite", estado="LIMITE_ALCANZADO", paso=paso,
                            texto=f"Se agotaron los {self.politica.max_pasos} pasos sin una respuesta final")
        ultimo = self.eventos[-1]
        self._registrar(tipo="fin", estado=ultimo["estado"], pasos=ultimo.get("paso", 0),
                        contexto_caracteres=len(json.dumps(self.historial, ensure_ascii=False)),
                        texto=ultimo.get("texto", "(sin respuesta final)"))
        pathlib.Path(self.traza_archivo).parent.mkdir(parents=True, exist_ok=True)
        with open(self.traza_archivo, "w", encoding="utf-8") as f:
            for e in self.eventos:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        return ultimo.get("texto", "(sin respuesta final)") if ultimo["tipo"] == "final" else "(sin respuesta final)"
