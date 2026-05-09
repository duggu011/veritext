from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_TERMS_PATH = (
    ROOT / "tests" / "fixtures" / "source_neutrality" / "phase_28_forbidden_runtime_terms.txt"
)
RUNTIME_ROOTS = (ROOT / "src", ROOT / "prompts")
RUNTIME_SUFFIXES = {".py", ".md"}


def test_phase28_legal_identifiers_do_not_enter_runtime_source_or_prompts() -> None:
    terms = tuple(
        line.strip()
        for line in FORBIDDEN_TERMS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )
    assert terms

    violations: list[str] = []
    for runtime_root in RUNTIME_ROOTS:
        for path in sorted(runtime_root.rglob("*")):
            if "__pycache__" in path.parts or path.suffix not in RUNTIME_SUFFIXES:
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for term in terms:
                    if term in line:
                        relative_path = path.relative_to(ROOT)
                        violations.append(f"{relative_path}:{line_number}: {term}")

    assert violations == []
