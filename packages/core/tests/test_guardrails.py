from datetime import date

from coopexecutive.guardrails import LEYENDA_BORRADOR, agregar_leyenda, pendiente, revisar_respuesta

HOY = date(2026, 9, 27)


def test_marcador_pendiente():
    assert pendiente(" misión ") == "[PENDIENTE: misión]"


def test_monto_con_respaldo_no_se_senala():
    rev = revisar_respuesta("El apoyo es de $250,000 MXN.", "La convocatoria ofrece 250,000 pesos.")
    assert rev.limpia


def test_monto_sin_respaldo_se_senala_y_en_estricto_se_sustituye():
    texto = "Solicite 1,500,000 MXN al fondo."
    rev = revisar_respuesta(texto, "Sin montos en las bases.")
    assert rev.texto == texto
    assert any("Monto sin respaldo" in o for o in rev.observaciones)
    estricto = revisar_respuesta(texto, "Sin montos en las bases.", estricto=True)
    assert estricto.texto == "Solicite MONTO POR DEFINIR al fondo."


def test_fechas_sin_respaldo():
    rev = revisar_respuesta("Cierra el 15 de octubre de 2026 y hay junta el 2026-10-20.", "", estricto=True)
    assert rev.texto.count("[PENDIENTE: fecha]") == 2
    assert len(rev.observaciones) == 2


def test_fecha_con_respaldo_o_de_hoy():
    contexto = "Fecha de cierre: 15/10/2026."
    assert revisar_respuesta("Cierra el 15 de octubre de 2026.", contexto).limpia
    assert revisar_respuesta("Hoy es 27 de septiembre de 2026.", "", hoy=HOY).limpia


def test_emojis_extension_y_contrapunto():
    rev = revisar_respuesta("Recomiendo APLICAR ✅ " + "palabra " * 950, "")
    textos = " ".join(rev.observaciones)
    assert "emojis" in textos
    assert "palabras" in textos
    assert "CONTRAPUNTO" in textos
    assert revisar_respuesta("Recomiendo APLICAR.\n\nCONTRAPUNTO: el plazo es corto.", "").limpia


def test_afirmar_acciones_no_ejecutadas():
    rev = revisar_respuesta("El financiador quedó registrado en la base.", "")
    assert any("no se ejecutó" in o for o in rev.observaciones)
    assert revisar_respuesta("El financiador quedó registrado.", "", acciones_ejecutadas=True).limpia


def test_leyenda_idempotente():
    una = agregar_leyenda("Texto")
    assert una.endswith(LEYENDA_BORRADOR)
    assert agregar_leyenda(una) == una
