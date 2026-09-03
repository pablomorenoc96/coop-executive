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
