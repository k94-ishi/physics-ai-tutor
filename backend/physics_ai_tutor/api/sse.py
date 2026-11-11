"""Server-sent events framing ([71]).

Transport detail, so it lives with the routers: services yield events,
this turns them into the wire format.
"""

import json


def event(name: str, payload: dict) -> str:
    """One SSE frame. JSON keeps newlines in answers from splitting it."""
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
