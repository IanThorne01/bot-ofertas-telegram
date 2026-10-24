"""Puntaje de una oferta según TU perfil (config.json).

Idea: cada palabra tiene un peso. Si aparece en el TÍTULO vale el doble
(el título es lo más importante); si solo aparece en el texto, vale el peso normal.
Las palabras que restan (senior, ventas...) tienen peso negativo.
"""
import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar 'Ingeniería' con 'ingenieria'."""
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower()


def contiene(texto_normalizado: str, palabra: str) -> bool:
    """True si la palabra/frase aparece completa (no como parte de otra palabra)."""
    patron = r"(?<!\w)" + re.escape(normalizar(palabra)) + r"(?!\w)"
    return re.search(patron, texto_normalizado) is not None


def titulo_excluido(titulo: str, config: dict) -> bool:
    t = normalizar(titulo)
    return any(contiene(t, p) for p in config.get("excluir_si_el_titulo_dice", []))


def es_remoto(texto: str) -> bool:
    t = normalizar(texto)
    return any(contiene(t, p) for p in
               ["remoto", "remota", "remote", "teletrabajo", "home office", "trabajo en casa", "100% remoto"])


def puntuar(titulo: str, texto: str, config: dict):
    """Devuelve (puntaje, lista_de_palabras_que_coincidieron)."""
    t = normalizar(titulo)
    x = normalizar(texto)
    puntaje = 0
    motivos = []
    pesos = {}
    pesos.update(config.get("palabras_suman", {}))
    pesos.update(config.get("palabras_restan", {}))
    for palabra, peso in pesos.items():
        if contiene(t, palabra):
            puntaje += peso * 2
            motivos.append(palabra)
        elif contiene(x, palabra):
            puntaje += peso
            motivos.append(palabra)
    return puntaje, motivos
