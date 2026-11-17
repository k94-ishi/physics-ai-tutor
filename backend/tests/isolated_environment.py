"""Keep a test run away from the developer's environment ([113]).

`conftest.py` calls `prepare()` before it imports the app, because the
settings are read once, at import:

- Every setting that could reach a real service is forced to a harmless
  value, so `backend/.env` (loaded by the settings) cannot bring a real
  database or API key into a test run. Environment variables win over
  the file.
- Unless `TEST_DATABASE_URL` is set, a throwaway PostgreSQL + pgvector
  container is started for this run and removed when it ends. CI and
  `docker compose exec backend` set it to their own test database.

A run that dies without cleaning up (killed, crashed) leaves its
container behind; the next run removes it. testcontainers' own reaper
(Ryuk) is off: on Docker Desktop its connection never arrived, so it
exited without removing anything, which was checked by killing a run.
"""

import atexit
import logging
import os
import socket

# The image of docker-compose.yml's postgres-test service; a test pins it.
POSTGRES_IMAGE = "pgvector/pgvector:pg17"

# Which run owns a container: its process id and machine.
OWNER_PID_LABEL = "physics-ai-tutor.test-run.pid"
OWNER_HOST_LABEL = "physics-ai-tutor.test-run.host"

# Forced: a test that escaped its mock must fail, not reach a real service.
FORCED_SETTINGS = {
    "OPENAI_API_KEY": "test-openai-key",
    "DEEPSEEK_API_KEY": "test-deepseek-key",
    # Nothing listens on port 9, so an unmocked call fails at once.
    "OPENAI_BASE_URL": "http://127.0.0.1:9",
    "DEEPSEEK_BASE_URL": "http://127.0.0.1:9",
}

# Defaults only: harmless whichever value wins.
DEFAULT_SETTINGS = {
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-the-isolated-test-run",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "SAME_SITE": "lax",
}

_container = None


def prepare() -> str:
    """Isolate the settings and return the test database URL."""
    url = os.environ.get("TEST_DATABASE_URL") or _start_database()

    os.environ.update(FORCED_SETTINGS)
    # The app's own engine points at the test database too, never elsewhere.
    os.environ["DATABASE_URL"] = url
    for name, value in DEFAULT_SETTINGS.items():
        os.environ.setdefault(name, value)

    return url


def _start_database() -> str:
    """A fresh database server for this run only."""
    global _container
    from testcontainers.community.postgres import PostgresContainer

    # An early-exit cleanup can run after pytest has closed its log
    # streams, where the Docker client's debug lines would fail.
    for name in ("docker", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    _remove_orphans()

    _container = PostgresContainer(
        POSTGRES_IMAGE,
        username="physics",
        password="physics",
        dbname="physics_ai_tutor_test",
        driver="psycopg",
    ).with_kwargs(
        labels={
            OWNER_PID_LABEL: str(os.getpid()),
            OWNER_HOST_LABEL: socket.gethostname(),
        }
    )
    _container.start()
    # conftest stops it at session end; this covers an early exit.
    atexit.register(stop)

    url = _container.get_connection_url()
    os.environ["TEST_DATABASE_URL"] = url
    return url


def _remove_orphans() -> None:
    """Remove containers left by earlier runs on this machine that died.

    Only a container whose owning process no longer exists is removed, so
    a run in another checkout or session is never touched.
    """
    from testcontainers.core.docker_client import DockerClient

    containers = DockerClient().client.containers
    host = socket.gethostname()
    leftovers = containers.list(all=True, filters={"label": OWNER_PID_LABEL})
    for container in leftovers:
        labels = container.labels
        if labels.get(OWNER_HOST_LABEL) != host:
            continue
        if not _process_alive(int(labels.get(OWNER_PID_LABEL, "0"))):
            container.remove(force=True)


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Someone else's live process: not ours to judge, keep it.
        return True
    return True


def stop() -> None:
    """Remove the container, if this run started one."""
    global _container
    if _container is not None:
        _container.stop()
        _container = None
