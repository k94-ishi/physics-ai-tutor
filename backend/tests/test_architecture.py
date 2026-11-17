"""Layering rules from AGENTS.md, checked on the source tree ([59])."""

import ast
import re
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
    """A session comes from `get_db` or `background_session` ([69]).

    Only `database/`, and script entry points (`cli/`, `database/seed.py`),
    may touch the session factory; everything else takes a session.
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
            if name.endswith(("SessionLocal", "sessionmaker", "async_sessionmaker"))
        ]
        if bad:
            offenders[str(path.relative_to(PACKAGE))] = bad
    assert offenders == {}


# Sync SQLAlchemy entry points; the app is async only since [110].
SYNC_SQLALCHEMY = {
    "sqlalchemy.orm.Session",
    "sqlalchemy.orm.sessionmaker",
    "sqlalchemy.orm.scoped_session",
    "sqlalchemy.create_engine",
    "sqlalchemy.engine.create_engine",
}


def test_the_app_has_no_sync_database_access():
    """The end state of Track F ([73], [99]): one async stack, nothing else.

    Anywhere in the package, `database/` included. Alembic (outside the
    package) keeps its own sync engine for migrations, and tests build a
    sync engine to arrange rows; neither is scanned here.
    """
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        bad = sorted(set(_imports(ast.parse(path.read_text()))) & SYNC_SQLALCHEMY)
        if bad:
            offenders[str(path.relative_to(PACKAGE))] = bad
    assert offenders == {}


def test_no_sync_llm_client_exists():
    """OpenAI and DeepSeek are called only through `AsyncOpenAI` ([108]).

    A sync SDK call inside an `async def` would block the event loop -
    worse than the thread it used to occupy, because it stops every other
    request too. Until [108] this pinned the two modules that still did.
    """
    users = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        source = path.read_text()
        names = _imports(ast.parse(source))
        imports_sync_sdk = any(name == "openai.OpenAI" for name in names)
        imports_sync_client = any(
            name.endswith((".deepseek.client", ".openai.client")) for name in names
        )
        calls_sync_client = re.search(
            r"(?<!async_)\bclient\.(chat|embeddings)\b", source
        )
        if imports_sync_sdk or imports_sync_client or calls_sync_client:
            users.add(str(path.relative_to(PACKAGE)))

    assert users == set(), f"sync LLM client in: {sorted(users)}"


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
    # A sync SQLAlchemy import is spotted by the end-state rule.
    sync = ast.parse("from sqlalchemy.orm import Session\nimport sqlalchemy\n")
    assert "sqlalchemy.orm.Session" in set(_imports(sync)) & SYNC_SQLALCHEMY


# Functions that leave the process to talk to an LLM provider, directly
# or through one hop. Name-based on purpose: a connection held across any
# of these is a connection spent waiting on something the database has no
# part in ([82]).
LLM_CALLS = {
    # The provider seams.
    "_request",
    "_request_embeddings",
    "generate_answer",
    "chat_completion",
    "stream_answer",
    "create_embeddings",
    "embed_many",
    "embed_query",
    "translate_qa",
    "extract_concept_names",
    "grade_answer",
    # One hop: use cases and prepare halves that call a seam ([82], [99]).
    "_build_sense",
    "_generate",
    "_prepare_approval",
    "_prepare_concepts",
    "_prepare_create",
    "_prepare_edit",
    "_prepare_import_concepts",
    "_prepare_import_translations",
    "_prepare_translation",
    "_reextract_one",
    "_resolve_sense",
    "_stream_generation",
    "_tag_names",
    "attach_concepts",
    "fetch_question",
    "generate_rag_answer",
    "grade_cases",
    "prepare_concepts",
    "prepare_refresh",
    "prepare_translation",
    "review_question",
    "save_ai_question",
    "search_similar_questions",
    "stream_rag_answer",
    "translate_missing",
    "translate_missing_languages",
    "translate_missing_name",
    "update_question",
}


def _llm_calls_inside_transactions(tree: ast.AST) -> dict[str, list[str]]:
    """{function: [offending call ...]} for one module."""

    def call_name(call: ast.Call) -> str | None:
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        if isinstance(call.func, ast.Name):
            return call.func.id
        return None

    offenders: dict[str, list[str]] = {}
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for block in ast.walk(function):
            if not isinstance(block, ast.With | ast.AsyncWith):
                continue
            in_transaction = any(
                isinstance(item.context_expr, ast.Call)
                and call_name(item.context_expr) in {"transaction"}
                for item in block.items
            )
            if not in_transaction:
                continue
            for inner in block.body:
                for node in ast.walk(inner):
                    if isinstance(node, ast.Call):
                        name = call_name(node)
                        if name in LLM_CALLS:
                            offenders.setdefault(function.name, []).append(
                                f"{name} (line {node.lineno})"
                            )
    return offenders


def test_no_transaction_spans_an_llm_call():
    """A transaction block must not wait on OpenAI or DeepSeek ([82]).

    Holding a pooled connection across a multi-second network call is
    what capped the backend at ~15 concurrent operations once threads no
    longer did. The check is lexical (direct calls only), so it is a
    tripwire rather than proof - the runtime guarantees live in
    tests/test_llm_connection_discipline.py.
    """
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        found = _llm_calls_inside_transactions(ast.parse(path.read_text()))
        relative = str(path.relative_to(PACKAGE))
        for function, calls in found.items():
            offenders[f"{relative}:{function}"] = calls
    assert offenders == {}


def test_the_llm_transaction_check_catches_a_violation():
    sample = ast.parse(
        "def f(db):\n"
        "    with transaction(db, 'x'):\n"
        "        deepseek_service.generate_answer(a, b)\n"
        "async def g(db):\n"
        "    async with transaction(db, 'x'):\n"
        "        await embedding_service.create_embeddings(t)\n"
    )
    found = _llm_calls_inside_transactions(sample)
    assert "f" in found and "g" in found


def test_services_use_no_threading_primitives():
    """Background work is asyncio, not threads ([72]).

    A lock or thread-local in a service is a sign that something is
    coordinating across threads, which the event loop makes both
    unnecessary and misleading - it holds inside one process only, and
    [75] is where cross-process claims belong.
    """
    offenders = {}
    for path in _modules("services"):
        names = _imports(ast.parse(path.read_text()))
        bad = [
            name
            for name in names
            if name == "threading" or name.startswith("threading.")
        ]
        if bad:
            offenders[path.name] = bad
    assert offenders == {}


def test_every_background_task_target_is_async():
    """`add_task` must be handed a coroutine function ([72]).

    A sync target runs on the anyio thread pool, which is what [68]
    measured competing with request handling; one left behind would
    quietly reintroduce that.
    """
    targets: list[tuple[str, str]] = []
    for path in _modules("api"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_task"
                and node.args
            ):
                first = node.args[0]
                if isinstance(first, ast.Attribute):
                    targets.append((first.value.id, first.attr))

    assert targets, "no background tasks found; has the scan broken?"

    # Resolve each target in its service module and check it is `async def`.
    not_async = []
    for module_name, function_name in targets:
        candidates = list(PACKAGE.joinpath("services").glob(f"{module_name}.py"))
        assert candidates, f"cannot locate service module {module_name}"
        tree = ast.parse(candidates[0].read_text())
        found = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == function_name
        ]
        assert found, f"{module_name}.{function_name} not found"
        if not isinstance(found[0], ast.AsyncFunctionDef):
            not_async.append(f"{module_name}.{function_name}")

    assert not_async == []


def test_services_keep_no_mutable_module_state():
    """Cross-request state belongs in the database, not a module ([75]).

    A module-level set or dict is per-process, so with more than one
    worker each gets its own copy and they silently disagree - which is
    exactly how background translation could do the same row twice. Read
    only lookup tables (uppercase names) are fine.
    """
    offenders: dict[str, list[str]] = {}
    for path in _modules("services"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign | ast.AnnAssign):
                continue
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            # Constants are conventionally uppercase and treated as frozen.
            mutable_names = [name for name in names if not name.isupper()]
            if not mutable_names:
                continue
            value = node.value
            is_container = isinstance(value, ast.Dict | ast.List | ast.Set) or (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in {"set", "dict", "list"}
            )
            if is_container:
                offenders.setdefault(path.name, []).extend(mutable_names)

    # `_preloaded` holds seed vectors for the offline seed: filled by the
    # seed script and read in the same process, never shared across one.
    # Names only, so moving a line does not fail the test.
    allowed = {"embedding_service.py": ["_preloaded"]}
    assert offenders == allowed
