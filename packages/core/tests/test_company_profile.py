from pathlib import Path

from coopexecutive.memory.company_profile import CoopProfile


def test_coop_profile_defaults():
    profile = CoopProfile()
    assert profile.name == "Organización de Economía Social"
    assert profile.statutory_funds.reserve_fund_pct == 15.0
    assert profile.statutory_funds.social_welfare_fund_pct == 10.0
    assert profile.statutory_funds.education_fund_pct == 10.0


def test_coop_profile_yaml_loading(tmp_path: Path):
    yaml_content = """name: "Cooperativa de Prueba"
legal_structure: "S.C. de R.L."
regime: "Economía Social"
mission: "Impulsar el bienestar común."
values:
  - "Solidaridad"
  - "Democracia"
"""
    yaml_file = tmp_path / "test_profile.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    profile = CoopProfile.load_from_yaml(yaml_file)
    assert profile.name == "Cooperativa de Prueba"
    assert profile.legal_structure == "S.C. de R.L."
    assert "Solidaridad" in profile.values

    block = profile.to_prompt_block()
    assert "Cooperativa de Prueba" in block
    assert "Fondo de Reserva: 15.0%" in block


def test_coop_profile_conserva_campos_opcionales(tmp_path: Path):
    yaml_file = tmp_path / "perfil.yaml"
    yaml_file.write_text(
        'name: "A.C. de Prueba"\n'
        'target_communities: ["Escuelas rurales"]\n'
        'focus_areas: ["Agua segura"]\n'
        'funding_sources: ["Fundaciones"]\n',
        encoding="utf-8",
    )
    profile = CoopProfile.load_from_yaml(yaml_file)
    assert profile.target_communities == ["Escuelas rurales"]
    assert profile.focus_areas == ["Agua segura"]
    assert profile.funding_sources == ["Fundaciones"]

    block = profile.to_prompt_block()
    assert "### Ejes de Trabajo:" in block
    assert "- Agua segura" in block
    assert "- Escuelas rurales" in block
    assert "- Fundaciones" in block


def test_coop_profile_omite_secciones_vacias():
    block = CoopProfile().to_prompt_block()
    assert "Ejes de Trabajo" not in block
    assert "Fuentes de Financiamiento" not in block


def test_plantillas_de_company_cargan():
    raiz = Path(__file__).resolve().parents[3] / "company"
    for yaml_file in [raiz / "profile.yaml", *sorted((raiz / "templates").glob("*.yaml"))]:
        assert yaml_file.exists(), yaml_file
        assert CoopProfile.load_from_yaml(yaml_file).name, yaml_file.name
