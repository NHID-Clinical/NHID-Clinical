"""
requirements.txt describes what is actually installed
=====================================================
Every dependency was declared with an unbounded floor (`fastapi>=0.110.0`), so
`pip install -r requirements.txt` resolved to whatever was newest on the day it
ran. Two consequences, both silent:

* a breaking major release would change what CI and the Docker image execute,
  with nothing failing to say so;
* the versions actually exercised had drifted far past the declared floors —
  openai two majors (1 → 3), cryptography nine (41 → 50), pytest and reportlab
  one each — so the file documented a range nobody had tested.

Upper bounds fix the first. This file fixes the second: it asserts the
*installed* set satisfies the *declared* ranges, so a bound cannot drift out of
step with what CI resolves, in either direction. Raising a bound now requires
the suite to pass under the new major, which is the point.

It deliberately does not pin exact versions. That would be a lockfile, and a
lockfile this project does not regenerate would rot faster than the bounds do.
"""
import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"

#: Distributions whose import name differs from their package name, or which are
#: pulled in for a framework rather than imported directly.
_NOT_IMPORTED_DIRECTLY = {
    # FastAPI needs it to parse the Twilio form posts app.py receives.
    "python-multipart",
    # Reached through fastapi.templating.Jinja2Templates in webplatform/app.py,
    # never imported by name. It was declared only in webplatform/requirements.txt,
    # so a clean root install collected webplatform/tests and ran nothing.
    "jinja2",
    # A pytest plugin, activated by the asyncio marker rather than imported.
    # It was dead weight until tests/test_llm_client.py gave the suite its
    # first async tests; pytest.ini had set asyncio_mode for a suite with none.
    "pytest-asyncio",
}

_SPEC = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<constraints>.*)$"
)
_CONSTRAINT = re.compile(r"(?P<op><=|>=|==|!=|~=|<|>)\s*(?P<version>[\w.*+!-]+)")


def _parse_version(text: str) -> tuple:
    """Compare versions by numeric components, ignoring any suffix.

    Enough for the bounds this file declares (all plain `major.minor.patch` or
    a bare date), and avoids depending on `packaging` just for a test.
    """
    parts = []
    for chunk in re.split(r"[.\-+]", text):
        digits = re.match(r"\d+", chunk)
        parts.append(int(digits.group()) if digits else 0)
    return tuple(parts)


def _requirements() -> list[tuple[str, list[tuple[str, str]]]]:
    entries = []
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _SPEC.match(line)
        assert match, f"could not parse requirement line: {raw!r}"
        name = match.group("name")
        constraints = _CONSTRAINT.findall(match.group("constraints"))
        entries.append((name, [(op, ver) for op, ver in constraints]))
    return entries


REQUIREMENT_ENTRIES = _requirements()


def test_the_requirements_file_parses_and_is_not_empty():
    assert REQUIREMENT_ENTRIES, "no requirements parsed"
    names = [name for name, _ in REQUIREMENT_ENTRIES]
    assert len(names) == len(set(names)), f"duplicate requirement: {names}"


@pytest.mark.parametrize("name,constraints", REQUIREMENT_ENTRIES,
                         ids=[n for n, _ in REQUIREMENT_ENTRIES])
def test_every_declared_dependency_is_installed(name, constraints):
    """A declared dependency that is not installed means the suite is passing
    on something other than what it says it needs."""
    try:
        version(name)
    except PackageNotFoundError:
        pytest.fail(f"{name} is declared in requirements.txt but not installed")


@pytest.mark.parametrize("name,constraints", REQUIREMENT_ENTRIES,
                         ids=[n for n, _ in REQUIREMENT_ENTRIES])
def test_the_installed_version_satisfies_the_declared_range(name, constraints):
    """Catches a bound that excludes what CI actually resolves — in both
    directions. A floor raised above the installed version, or a ceiling that
    the resolver has already passed, fails here rather than in a deploy."""
    installed = _parse_version(version(name))
    for op, bound_text in constraints:
        bound = _parse_version(bound_text)
        if op == ">=":
            assert installed >= bound, (
                f"{name} {version(name)} is below its declared floor {bound_text}"
            )
        elif op == ">":
            assert installed > bound
        elif op == "<":
            assert installed < bound, (
                f"{name} {version(name)} is at or above its declared ceiling "
                f"{bound_text}; the suite has not been verified on this major"
            )
        elif op == "<=":
            assert installed <= bound
        elif op == "==":
            assert installed == bound


@pytest.mark.parametrize("name,constraints", REQUIREMENT_ENTRIES,
                         ids=[n for n, _ in REQUIREMENT_ENTRIES])
def test_every_dependency_has_an_upper_bound(name, constraints):
    """The actual defect: without one, a breaking major lands unannounced.

    `pdfminer.six` is exempt — it versions by date (`20231228`), so "the next
    major" is not a meaningful boundary.
    """
    if name == "pdfminer.six":
        return  # versions by date; "the next major" is not meaningful
    operators = {op for op, _ in constraints}
    assert operators & {"<", "<=", "=="}, (
        f"{name} has no upper bound, so `pip install -r requirements.txt` can "
        f"resolve it to a future major that nothing here has executed"
    )


def test_declared_dependencies_are_actually_imported_somewhere():
    """A dependency nothing imports is either dead weight or, worse, a
    capability the project believes it has and does not use.

    `jsonschema` was exactly that: declared, never imported, while two
    published JSON Schemas went unvalidated. It is covered now, and this test
    keeps the file honest about the rest.
    """
    import_names = {
        "pyyaml": "yaml",
        "PyJWT": "jwt",
        "pdfminer.six": "pdfminer",
        "python-dotenv": "dotenv",
    }
    sources = []
    for pattern in ("*.py", "src/*.py", "functions/*.py", "adapters/*.py",
                    "tests/*.py", "scripts/*.py", "experiments/*/*.py",
                    "webplatform/*.py", "docs/pilot-kit/*.py", "examples/*.py"):
        for path in ROOT.glob(pattern):
            sources.append(path.read_text(encoding="utf-8", errors="ignore"))
    corpus = "\n".join(sources)

    unused = []
    for name, _constraints in REQUIREMENT_ENTRIES:
        if name in _NOT_IMPORTED_DIRECTLY:
            continue
        module = import_names.get(name, name.replace("-", "_"))
        if not re.search(rf"^\s*(import|from)\s+{re.escape(module)}\b",
                         corpus, re.MULTILINE):
            unused.append(f"{name} (as {module})")
    assert not unused, (
        "declared but imported nowhere: " + ", ".join(unused)
    )
