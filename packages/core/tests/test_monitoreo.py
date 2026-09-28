from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
from click.testing import CliRunner

from coopexecutive import monitoring
from coopexecutive.cli import cli
from coopexecutive.monitoring import lector
from coopexecutive.monitoring.cierre import extraer_cierre
from coopexecutive.monitoring.fuentes import FUENTES_INCLUIDAS, cargar_catalogo, leer_catalogo
from coopexecutive.monitoring.temas import coincidencias, preparar_temas

HOY = date(2026, 9, 27)


# --- Fecha de cierre ------------------------------------------------------------------


@pytest.mark.parametrize("texto, esperada", [
    ("Fecha límite: 15 de octubre de 2026.", date(2026, 10, 15)),
    ("La convocatoria cierra el 3 de noviembre del 2026 a las 18:00.", date(2026, 11, 3)),
    ("Recepción de propuestas hasta el 30/11/2026.", date(2026, 11, 30)),
    ("Cierre: 2026-10-30", date(2026, 10, 30)),
    ("Deadline: December 15, 2026 Applications are open.", date(2026, 12, 15)),
    ("The deadline is Tuesday, 6 October 2026 (12:00 noon).", date(2026, 10, 6)),
    ("Applications close on 1st Nov 2026.", date(2026, 11, 1)),
])
def test_extrae_cierre_en_espanol_e_ingles(texto, esperada):
    assert extraer_cierre(texto) == esperada


@pytest.mark.parametrize("texto", [
    "Publicado el 15 de octubre de 2026. Programa de becas.",  # fecha sin palabra de cierre
    "Deadlines are not specified in the source text.",
    "Fecha límite: 31 de febrero de 2026.",  # fecha imposible
    "",
])
def test_sin_cierre_explicito_no_se_supone_fecha(texto):
    assert extraer_cierre(texto) is None


# --- Temas ------------------------------------------------------------------------------


def test_temas_en_espanol_encuentran_avisos_en_ingles():
    temas = preparar_temas(["Energía eólica", "Becas de posgrado"])
    assert [p.etiqueta for p in temas[1].palabras] == ["becas", "posgrado"]  # «de» se ignora
    c = coincidencias("Wind Energy Fellowship for PhD students", temas)
    assert c.temas == ["Energía eólica", "Becas de posgrado"]
    assert c.palabras == ["energía", "eólica", "becas", "posgrado"]
    parcial = coincidencias("Community energy grant", temas)
    assert parcial.palabras == ["energía"] and parcial.temas == []
    assert not coincidencias("Arts festival", temas)


# --- Lectura de canales -------------------------------------------------------------------


def _rss(*items: tuple[str, str, date | None]) -> bytes:
    cuerpo = ""
    for n, (titulo, descripcion, publicado) in enumerate(items):
        fecha = ""
        if publicado is not None:
            momento = datetime(publicado.year, publicado.month, publicado.day, 12, tzinfo=timezone.utc)
            fecha = f"<pubDate>{format_datetime(momento)}</pubDate>"
        cuerpo += (f"<item><title>{titulo}</title><link>https://ejemplo.org/{n}</link>"
                   f"<description><![CDATA[<p>{descripcion}</p>]]></description>{fecha}</item>")
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>X</title>{cuerpo}</channel></rss>'.encode()


def test_lee_rss_y_atom():
    entradas = lector.leer_canal(_rss(("Beca &amp; premio", "Texto <b>con</b> etiquetas", HOY)))
    assert entradas[0].titulo == "Beca & premio"
    assert entradas[0].texto == "Texto con etiquetas" and entradas[0].publicado == HOY

    atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Fondo solar</title>'
            b'<link href="https://ejemplo.org/a"/><summary>Cierre: 2026-10-30</summary>'
            b'<updated>2026-09-20T10:00:00Z</updated></entry></feed>')
    entrada = lector.leer_canal(atom)[0]
    assert entrada.enlace == "https://ejemplo.org/a" and entrada.publicado == date(2026, 9, 20)

    with pytest.raises(ValueError, match="no es un canal"):
        lector.leer_canal(b"<html><body>Hola</body></html>")
    with pytest.raises(ValueError, match="no es un canal"):
        lector.leer_canal(b"no es xml")


