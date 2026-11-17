"""Read and write seed_embeddings.jsonl.gz, the seed's stored vectors.

Kept apart from seed.jsonl (owner, 2026-11-10): seed.jsonl is the
reviewable content; this file only spares the OpenAI calls when a local
database is rebuilt. Standard library only: gzip-compressed JSON lines,
a header line, then one `{"key", "vector"}` line per embedding, with the
vector as base64 little-endian float32 (pgvector's own precision, so
values round-trip exactly). Keys are `embedding_service.vector_key`.
"""

import base64
import gzip
import json
import sys
from array import array
from pathlib import Path

FORMAT = "float32-le-base64"
EMBEDDINGS_FILE = Path(__file__).resolve().parent / "seed_embeddings.jsonl.gz"


def _encode(vector: list[float]) -> str:
    packed = array("f", vector)
    if sys.byteorder != "little":
        packed.byteswap()
    return base64.b64encode(packed.tobytes()).decode("ascii")


def _decode(text: str) -> list[float]:
    packed = array("f")
    packed.frombytes(base64.b64decode(text))
    if sys.byteorder != "little":
        packed.byteswap()
    return packed.tolist()


def write(path: Path, model: str, vectors: dict[str, list[float]]) -> None:
    """Write vectors sorted by key, so the file changes only with its data."""
    dimensions = len(next(iter(vectors.values()))) if vectors else 0
    # mtime=0 keeps the gzip bytes identical for identical content.
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        header = {"model": model, "dimensions": dimensions, "format": FORMAT}
        f.write((json.dumps(header) + "\n").encode())
        for key in sorted(vectors):
            line = {"key": key, "vector": _encode(vectors[key])}
            f.write((json.dumps(line) + "\n").encode())


def read(path: Path, model: str) -> dict[str, list[float]]:
    """Vectors for `model`; empty when the file is absent or for another model."""
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        header = json.loads(f.readline())
        if header.get("model") != model or header.get("format") != FORMAT:
            return {}
        return {line["key"]: _decode(line["vector"]) for line in map(json.loads, f)}
