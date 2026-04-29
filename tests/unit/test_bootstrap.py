from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_required_package_directories_exist() -> None:
    packages = [
        "contracts",
        "config",
        "ingestion",
        "chunker",
        "llm",
        "planner",
        "executor",
        "critic",
        "verifier",
        "reconciler",
        "reporter",
        "orchestrator",
        "audit",
        "cli",
        "evals",
    ]

    for package in packages:
        path = ROOT / "src" / "extractor" / package
        assert path.is_dir()
        assert (path / "__init__.py").is_file()


def test_pyproject_declares_required_dependencies() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = set(pyproject["project"]["dependencies"])

    required_prefixes = {
        "anthropic",
        "openai",
        "pydantic",
        "aiosqlite",
        "structlog",
        "pyyaml",
        "tiktoken",
        "pytest",
        "pytest-asyncio",
        "pdfplumber",
    }

    normalized = {dependency.split(">=")[0] for dependency in dependencies}
    assert required_prefixes <= normalized


def test_makefile_exposes_required_targets() -> None:
    makefile = (ROOT / "Makefile").read_text()

    for target in ("test:", "lint:", "smoke:"):
        assert target in makefile
