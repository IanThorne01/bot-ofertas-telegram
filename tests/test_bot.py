"""Pruebas sin internet: usan datos de ejemplo. Se corren con:  python -m unittest -v"""
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scoring import contiene, es_remoto, normalizar, puntuar, titulo_excluido
from sources import Oferta, parsear_computrabajo, parsear_getonboard, parsear_linkedin, parsear_remotive
from storage import Estado
import main as bot

CFG = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text(encoding="utf-8"))


class TestPuntaje(unittest.TestCase):
    def test_normaliza_tildes(self):
        self.assertEqual(normalizar("Ingeniería"), "ingenieria")

    def test_palabra_completa(self):
        self.assertTrue(contiene("auxiliar de datos", "datos"))
        self.assertFalse(contiene("base de datos", "sql"))
        self.assertFalse(contiene("seniority", "senior"))
        self.assertTrue(contiene("programador c++ junior", "c++"))

    def test_titulo_vale_doble(self):
        en_titulo, _ = puntuar("Analista SQL", "", CFG)
        en_texto, _ = puntuar("Analista", "usamos sql", CFG)
        self.assertEqual(en_titulo, 2 * en_texto)

    def test_senior_resta(self):
        malo, _ = puntuar("Analista de datos senior", "excel", CFG)
        bueno, _ = puntuar("Analista de datos junior", "excel", CFG)
        self.assertLess(malo, bueno)

    def test_excluidos_y_remoto(self):
        self.assertTrue(titulo_excluido("Gerente de datos", CFG))
        self.assertFalse(titulo_excluido("Auxiliar de datos", CFG))
        self.assertTrue(es_remoto("Trabajo 100% remoto"))
        self.assertFalse(es_remoto("Presencial en Bogotá"))


class TestParsers(unittest.TestCase):
    def test_getonboard(self):
        datos = {"data": [{"id": "analista-datos-acme", "type": "job",
                           "attributes": {"title": "Analista de datos", "countries": ["Colombia"],
                                          "remote_modality": "fully_remote", "published_at": 1790000000,
                                          "description": "<p>Excel y SQL</p>",
                                          "company": {"data": {"attributes": {"name": "ACME"}}}},
                           "links": {"public_url": "https://www.getonbrd.com/jobs/analista-datos-acme"}}]}
        o = parsear_getonboard(datos)[0]
        self.assertEqual((o.titulo, o.empresa, o.id), ("Analista de datos", "ACME", "gob:analista-datos-acme"))
        self.assertIn("Excel", o.texto)

    def test_linkedin_ejemplo(self):
        html = """<li><div class="base-card" data-entity-urn="urn:li:jobPosting:123">
        <a class="base-card__full-link" href="https://co.linkedin.com/jobs/view/x-123?trk=abc"></a>
        <h3 class="base-search-card__title"> Auxiliar de datos </h3>
        <h4 class="base-search-card__subtitle">Empresa SAS</h4>
        <span class="job-search-card__location">Colombia</span></div></li>"""
        o = parsear_linkedin(html)[0]
        self.assertEqual((o.id, o.titulo, o.url), ("li:123", "Auxiliar de datos", "https://co.linkedin.com/jobs/view/x-123"))

    def test_computrabajo_ejemplo(self):
        html = """<article class="box_offer" data-id="ABC"><h2><a class="js-o-link" href="/ofertas-de-trabajo/oferta-x.html#ABC">Auxiliar de datos remoto</a></h2>
        <p class="fs16"><a href="/empresa-x">Empresa X</a></p></article>"""
        o = parsear_computrabajo(html)[0]
        self.assertEqual((o.id, o.titulo), ("ct:ABC", "Auxiliar de datos remoto"))
        self.assertTrue(o.url.startswith("https://co.computrabajo.com/ofertas"))


class TestRemotive(unittest.TestCase):
    def test_filtra_por_ubicacion(self):
        datos = {"jobs": [
            {"id": 1, "url": "https://remotive.com/a", "title": "Data Analyst", "company_name": "ACME",
             "candidate_required_location": "Worldwide", "publication_date": "2026-10-22T13:20:12",
             "description": "<p>SQL and Excel</p>"},
            {"id": 2, "url": "https://remotive.com/b", "title": "Data Analyst", "company_name": "USA Inc",
             "candidate_required_location": "USA Only", "publication_date": "2026-10-22T13:20:12", "description": ""},
            {"id": 3, "url": "https://remotive.com/c", "title": "Support", "company_name": "LatamCo",
             "candidate_required_location": "LATAM", "publication_date": "malo", "description": ""}]}
        ofertas = parsear_remotive(datos, CFG["remotive_ubicaciones"])
        self.assertEqual([o.id for o in ofertas], ["rem:1", "rem:3"])
        self.assertGreater(ofertas[0].publicada_ts, 0)
        self.assertEqual(ofertas[1].publicada_ts, 0)


