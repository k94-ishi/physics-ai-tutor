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


def test_the_sync_llm_clients_are_only_used_by_unconverted_code():
    """Pin who still calls OpenAI or DeepSeek synchronously ([70]).

    A sync SDK call inside an `async def` would block the event loop -
    worse than the thread it used to occupy, because it stops every other
    request too. This list may only shrink; [73] empties it.
    """
    # Exactly these two, so a new sync caller anywhere fails the test and
    # removing one is a deliberate edit here. Modules that call the *sync
    # service functions* (concept extraction, run grading, the eval) are
    # not listed: they are unconverted callers, not SDK users.
    expected = {
        "services/deepseek_service.py",
        "services/embedding_service.py",
    }
    users = set()
    for path in sorted(PACKAGE.rglob("*.py")):
        source = path.read_text()
        tree = ast.parse(source)
        names = _imports(tree)
        imports_sync_client = any(
            name.endswith((".deepseek.client", ".openai.client")) for name in names
        ) or any(
            name.endswith((".deepseek", ".openai"))
            and "client" in source
            and "async_client" not in source
            for name in names
        )
        # The services reach the clients through their own module import.
        if imports_sync_client or re.search(r"\bclient\.(chat|embeddings)\b", source):
            users.add(str(path.relative_to(PACKAGE)))

    assert users == expected, (
        f"new sync LLM caller(s): {sorted(users - expected)}; "
        f"no longer sync: {sorted(expected - users)}"
    )


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


# Functions that leave the process to talk to an LLM provider, directly
# or through one hop. Name-based on purpose: a connection held across any
# of these is a connection spent waiting on something the database has no
# part in ([82]).
LLM_CALLS = {
    "generate_answer",
    "async_generate_answer",
    "chat_completion",
    "async_chat_completion",
    "async_stream_answer",
    "create_embeddings",
    "async_create_embeddings",
    "translate_qa",
    "async_translate_qa",
    "extract_concept_names",
    "async_extract_concept_names",
    "async_prepare_concepts",
    "grade_answer",
    "async_grade_answer",
    "embed_language",
    "prepare_translation",
    "async_prepare_translation",
    "translate_into",
    "translate_missing",
    "refresh_machine_translations",
    "embed_query",
    "async_embed_query",
    "generate_rag_answer",
    "async_generate_rag_answer",
    "async_stream_rag_answer",
}

# Sync admin-only paths that keep their transaction across an LLM call on
# purpose, each with the issue that retires it. This list may only shrink.
# Empty since [94]: every path that held a transaction across an LLM
# call has been split into prepare/apply. Keep it empty.
KNOWN_TRANSACTION_LLM_CALLERS: set[tuple[str, str]] = set()


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
                and call_name(item.context_expr) in {"transaction", "async_transaction"}
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
            if (relative, function) in KNOWN_TRANSACTION_LLM_CALLERS:
                continue
            offenders[f"{relative}:{function}"] = calls
    assert offenders == {}


def test_the_known_transaction_llm_callers_still_exist():
    """The allowlist must shrink when a path is fixed, not linger."""
    stale = set()
    for relative, function in KNOWN_TRANSACTION_LLM_CALLERS:
        tree = ast.parse((PACKAGE / relative).read_text())
        found = _llm_calls_inside_transactions(tree)
        if function not in found:
            stale.add((relative, function))
    assert stale == set()


def test_the_llm_transaction_check_catches_a_violation():
    sample = ast.parse(
        "def f(db):\n"
        "    with transaction(db, 'x'):\n"
        "        deepseek_service.generate_answer(a, b)\n"
        "async def g(db):\n"
        "    async with async_transaction(db, 'x'):\n"
        "        await embedding_service.async_create_embeddings(t)\n"
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
