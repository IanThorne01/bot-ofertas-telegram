"""Hablar con Telegram usando su API HTTP (gratis). Documentación: core.telegram.org/bots/api"""
import html
import requests


class Telegram:
    def __init__(self, token: str, chat_id: str):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = str(chat_id)

    def _post(self, metodo: str, **datos):
        r = requests.post(f"{self.base}/{metodo}", json=datos, timeout=20)
        r.raise_for_status()
        return r.json()

    def enviar(self, texto: str, botones=None):
        datos = dict(chat_id=self.chat_id, text=texto, parse_mode="HTML", disable_web_page_preview=True)
        if botones:
            datos["reply_markup"] = {"inline_keyboard": botones}
        return self._post("sendMessage", **datos)

    def responder_boton(self, callback_id: str, texto: str):
        self._post("answerCallbackQuery", callback_query_id=callback_id, text=texto)

    def quitar_botones(self, message_id: int):
        self._post("editMessageReplyMarkup", chat_id=self.chat_id, message_id=message_id,
                   reply_markup={"inline_keyboard": []})

    def definir_comandos(self):
        """Crea el menú que aparece al escribir "/" en el chat."""
        self._post("setMyCommands", commands=[
            {"command": "estado", "description": "Ver si el bot está activo"},
            {"command": "pausar", "description": "Dejar de enviarme ofertas"},
            {"command": "reanudar", "description": "Volver a enviarme ofertas"},
            {"command": "guardadas", "description": "Ver las ofertas que guardé"},
            {"command": "ayuda", "description": "Qué puede hacer el bot"},
        ])

    def actualizaciones(self, offset: int = 0):
        r = requests.get(f"{self.base}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=20)
        r.raise_for_status()
        return r.json().get("result", [])


def esc(texto: str) -> str:
    """Escapa caracteres raros para que Telegram (modo HTML) no se confunda."""
    return html.escape(texto or "", quote=False)