def test_cache_reutiliza_y_respalda_fallas(tmp_path):
    llamadas = []

    def responder(request):
        llamadas.append(request)
        return httpx.Response(200, content=b"<rss/>")

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    primera = lector.descargar("https://ejemplo.org/feed", cliente, tmp_path)
    segunda = lector.descargar("https://ejemplo.org/feed", cliente, tmp_path)
    assert not primera.desde_cache and segunda.desde_cache and len(llamadas) == 1

    caido = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    respaldo = lector.descargar("https://ejemplo.org/feed", caido, tmp_path, usar_cache=False)
    assert respaldo.desde_cache and "HTTP 503" in respaldo.aviso
    with pytest.raises(httpx.HTTPStatusError):
        lector.descargar("https://ejemplo.org/otro", caido, tmp_path)


def test_fuentes_incluidas_tienen_canal_https():
    catalogo = leer_catalogo(FUENTES_INCLUIDAS)
    assert len(catalogo.fuentes) >= 4
    assert all(f.rss.startswith("https://") for f in catalogo.fuentes)


def test_fuentes_del_espacio_se_suman_o_reemplazan(tmp_path):
    (tmp_path / "fuentes.yaml").write_text(
        "temas: [wind power]\n"
        "fuentes:\n"
        "  - {nombre: Portal propio, url: 'https://propio.org/'}\n", encoding="utf-8")
    catalogo = cargar_catalogo(tmp_path)
    nombres = [f.nombre for f in catalogo.fuentes]
    assert "Portal propio" in nombres and "fundsforNGOs" in nombres
    assert catalogo.temas == ["wind power"]

    (tmp_path / "fuentes.yaml").write_text(
        "solo_propias: true\nfuentes:\n  - {nombre: Solo esta, rss: 'https://propio.org/feed'}\n",
        encoding="utf-8")
    assert [f.nombre for f in cargar_catalogo(tmp_path).fuentes] == ["Solo esta"]

    (tmp_path / "fuentes.yaml").write_text("fuentes:\n  - {nombre: Mala, rss: 'ftp://x'}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fuentes.yaml no es válido"):
        cargar_catalogo(tmp_path)


# --- Monitoreo completo -------------------------------------------------------------------------


def _espacio(tmp_path, extra: str = "") -> None:
    (tmp_path / "fuentes.yaml").write_text(
        "solo_propias: true\n"
        "fuentes:\n"
        "  - {nombre: Portal A, rss: 'https://a.org/feed'}\n"
        "  - {nombre: Portal caído, rss: 'https://caido.org/feed'}\n"
        "  - {nombre: Portal sin canal, url: 'https://manual.org/'}\n" + extra,
        encoding="utf-8")


def _feed_a(hoy: date) -> bytes:
    def cierre(dias: int) -> str:
        return (hoy + timedelta(days=dias)).isoformat()

    reciente = hoy - timedelta(days=2)
    return _rss(
        ("Community wind energy fund", f"Deadline: {cierre(40)}. Grants for cooperatives.", reciente),
        ("Solar energy grants", f"Fecha límite: {cierre(20)}.", reciente),
        ("Energy access award", f"Cierre: {cierre(3)}.", reciente),
        ("Energy research call", "Open call for energy research.", reciente),
        ("Wind energy innovation prize", f"Deadline: {cierre(-5)}.", reciente),
        ("Energy fund 2024", f"Deadline: {cierre(30)}.", hoy - timedelta(days=400)),
        ("Arts festival", f"Deadline: {cierre(30)}.", reciente),
    )


