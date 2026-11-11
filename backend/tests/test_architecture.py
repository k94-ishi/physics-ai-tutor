"""Layering rules from AGENTS.md, checked on the source tree ([59])."""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "physics_ai_tutor"

# Session methods that touch the database or the transaction.
SESSION_CALLS = {
    "query",
    "get",
    "add",
    "add_all",
    "delete",
    "execute",
    "flush",
    "refresh",
    "commit",
    "rollback",
}
FORBIDDEN_IN_ROUTERS = (
    "physics_ai_tutor.repositories",
    "physics_ai_tutor.database.database",
    "physics_ai_tutor.database.session",
)


def _modules(*parts: str) -> list[Path]:
    return sorted(PACKAGE.joinpath(*parts).rglob("*.py"))


def _imports(tree: ast.AST) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names += [node.module] + [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            names += [a.name for a in node.names]
    return names


def _session_calls(tree: ast.AST, methods: set[str]) -> list[str]:
    """Calls such as `db.query(...)` or `session.commit()`."""
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"db", "session"}
            and node.func.attr in methods
        ):
            found.append(f"{node.func.value.id}.{node.func.attr} (line {node.lineno})")
    return found


def test_routers_call_services_only():
    offenders = {}
    for path in _modules("api"):
        tree = ast.parse(path.read_text())
        bad = [n for n in _imports(tree) if n.startswith(FORBIDDEN_IN_ROUTERS)]
        bad += _session_calls(tree, SESSION_CALLS)
        if bad:
            offenders[path.name] = bad
    assert offenders == {}


def test_only_the_transaction_helper_commits_or_rolls_back():
    allowed = PACKAGE / "database" / "transaction.py"
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        if path == allowed:
            continue
        bad = _session_calls(ast.parse(path.read_text()), {"commit", "rollback"})
        if bad:
            offenders[str(path.relative_to(PACKAGE))] = bad
    assert offenders == {}


def test_only_the_database_layer_builds_sessions():
    """A session comes from a dependency or a `*_background_session` ([69]).

    Both stacks coexist during Track F ([67]); whichever a module uses, it
    must not instantiate its own factory. [73] tightens this further by
    forbidding the sync factory outside `cli/`.
    """
    allowed = {
        PACKAGE / "database" / "database.py",
        PACKAGE / "database" / "dependency.py",
        PACKAGE / "database" / "session.py",
        # Script entry points own their session, as the CLIs do.
        PACKAGE / "database" / "seed.py",
    }
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        if path in allowed or path.parts[-2] == "cli":
            continue
        names = _imports(ast.parse(path.read_text()))
        bad = [
            name
            for name in names
            if name.endswith(("SessionLocal", "AsyncSessionLocal"))
            or name.endswith(("sessionmaker", "async_sessionmaker"))
        ]
        if bad:
            offenders[str(path.relative_to(PACKAGE))] = bad
    assert offenders == {}


def test_async_code_never_uses_the_sync_transaction_helper():
    """An `async def` that commits must use `async_transaction` ([69]).

    `transaction()` on an `AsyncSession` would call `commit()` without
    awaiting it: the block would look fine and write nothing.
    """
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for inner in ast.walk(node):
                # `with transaction(...)` inside async code, not `async with`.
                if isinstance(inner, ast.With):
                    for item in inner.items:
                        call = item.context_expr
                        if (
                            isinstance(call, ast.Call)
                            and isinstance(call.func, ast.Name)
                            and call.func.id == "transaction"
                        ):
                            offenders.setdefault(
                                str(path.relative_to(PACKAGE)), []
                            ).append(f"{node.name} (line {inner.lineno})")
    assert offenders == {}


def test_the_checks_catch_a_violation():
    # Guards against the rules above silently matching nothing.
    sample = ast.parse("from physics_ai_tutor.repositories import x\ndb.commit()\n")
    assert _imports(sample)[0].startswith(FORBIDDEN_IN_ROUTERS)
    assert _session_calls(sample, {"commit"}) == ["db.commit (line 2)"]
    # An awaited commit is still a commit.
    awaited = ast.parse("async def f(db):\n    await db.commit()\n")
    assert _session_calls(awaited, {"commit"}) == ["db.commit (line 2)"]
    # A session factory import is spotted wherever it comes from.
    factory = ast.parse("from physics_ai_tutor.database.database import SessionLocal\n")
    assert any(name.endswith("SessionLocal") for name in _imports(factory))
