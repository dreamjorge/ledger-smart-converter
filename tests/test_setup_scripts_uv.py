from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_setup_env_ps1_uses_uv_for_env_creation_and_dependency_install() -> None:
    content = read_repo_file("scripts/setup_env.ps1")

    assert "uv venv" in content
    assert "uv pip install" in content
    assert "uv pip sync" not in content
    assert "python -m venv" not in content
    assert "-m pip install" not in content


def test_setup_env_sh_uses_uv_for_env_creation_and_dependency_install() -> None:
    content = read_repo_file("scripts/setup_env.sh")

    assert "uv venv" in content
    assert "uv pip install" in content
    assert "uv pip sync" not in content
    assert "python -m venv" not in content
    assert "-m pip install" not in content


def test_runner_scripts_reference_uv_setup_in_error_messages() -> None:
    for relative_path in (
        "scripts/run.ps1",
        "scripts/run_web.ps1",
        "scripts/run_hsbc_example.ps1",
        "scripts/run_flet.ps1",
    ):
        content = read_repo_file(relative_path)
        assert "setup_env.ps1" in content
        assert "uv" in content.lower()
