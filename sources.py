"""Fuentes de ofertas. Cada una devuelve una lista de objetos Oferta.

- Get on Board: tiene API PÚBLICA y gratuita (la vía más limpia y estable).
- Computrabajo y LinkedIn: NO tienen API pública. Aquí se leen las páginas públicas de
  búsqueda (sin iniciar sesión). Sus términos de uso restringen el scraping, y pueden bloquear
  la conexión o cambiar su HTML sin avisar. Por eso: poca frecuencia, nunca con tu usuario
  y cualquier fallo solo apaga esa fuente (el bot sigue con las demás).
"""
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scoring import normalizar

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "es-CO,es;q=0.9",
}
PAUSA_ENTRE_BUSQUEDAS = 3  # segundos: ser amable con los sitios


class FuenteBloqueada(Exception):
    """La página nos rechazó (403/429/999...) o cambió. No es grave: se salta esa fuente."""


@dataclass
class Oferta:
    id: str
    titulo: str
    empresa: str
    lugar: str
    url: str
    fuente: str
    texto: str = ""            # descripción o texto de la tarjeta, para puntuar
    publicada_ts: int = 0      # fecha en segundos (0 = desconocida)
    puntaje: int = 0
    motivos: list = field(default_factory=list)


def _get(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=25)
    if r.status_code in (403, 429, 999) or r.status_code >= 500:
        raise FuenteBloqueada(f"{urlparse(url).netloc} respondió {r.status_code}")
    r.raise_for_status()
    return r


