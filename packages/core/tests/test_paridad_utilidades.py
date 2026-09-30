"""Plazos, datos sensibles, etiquetas de origen, comparación de evaluaciones y búsqueda en el conocimiento."""
from datetime import date, timedelta

import pytest

from coopexecutive import knowledge
from coopexecutive.grant_tools import comparar, matrix
from coopexecutive.grant_tools.matrix import PESOS
from coopexecutive.guardrails.marcadores import etiqueta_de, pendiente
from coopexecutive.guardrails.sensibles import (
    CONTACTO_OMITIDO,
    DATO_BANCARIO_OMITIDO,
    IDENTIFICADOR_OMITIDO,
    censurar_datos_bancarios,
    contiene_dato_bancario,
    limpiar_datos_sensibles,
)
from coopexecutive.memory import onboarding
from coopexecutive.utils.plazos import leer_fecha, plazo

HOY = date(2026, 9, 27)


# --- Plazos --------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["2026-10-30", "30/10/2026", "30 de octubre de 2026", "30 de Octubre del 2026"])
def test_leer_fecha_admite_los_tres_formatos(texto):
    assert leer_fecha(texto) == date(2026, 10, 30)


def test_leer_fecha_rechaza_texto_libre():
    with pytest.raises(ValueError, match="no es una fecha"):
        leer_fecha("a fin de mes")


def test_plazo_urgente_hasta_trece_dias_y_vencido():
    assert plazo(HOY + timedelta(days=13), HOY).urgente
    assert not plazo(HOY + timedelta(days=14), HOY).urgente
    cierra_hoy = plazo(HOY, HOY)
    assert cierra_hoy.texto == "Cierra hoy (URGENTE)"
    vencido = plazo("2026-09-20", HOY)
    assert vencido.vencida and vencido.dias == -7 and vencido.texto == "Vencida"


def test_plazo_da_dia_de_la_semana():
    assert plazo("2026-09-28", HOY).fecha_larga.startswith("lunes 28 de septiembre de 2026")


# --- Datos sensibles -----------------------------------------------------------------


def test_censura_clabe_de_dieciocho_digitos():
    texto, n = censurar_datos_bancarios("Deposite a la CLABE 012 180 00123456789 1 antes del cierre.")
    assert n == 1 and DATO_BANCARIO_OMITIDO in texto and "0123" not in texto


def test_censura_tarjeta_solo_si_pasa_luhn():
    assert contiene_dato_bancario("Tarjeta 4111 1111 1111 1111")
    assert not contiene_dato_bancario("Folio 4111 1111 1111 1112")


def test_censura_iban_valido_y_respeta_uno_invalido():
    assert contiene_dato_bancario("IBAN ES91 2100 0418 4502 0005 1332")
    assert not contiene_dato_bancario("IBAN ES00 2100 0418 4502 0005 1332")


def test_limpiar_quita_rfc_curp_correo_gratuito_y_telefono_pero_no_cifras_de_impacto():
    texto = (
        "RFC ABC010203XY1, CURP GODE561231HDFRRN09, escriba a persona@gmail.com o al 55 1234 5678. "
        "Atendimos a 1,200 familias en 2025. Correo institucional: contacto@ejemplo.org."
    )
    limpio = limpiar_datos_sensibles(texto)
    assert "ABC010203XY1" not in limpio and "GODE561231" not in limpio
    assert limpio.count(IDENTIFICADOR_OMITIDO) == 2
    assert "persona@gmail.com" not in limpio and "1234 5678" not in limpio
    assert CONTACTO_OMITIDO in limpio
    assert "1,200 familias en 2025" in limpio and "contacto@ejemplo.org" in limpio


def test_onboarding_rechaza_cuentas_bancarias():
    with pytest.raises(ValueError, match="cuenta bancaria"):
        onboarding.aplicar_respuestas({"name": "X"}, {"mecanismos_cobro": "Transferencia a 012180001234567891"})


def test_etiquetas_y_marcador_pendiente():
    assert etiqueta_de("Dato público verificado") == "DATO PÚBLICO VERIFICADO"
    assert etiqueta_de("Propuesta del agente") == "INFERENCIA ESTRATÉGICA"
    assert pendiente("  monto ") == "[PENDIENTE: monto]"


