"""Memoria del bot: un archivo state.json.

Guarda qué ofertas ya te mostró (para no repetirlas), cuáles guardaste con el botón,
hasta dónde leyó los mensajes de Telegram y cuándo avisó de una fuente caída.
"""
import json
import time
from pathlib import Path

ARCHIVO = Path(__file__).parent / "state.json"
DIAS_MEMORIA = 30


class Estado:
    def __init__(self, ruta: Path = ARCHIVO):
        self.ruta = ruta
        self.datos = {"vistas": {}, "pendientes": {}, "guardadas": {}, "offset": 0, "avisos": {},
                      "pausado": False, "ultima_busqueda": 0, "ultimo_resumen": "",
                      "acum": {"nuevas": 0, "enviadas": 0, "casi": []}}
        if ruta.exists():
            try:
                self.datos.update(json.loads(ruta.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass  # si el archivo se dañó, empezamos de cero

    # --- ofertas vistas ---
    def ya_vista(self, oferta_id: str) -> bool:
        return oferta_id in self.datos["vistas"]

    def marcar_vista(self, oferta_id: str):
        self.datos["vistas"][oferta_id] = int(time.time())

    # --- botones (⭐ guardar / 🗑 descartar) ---
    def recordar_pendiente(self, clave: str, info: dict):
        self.datos["pendientes"][clave] = info

    def guardar_oferta(self, clave: str):
        info = self.datos["pendientes"].get(clave)
        if info:
            self.datos["guardadas"][clave] = info
        return info

    def descartar(self, clave: str):
        self.datos["pendientes"].pop(clave, None)

    # --- aviso de fuentes caídas (máximo 1 aviso por día) ---
    def debe_avisar(self, fuente: str) -> bool:
        ultimo = self.datos["avisos"].get(fuente, 0)
        return time.time() - ultimo > 86400

    def marcar_aviso(self, fuente: str):
        self.datos["avisos"][fuente] = int(time.time())

    def guardar(self):
        limite = time.time() - DIAS_MEMORIA * 86400
        self.datos["vistas"] = {k: v for k, v in self.datos["vistas"].items() if v > limite}
        # los pendientes se limpian solos: solo conservamos los últimos 300
        pend = self.datos["pendientes"]
        if len(pend) > 300:
            for k in list(pend)[: len(pend) - 300]:
                pend.pop(k)
        self.ruta.write_text(json.dumps(self.datos, ensure_ascii=False, indent=1), encoding="utf-8")