def _limpiar_url(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


# ----------------------------------------------------------------------------- Get on Board
def parsear_getonboard(datos: dict) -> list:
    ofertas = []
    for item in datos.get("data", []):
        a = item.get("attributes", {})
        empresa = ""
        c = a.get("company")
        if isinstance(c, dict):
            c = c.get("data", c)
            empresa = (c.get("attributes", {}) or {}).get("name") or c.get("name", "")
        paises = a.get("countries") or []
        lugar = ", ".join(paises) if isinstance(paises, list) else str(paises)
        modalidad = a.get("remote_modality") or ""
        if modalidad:
            lugar = f"{lugar} ({modalidad})" if lugar else modalidad
        slug = item.get("id", "")
        url = (item.get("links") or {}).get("public_url") or f"https://www.getonbrd.com/jobs/{slug}"
        texto = " ".join(str(a.get(k, "")) for k in ("description", "functions", "desirable", "category_name"))
        texto = re.sub(r"<[^>]+>", " ", texto)  # quita etiquetas HTML
        ofertas.append(Oferta(
            id=f"gob:{slug}", titulo=a.get("title", ""), empresa=empresa, lugar=lugar,
            url=url, fuente="Get on Board", texto=texto, publicada_ts=int(a.get("published_at") or 0)))
    return ofertas


def buscar_getonboard(cfg: dict) -> list:
    resultado = []
    for consulta in cfg["buscar"]:
        params = {"query": consulta, "per_page": 30, "page": 1, "lang": "es", "expand[]": "company"}
        if cfg.get("solo_remoto"):
            params["remote"] = "true"
        r = _get("https://www.getonbrd.com/api/v0/search/jobs", params)
        resultado += parsear_getonboard(r.json())
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return resultado


# ----------------------------------------------------------------------------- LinkedIn (páginas públicas)
def parsear_linkedin(html: str) -> list:
    sopa = BeautifulSoup(html, "html.parser")
    ofertas = []
    for tarjeta in sopa.select("li"):
        enlace = tarjeta.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
        titulo = tarjeta.select_one(".base-search-card__title")
        if not enlace or not titulo:
            continue
        empresa = tarjeta.select_one(".base-search-card__subtitle")
        lugar = tarjeta.select_one(".job-search-card__location")
        div = tarjeta.select_one("[data-entity-urn]")
        urn = div["data-entity-urn"].split(":")[-1] if div else _limpiar_url(enlace["href"])
        ofertas.append(Oferta(
            id=f"li:{urn}", titulo=titulo.get_text(strip=True),
            empresa=empresa.get_text(strip=True) if empresa else "",
            lugar=lugar.get_text(strip=True) if lugar else "",
            url=_limpiar_url(enlace["href"]), fuente="LinkedIn"))
    return ofertas


def buscar_linkedin(cfg: dict) -> list:
    resultado = []
    for consulta in cfg["buscar"]:
        params = {"keywords": consulta, "location": cfg.get("ubicacion", "Colombia"),
                  "f_TPR": f"r{int(cfg.get('antiguedad_horas', 72)) * 3600}", "start": 0}
        if cfg.get("solo_remoto"):
            params["f_WT"] = 2  # 2 = remoto en el filtro de LinkedIn
        r = _get("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search", params)
        resultado += parsear_linkedin(r.text)
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return resultado


# ----------------------------------------------------------------------------- Computrabajo (páginas públicas)
def parsear_computrabajo(html: str, base: str = "https://co.computrabajo.com") -> list:
    sopa = BeautifulSoup(html, "html.parser")
    ofertas = []
    for tarjeta in sopa.select("article.box_offer, article[data-id]"):
        enlace = tarjeta.select_one("h2 a, a.js-o-link")
        if not enlace or not enlace.get("href"):
            continue
        empresa = tarjeta.select_one("a[href*='empresa'], p.fs16 a, a.fc_base")
        lugar = tarjeta.select_one("p.fs16.fc_base.mt5 span, span.mr10")
        url = _limpiar_url(urljoin(base, enlace["href"]))
        ofertas.append(Oferta(
            id=f"ct:{tarjeta.get('data-id') or url}", titulo=enlace.get_text(strip=True),
            empresa=empresa.get_text(strip=True) if empresa else "",
            lugar=lugar.get_text(strip=True) if lugar else "",
            url=url, fuente="Computrabajo", texto=tarjeta.get_text(" ", strip=True)))
    return ofertas


def buscar_computrabajo(cfg: dict) -> list:
    resultado = []
    for consulta in cfg["buscar"]:
        slug = re.sub(r"[^a-z0-9]+", "-", normalizar(consulta)).strip("-")
        r = _get(f"https://co.computrabajo.com/trabajo-de-{slug}")
        resultado += parsear_computrabajo(r.text)
        time.sleep(PAUSA_ENTRE_BUSQUEDAS)
    return resultado


# ----------------------------------------------------------------------------- Remotive (API pública, en inglés)
def parsear_remotive(datos: dict, ubicaciones: list) -> list:
    """Remotive publica ofertas remotas de todo el mundo. Solo dejamos las que aceptan candidatos
    desde Latinoamérica/Colombia o desde cualquier lugar (campo candidate_required_location)."""
    ofertas = []
    permitidas = [normalizar(u) for u in ubicaciones]
    for j in datos.get("jobs", []):
        lugar = j.get("candidate_required_location") or ""
        if permitidas and not any(p in normalizar(lugar) for p in permitidas):
            continue
        try:
            ts = int(datetime.fromisoformat(j["publication_date"]).replace(tzinfo=timezone.utc).timestamp())
        except (KeyError, ValueError, TypeError):
            ts = 0
        texto = re.sub(r"<[^>]+>", " ", j.get("description") or "")
        ofertas.append(Oferta(
            id=f"rem:{j.get('id')}", titulo=j.get("title", ""), empresa=j.get("company_name", ""),
            lugar=lugar, url=j.get("url", ""), fuente="Remotive", texto=texto[:3000], publicada_ts=ts))
    return ofertas


def buscar_remotive(cfg: dict) -> list:
    # UNA sola petición trae todo el listado; el filtro lo hacemos nosotros (así no abusamos de su API).
    r = _get("https://remotive.com/api/remote-jobs", {"limit": 200})
    return parsear_remotive(r.json(), cfg.get("remotive_ubicaciones", []))


FUENTES = {
    "getonboard": ("Get on Board", buscar_getonboard),
    "computrabajo": ("Computrabajo", buscar_computrabajo),
    "linkedin": ("LinkedIn", buscar_linkedin),
    "remotive": ("Remotive", buscar_remotive),
}
