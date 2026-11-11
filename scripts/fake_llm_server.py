#!/usr/bin/env python3
"""A stand-in for OpenAI and DeepSeek that just sleeps ([68]).

Latency work needs a *known* generation time, not a real one: point the
backend's `DEEPSEEK_BASE_URL` and `OPENAI_BASE_URL` here and every
completion takes exactly `--chat-delay` seconds. That makes "slow calls
block fast requests" measurable and repeatable, and it spends no quota
and needs no API key.

Serves the two routes the app uses, OpenAI-compatible:
`POST /chat/completions` and `POST /embeddings`.

    python scripts/fake_llm_server.py --port 9100 --chat-delay 20

It is a measurement aid, never part of the app. Binds loopback only.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EMBEDDING_DIMENSIONS = 1536
ANSWER = "これはダミーの回答です。" * 20


class Handler(BaseHTTPRequestHandler):
    chat_delay = 20.0
    embedding_delay = 0.3

    def log_message(self, *args: object) -> None:
        """Keep the probe's output readable."""

    def _send(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (http.server's required name)
        length = int(self.headers.get("Content-Length", 0))
        request = json.loads(self.rfile.read(length) or b"{}")

        if self.path.endswith("/embeddings"):
            time.sleep(self.embedding_delay)
            texts = request.get("input") or [""]
            if isinstance(texts, str):
                texts = [texts]
            # A fixed seed per text keeps repeated runs comparable.
            vectors = []
            for text in texts:
                rng = random.Random(hash(text) & 0xFFFF)
                vectors.append(
                    [rng.uniform(-1, 1) for _ in range(EMBEDDING_DIMENSIONS)]
                )
            self._send(
                {
                    "object": "list",
                    "model": request.get("model", "fake-embedding"),
                    "data": [
                        {"object": "embedding", "index": i, "embedding": vector}
                        for i, vector in enumerate(vectors)
                    ],
                }
            )
            return

        time.sleep(self.chat_delay)
        self._send(
            {
                "id": "fake",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.get("model", "fake-chat"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": ANSWER},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                    "total_tokens": 300,
                },
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--chat-delay", type=float, default=20.0)
    parser.add_argument("--embedding-delay", type=float, default=0.3)
    args = parser.parse_args()

    Handler.chat_delay = args.chat_delay
    Handler.embedding_delay = args.embedding_delay

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(
        f"Fake LLM on http://127.0.0.1:{args.port} "
        f"(chat {args.chat_delay}s, embeddings {args.embedding_delay}s)"
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