# --- Comparación de evaluaciones -----------------------------------------------------


def _guardada(id_: int, dias: int, puntos: dict | None = None, **extra) -> matrix.EvaluacionGuardada:
    datos = {
        "convocatoria": f"Convocatoria {id_}",
        "financiador": "Fundación Ejemplo",
        "elegibilidad": "confirmada",
        "vigencia": "vigente",
        "fecha_cierre": (HOY + timedelta(days=dias)).isoformat(),
        "evidencia_plazo": "Bases.",
        "criterios": {c: {"puntos": (puntos or {}).get(c, p), "evidencia": "Bases."} for c, p in PESOS.items()},
        **extra,
    }
    resultado = matrix.evaluar(datos, hoy=HOY, rango_presupuesto_definido=True)
    return matrix.EvaluacionGuardada(id=id_, expediente_folio=None, resultado=resultado)


def test_comparar_prioriza_la_decision_y_luego_el_cierre():
    completa_lejana = _guardada(1, 60)
    completa_cercana = _guardada(2, 35)
    vencida = _guardada(3, -2)
    res = comparar.comparar([completa_lejana, completa_cercana, vencida], HOY)
    assert res.prioridad is not None and res.prioridad.id == 2
    assert [f.id for f in res.filas][-1] == 3 and res.filas[-1].descartada
    assert res.prioridad.plazo == "Faltan 35 días"


def test_comparar_el_orden_por_puntaje_no_cambia_la_prioridad():
    baja = _guardada(1, 40, puntos={c: 0 for c in PESOS})
    alta = _guardada(2, 90)
    por_plazo = comparar.comparar([baja, alta], HOY, "plazo")
    por_puntaje = comparar.comparar([baja, alta], HOY, "puntaje")
    assert por_plazo.prioridad.id == por_puntaje.prioridad.id
    assert por_puntaje.filas[0].id == 2


def test_comparar_sin_vigentes_no_elige_y_pide_dos():
    res = comparar.comparar([_guardada(1, -1), _guardada(2, -5)], HOY)
    assert res.prioridad is None and "vencidas o descartadas" in res.motivo
    with pytest.raises(ValueError, match="al menos dos"):
        comparar.comparar([_guardada(1, 10)], HOY)


# --- Conocimiento --------------------------------------------------------------------


def test_partir_respeta_encabezados():
    pasajes = knowledge.partir("# Becas\n\nOtorgamos becas.\n\n## Donativos\n\nRecibimos donativos.", "doc.md")
    assert [(p.titulo, p.texto) for p in pasajes] == [("Becas", "Otorgamos becas."), ("Donativos", "Recibimos donativos.")]


def test_buscar_encuentra_por_raiz_y_devuelve_vacio_sin_coincidencias():
    pasajes = knowledge.partir("## Programas\n\nBeca de estudios para jóvenes.\n\n## Otro\n\nNada que ver.", "x.md")
    encontrados = knowledge.buscar("¿Qué becas ofrecen?", pasajes)
    assert encontrados and encontrados[0].titulo == "Programas"
    assert knowledge.buscar("astronomía cuántica", pasajes) == []
    assert knowledge.buscar("de la el", pasajes) == []


def test_documentos_incluye_perfil_y_carpeta_del_espacio(tmp_path):
    carpeta = tmp_path / knowledge.CARPETA_ESPACIO
    carpeta.mkdir()
    (carpeta / "politicas.md").write_text("# Política de donativos\n\nSolo aceptamos donativos en especie.",
                                           encoding="utf-8")
    (carpeta / "imagen.png").write_bytes(b"\x89PNG")
    pasajes = knowledge.documentos(carpeta, "Nombre: Cooperativa Ejemplo")
    fuentes = {p.fuente for p in pasajes}
    assert "Perfil de la organización" in fuentes and "conocimiento/politicas.md" in fuentes
    assert not any(f.endswith(".png") for f in fuentes)
    assert knowledge.buscar("donativos en especie", pasajes)[0].fuente == "conocimiento/politicas.md"