def _transporte(hoy: date, peticiones: list):
    def responder(request: httpx.Request):
        peticiones.append(request)
        if request.url.host == "a.org":
            return httpx.Response(200, content=_feed_a(hoy))
        if request.url.host == "buscador.local":
            return httpx.Response(200, json={"results": [
                {"title": "Convocatoria energía eólica comunitaria", "url": "https://gob.example/eolica",
                 "content": f"Fecha límite: {(hoy + timedelta(days=60)).isoformat()}."},
            ]})
        return httpx.Response(500)
    return httpx.MockTransport(responder)


def test_monitoreo_prioriza_marca_vigencia_y_separa_cerradas(tmp_path):
    _espacio(tmp_path)
    peticiones: list = []
    cliente = httpx.Client(transport=_transporte(HOY, peticiones))
    r = monitoring.monitorear(["Energía eólica comunitaria"], HOY, tmp_path, cliente=cliente)

    titulos = [a.titulo for a in r.priorizadas]
    # Tema completo primero; luego con fecha y tiempo suficiente; sin fecha antes que urgente.
    assert titulos == ["Community wind energy fund", "Solar energy grants", "Energy research call"]
    assert r.priorizadas[0].plazo == "Faltan 40 días. Cierre: 2026-11-06"
    assert r.priorizadas[2].plazo == "VIGENCIA NO VERIFICADA"
    assert [a.titulo for a in r.por_revisar] == ["Energy access award"]
    assert "URGENTE" in r.por_revisar[0].plazo
    assert [a.titulo for a in r.cerradas] == ["Wind energy innovation prize"]
    assert r.antiguos == 1 and r.leidos == 7
    assert r.fallidas == [("Portal caído", "HTTP 500")]
    assert [f.nombre for f in r.manuales] == ["Portal sin canal"]
    # Solo se consultan los canales; no viaja ningún dato del perfil.
    assert {p.url.host for p in peticiones} == {"a.org", "caido.org"}


def test_buscador_solo_recibe_los_temas(tmp_path):
    _espacio(tmp_path, "buscador: 'http://buscador.local'\n")
    peticiones: list = []
    cliente = httpx.Client(transport=_transporte(HOY, peticiones))
    r = monitoring.monitorear(["Energía eólica"], HOY, tmp_path, cliente=cliente)
    consulta = next(p for p in peticiones if p.url.host == "buscador.local")
    assert dict(consulta.url.params) == {"q": "convocatoria Energía eólica", "format": "json"}
    assert "Convocatoria energía eólica comunitaria" in [a.titulo for a in r.priorizadas]


def test_monitoreo_sin_temas(tmp_path):
    _espacio(tmp_path)
    with pytest.raises(ValueError, match="No hay temas"):
        monitoring.monitorear([], HOY, tmp_path, cliente=httpx.Client(transport=_transporte(HOY, [])))


# --- CLI ----------------------------------------------------------------------------------------


def test_cli_monitorear(entorno_aislado, monkeypatch):
    from coopexecutive.utils.fechas import hoy_local

    hoy = hoy_local("America/Mexico_City")
    _espacio(entorno_aislado)
    monkeypatch.setattr(monitoring, "nuevo_cliente",
                        lambda: httpx.Client(transport=_transporte(hoy, [])))
    res = CliRunner().invoke(cli, ["monitorear"], env={"COLUMNS": "200"})
    assert res.exit_code == 0, res.output
    assert "Energía comunitaria" in res.output  # tema del perfil
    assert "Priorizadas" in res.output and "Community wind energy fund" in res.output
    assert "Cerradas" in res.output and "VIGENCIA NO VERIFICADA" in res.output
    assert "No se pudo consultar Portal caído: HTTP 500" in res.output
    assert "Portal sin canal" in res.output
    assert (entorno_aislado / ".cache" / "monitoreo").is_dir()

    res = CliRunner().invoke(cli, ["monitorear", "--tema", "salud materna"], env={"COLUMNS": "200"})
    assert "Ningún aviso coincide" in res.output and "Arts festival" not in res.output
