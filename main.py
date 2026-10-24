"""Bot de ofertas de trabajo -> Telegram.

Uso:
    python main.py --chat-id    # te muestra tu chat_id (después de escribirle algo al bot)
    python main.py --prueba     # manda un mensaje de prueba
    python main.py --seco       # busca y MUESTRA en pantalla, sin enviar ni guardar nada
    python main.py --comandos   # crea el menú de comandos (/pausar, /estado...) en Telegram
    python main.py              # corrida normal: busca, filtra, envía y guarda

Comandos desde el chat: /estado /pausar /reanudar /guardadas /ayuda
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # en GitHub Actions las variables ya vienen del entorno
    pass

from scoring import es_remoto, puntuar, titulo_excluido
from sources import FUENTES, FuenteBloqueada
from storage import Estado
from telegram_api import Telegram, esc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")
ZONA_COLOMBIA = timezone(timedelta(hours=-5))  # Colombia y Perú: UTC-5


def cargar_config() -> dict:
    return json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))


def clave_corta(oferta_id: str) -> str:
    """Telegram limita los datos de un botón a 64 bytes: usamos un código corto."""
    return hashlib.sha1(oferta_id.encode()).hexdigest()[:12]


def reunir_ofertas(cfg: dict, estado: Estado, tg) -> list:
    todas = []
    for nombre, (titulo, funcion) in FUENTES.items():
        if not cfg["fuentes"].get(nombre):
            continue
        # algunas fuentes se consultan menos seguido (ver intervalo_fuente_horas en config.json)
        horas = cfg.get("intervalo_fuente_horas", {}).get(nombre, 0)
        ultima = estado.datos.setdefault("ultima_fuente", {}).get(nombre, 0)
        if horas and time.time() - ultima < horas * 3600:
            log.info("%s: consultada hace poco, se salta esta vez", titulo)
            continue
        try:
            encontradas = funcion(cfg)
            if tg:  # en modo seco no se guarda nada
                estado.datos["ultima_fuente"][nombre] = int(time.time())
            log.info("%s: %d ofertas leídas", titulo, len(encontradas))
            todas += encontradas
        except (FuenteBloqueada, Exception) as e:  # una fuente caída no tumba al bot
            log.warning("%s falló: %s", titulo, e)
            if tg and estado.debe_avisar(nombre):
                tg.enviar(f"⚠️ La fuente <b>{esc(titulo)}</b> no respondió hoy: {esc(str(e))[:150]}")
                estado.marcar_aviso(nombre)
    return todas


def filtrar(ofertas: list, cfg: dict, estado: Estado) -> list:
    limite = time.time() - cfg.get("antiguedad_horas", 72) * 3600
    unicas, vistos_ahora = [], set()
    for o in ofertas:
        if o.id in vistos_ahora or estado.ya_vista(o.id):
            continue
        vistos_ahora.add(o.id)
        if o.publicada_ts and o.publicada_ts < limite:
            continue
        if titulo_excluido(o.titulo, cfg):
            continue
        if cfg.get("solo_remoto") and o.fuente == "Computrabajo" and not es_remoto(o.titulo + " " + o.texto):
            continue
        o.puntaje, o.motivos = puntuar(o.titulo, o.texto, cfg)
        unicas.append(o)
    buenas = [o for o in unicas if o.puntaje >= cfg.get("puntaje_minimo", 3)]
    buenas.sort(key=lambda o: o.puntaje, reverse=True)
    return buenas, unicas


def formatear(o) -> str:
    return (f"🆕 <b>{esc(o.titulo)}</b>\n🏢 {esc(o.empresa) or 'Empresa no indicada'}\n"
            f"📍 {esc(o.lugar) or 'Ubicación no indicada'}\n🔎 {esc(o.fuente)} · ⭐ {o.puntaje}"
            f"{' · ' + esc(', '.join(o.motivos[:4])) if o.motivos else ''}\n"
            f'<a href="{esc(o.url)}">Ver oferta</a>')


def procesar_botones(tg: Telegram, estado: Estado, cfg: dict):
    """Lee lo que hiciste en Telegram desde la última corrida: botones y comandos."""
    for u in tg.actualizaciones(estado.datos["offset"]):
        estado.datos["offset"] = u["update_id"] + 1
        cb = u.get("callback_query")
        if cb and str((cb.get("message") or {}).get("chat", {}).get("id")) == tg.chat_id:  # solo TÚ
            accion, _, clave = cb["data"].partition(":")
            if accion == "g":
                info = estado.guardar_oferta(clave)
                tg.responder_boton(cb["id"], "⭐ Guardada" if info else "Ya no está disponible")
            else:
                estado.descartar(clave)
                tg.responder_boton(cb["id"], "🗑 Descartada")
            tg.quitar_botones(cb["message"]["message_id"])
        msg = u.get("message")
        if msg and str(msg["chat"]["id"]) == tg.chat_id:
            manejar_comando(tg, estado, cfg, (msg.get("text") or "").strip().lower())


def manejar_comando(tg, estado: Estado, cfg: dict, texto: str):
    """Comandos que le escribes al bot. Se aplican en la siguiente ejecución (máx. unos 15 min)."""
    if texto.startswith("/pausar"):
        estado.datos["pausado"] = True
        tg.enviar("⏸ Pausado. No te enviaré más ofertas hasta que escribas /reanudar.")
    elif texto.startswith("/reanudar"):
        estado.datos["pausado"] = False
        estado.datos["ultima_busqueda"] = 0  # que busque en la siguiente corrida
        tg.enviar("▶️ Reanudado. Vuelvo a buscar ofertas para ti.")
    elif texto.startswith("/estado"):
        hace = int((time.time() - estado.datos["ultima_busqueda"]) / 60) if estado.datos["ultima_busqueda"] else None
        fuentes = ", ".join(FUENTES[n][0] for n, on in cfg["fuentes"].items() if on) or "ninguna"
        tg.enviar("📊 <b>Estado</b>\n" + ("⏸ En pausa" if estado.datos["pausado"] else "✅ Activo") +
                  f"\nÚltima búsqueda: {'hace ' + str(hace) + ' min' if hace is not None else 'aún no'}"
                  f"\nEnviadas desde el último resumen: {estado.datos['acum']['enviadas']}"
                  f"\nFuentes: {esc(fuentes)}\nBúsqueda cada {cfg.get('intervalo_busqueda_min', 60)} min")
    elif texto.startswith("/guardadas"):
        g = estado.datos["guardadas"]
        cuerpo = "\n\n".join(f'⭐ <a href="{esc(i["url"])}">{esc(i["titulo"])}</a>\n{esc(i["empresa"])}'
                              for i in g.values()) or "Aún no guardaste ofertas."
        tg.enviar("<b>Tus ofertas guardadas</b>\n\n" + cuerpo)
    elif texto.startswith(("/ayuda", "/start")):
        tg.enviar("Te envío ofertas filtradas con tu perfil.\n⭐ Guardar / 🗑 Descartar bajo cada oferta.\n\n"
                  "/estado — ver si estoy activo\n/pausar — dejar de enviarte ofertas\n"
                  "/reanudar — volver a enviarlas\n/guardadas — tus ofertas guardadas")


def debe_enviar_resumen(estado: Estado, cfg: dict, ahora: datetime) -> bool:
    """Un resumen al día, después de la hora configurada (hora de Colombia)."""
    return (estado.datos["ultimo_resumen"] != ahora.strftime("%Y-%m-%d")
            and ahora.hour >= cfg.get("hora_resumen", 8))


def enviar_resumen(tg, estado: Estado, ahora: datetime):
    a = estado.datos["acum"]
    texto = (f"☀️ <b>Resumen diario</b>\nSigo activo ✅\nRevisé {a['nuevas']} ofertas nuevas "
             f"y te envié {a['enviadas']}.")
    if a["enviadas"] == 0:
        texto += "\nNinguna pasó tu filtro."
        if a["casi"]:
            texto += " Las más cercanas fueron:\n" + "\n".join(
                f'• <a href="{esc(c["url"])}">{esc(c["titulo"])}</a> ({esc(c["empresa"])}, ⭐ {c["puntaje"]})'
                for c in a["casi"])
            texto += "\n\nSi quieres más ofertas, baja \"puntaje_minimo\" en config.json."
    tg.enviar(texto)
    estado.datos["ultimo_resumen"] = ahora.strftime("%Y-%m-%d")
    estado.datos["acum"] = {"nuevas": 0, "enviadas": 0, "casi": []}


def acumular(estado: Estado, evaluadas: list, buenas: list, enviadas: int):
    a = estado.datos["acum"]
    a["nuevas"] += len(evaluadas)
    a["enviadas"] += enviadas
    ids_buenas = {o.id for o in buenas}
    cercanas = sorted((o for o in evaluadas if o.id not in ids_buenas), key=lambda o: o.puntaje, reverse=True)[:3]
    a["casi"] = sorted(a["casi"] + [{"titulo": o.titulo, "empresa": o.empresa, "url": o.url, "puntaje": o.puntaje}
                                    for o in cercanas], key=lambda c: c["puntaje"], reverse=True)[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", action="store_true")
    ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--seco", action="store_true")
    ap.add_argument("--comandos", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token:
        sys.exit("Falta TELEGRAM_TOKEN. Revisa tu archivo .env")

    if args.chat_id:
        for u in Telegram(token, "0").actualizaciones():
            m = u.get("message")
            if m:
                print("Tu chat_id es:", m["chat"]["id"], "| nombre:", m["chat"].get("first_name"))
                return
        sys.exit("No veo mensajes. Escríbele algo a tu bot en Telegram y vuelve a correr esto.")

    if not chat:
        sys.exit("Falta TELEGRAM_CHAT_ID. Corre: python main.py --chat-id")
    tg = Telegram(token, chat)

    if args.prueba:
        tg.enviar("✅ ¡Tu bot de ofertas funciona! Pronto te llegarán ofertas.")
        return
    if args.comandos:
        tg.definir_comandos()
        print("Menú de comandos creado. Escribe / en tu chat con el bot para verlo.")
        return

    cfg, estado = cargar_config(), Estado()
    ahora = datetime.now(ZONA_COLOMBIA)
    if not args.seco:
        procesar_botones(tg, estado, cfg)
        if not estado.datos["ultimo_resumen"]:  # primera vez: el primer resumen llega mañana
            estado.datos["ultimo_resumen"] = ahora.strftime("%Y-%m-%d")
        if debe_enviar_resumen(estado, cfg, ahora):
            enviar_resumen(tg, estado, ahora)
        if estado.datos["pausado"]:
            log.info("Bot en pausa: no se busca.")
            estado.guardar()
            return
        minutos = (time.time() - estado.datos["ultima_busqueda"]) / 60
        if minutos < cfg.get("intervalo_busqueda_min", 60):
            log.info("Última búsqueda hace %.0f min: aún no toca.", minutos)
            estado.guardar()
            return

    todas = reunir_ofertas(cfg, estado, None if args.seco else tg)
    buenas, evaluadas = filtrar(todas, cfg, estado)
    enviar = buenas[: cfg.get("max_por_corrida", 10)]
    log.info("%d leídas, %d nuevas, %d pasan el filtro, se envían %d",
             len(todas), len(evaluadas), len(buenas), len(enviar))

    for o in enviar:
        if args.seco:
            print(f"[{o.puntaje}] {o.titulo} | {o.empresa} | {o.fuente}\n    {o.url}")
            continue
        clave = clave_corta(o.id)
        estado.recordar_pendiente(clave, {"titulo": o.titulo, "empresa": o.empresa, "url": o.url})
        tg.enviar(formatear(o), [[{"text": "⭐ Guardar", "callback_data": f"g:{clave}"},
                                  {"text": "🗑 Descartar", "callback_data": f"d:{clave}"}]])
    if not args.seco:
        for o in evaluadas:
            estado.marcar_vista(o.id)  # también las que no pasaron: así no se reevalúan
        acumular(estado, evaluadas, buenas, len(enviar))
        estado.datos["ultima_busqueda"] = int(time.time())
        estado.guardar()


if __name__ == "__main__":
    main()
