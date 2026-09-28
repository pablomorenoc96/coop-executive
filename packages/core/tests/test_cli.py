from click.testing import CliRunner

from coopexecutive.cli import cli


def invocar(*args: str):
    return CliRunner().invoke(cli, list(args))


def test_info_muestra_perfil_activo(entorno_aislado):
    res = invocar("info")
    assert res.exit_code == 0, res.output
    assert "Cooperativa de Prueba" in res.output
    assert "Energía comunitaria" in res.output


def test_propuesta_y_listado(entorno_aislado):
    res = invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    assert res.exit_code == 0, res.output
    assert "Propuesta registrada" in res.output
    assert "#1" in res.output

    res = invocar("propuestas")
    assert res.exit_code == 0, res.output
    assert "Fondo eolico" in res.output
    assert "ABIERTA" in res.output


def test_propuestas_sin_registros(entorno_aislado):
    res = invocar("propuestas")
    assert res.exit_code == 0, res.output
    assert "No hay propuestas" in res.output


def test_propuesta_prohibida_muestra_error(entorno_aislado):
    res = invocar("propuesta", "Venta", "-d", "Vender acciones de la cooperativa.")
    assert res.exit_code == 0, res.output
    assert "Error Estatutario" in res.output
    assert "No hay propuestas" in invocar("propuestas").output


def test_votar_y_escrutinio(entorno_aislado):
    invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    for socio, voto in [("S1", "a_favor"), ("S2", "A_FAVOR"), ("S3", "EN_CONTRA")]:
        res = invocar("votar", "1", "-s", socio, "-n", f"Socio {socio}", "-v", voto)
        assert res.exit_code == 0, res.output
        assert "Voto Recibida" in res.output

    duplicado = invocar("votar", "1", "-s", "S1", "-n", "Socio S1", "-v", "EN_CONTRA")
    assert "Rechazo de Cédula" in duplicado.output

    res = invocar("escrutinio", "1", "--padron", "5")
    assert res.exit_code == 0, res.output
    assert "APROBADA" in res.output
    assert "SHA256:" in res.output


def test_escrutinio_sin_cuorum_rechaza(entorno_aislado):
    invocar("propuesta", "Fondo eolico", "-d", "Aprobar la contrapartida del proyecto.")
    invocar("votar", "1", "-s", "S1", "-n", "Socio S1", "-v", "A_FAVOR")
    res = invocar("escrutinio", "1", "--padron", "12")
    assert res.exit_code == 0, res.output
    assert "RECHAZADA" in res.output


def test_escrutinio_propuesta_inexistente(entorno_aislado):
    res = invocar("escrutinio", "99")
    assert res.exit_code == 0, res.output
    assert "no existe" in res.output