class TestFlujo(unittest.TestCase):
    def test_filtra_duplicados_vistas_y_puntaje(self):
        with tempfile.TemporaryDirectory() as d:
            estado = Estado(Path(d) / "s.json")
            estado.marcar_vista("a:1")
            ahora = int(time.time())
            ofertas = [
                Oferta("a:1", "Analista SQL", "X", "", "u", "t", "excel", ahora),          # ya vista
                Oferta("a:2", "Analista SQL junior", "X", "", "u", "t", "excel", ahora),    # buena
                Oferta("a:2", "Analista SQL junior", "X", "", "u", "t", "excel", ahora),    # repetida
                Oferta("a:3", "Barista", "X", "", "u", "t", "café", ahora),                 # puntaje bajo
                Oferta("a:4", "Analista SQL", "X", "", "u", "t", "", ahora - 99 * 3600),    # muy vieja
                Oferta("a:5", "Gerente de datos SQL", "X", "", "u", "t", "", ahora),        # excluida
            ]
            buenas, evaluadas = bot.filtrar(ofertas, CFG, estado)
            self.assertEqual([o.id for o in buenas], ["a:2"])
            self.assertEqual(len(evaluadas), 2)

    def test_fuente_con_intervalo_se_salta(self):
        with tempfile.TemporaryDirectory() as d:
            estado = Estado(Path(d) / "s.json")
            llamadas = []
            bot.FUENTES_ORIG = bot.FUENTES
            bot.FUENTES = {"remotive": ("Remotive", lambda cfg: llamadas.append(1) or [])}
            try:
                cfg = {**CFG, "fuentes": {"remotive": True}}
                bot.reunir_ofertas(cfg, estado, FakeTG())
                bot.reunir_ofertas(cfg, estado, FakeTG())   # 2.ª vez: aún no pasan 6 horas
                self.assertEqual(len(llamadas), 1)
            finally:
                bot.FUENTES = bot.FUENTES_ORIG

    def test_estado_guarda_y_recarga(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "s.json"
            e = Estado(ruta); e.marcar_vista("x"); e.recordar_pendiente("k", {"titulo": "t"}); e.guardar_oferta("k"); e.guardar()
            e2 = Estado(ruta)
            self.assertTrue(e2.ya_vista("x"))
            self.assertIn("k", e2.datos["guardadas"])


class FakeTG:
    chat_id = "42"
    def __init__(self): self.mensajes = []; self.ups = []
    def enviar(self, texto, botones=None): self.mensajes.append(texto)
    def actualizaciones(self, offset=0): return self.ups
    def responder_boton(self, i, t): pass
    def quitar_botones(self, m): pass


class TestComandos(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.estado = Estado(Path(self.dir.name) / "s.json")
        self.tg = FakeTG()

    def tearDown(self): self.dir.cleanup()

    def comando(self, texto, chat=42):
        self.tg.ups = [{"update_id": 1, "message": {"chat": {"id": chat}, "text": texto}}]
        bot.procesar_botones(self.tg, self.estado, CFG)

    def test_pausar_y_reanudar(self):
        self.comando("/pausar")
        self.assertTrue(self.estado.datos["pausado"])
        self.comando("/reanudar")
        self.assertFalse(self.estado.datos["pausado"])
        self.assertEqual(self.estado.datos["ultima_busqueda"], 0)

    def test_ignora_a_extranos(self):
        self.comando("/pausar", chat=999)
        self.assertFalse(self.estado.datos["pausado"])
        self.assertEqual(self.tg.mensajes, [])

    def test_estado_responde(self):
        self.comando("/estado")
        self.assertIn("Activo", self.tg.mensajes[0])

    def test_resumen_diario(self):
        manana = datetime(2026, 10, 24, 9, 0, tzinfo=bot.ZONA_COLOMBIA)
        self.assertTrue(bot.debe_enviar_resumen(self.estado, CFG, manana))
        bot.enviar_resumen(self.tg, self.estado, manana)
        self.assertFalse(bot.debe_enviar_resumen(self.estado, CFG, manana))           # ya se envió hoy
        madrugada = datetime(2026, 10, 25, 6, 0, tzinfo=bot.ZONA_COLOMBIA)
        self.assertFalse(bot.debe_enviar_resumen(self.estado, CFG, madrugada))        # antes de la hora

    def test_resumen_muestra_las_mas_cercanas(self):
        o = Oferta("a:1", "Auxiliar", "ACME", "", "https://x", "t", "", 0, puntaje=2)
        bot.acumular(self.estado, [o], [], 0)
        bot.enviar_resumen(self.tg, self.estado, datetime(2026, 10, 24, 9, tzinfo=bot.ZONA_COLOMBIA))
        self.assertIn("Auxiliar", self.tg.mensajes[0])


if __name__ == "__main__":
    unittest.main()
