"""Production password hashing is untouched by the cheap test hasher ([66])."""

from physics_ai_tutor.core import security
from tests.conftest import PRODUCTION_PASSWORD_HASH


def test_production_hashes_with_argon2id_recommended_cost():
    hashed = PRODUCTION_PASSWORD_HASH.hash("a-long-enough-password")

    # pwdlib's recommended Argon2id parameters (64 MiB, 3 passes, 4 lanes).
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")


def test_test_hasher_is_swapped_only_during_the_session():
    assert security.password_hash is not PRODUCTION_PASSWORD_HASH


def test_hashes_from_either_cost_verify_with_the_test_hasher():
    # Argon2 stores its parameters in the hash, so stored production hashes
    # still verify; only new hashes are cheap.
    production_hash = PRODUCTION_PASSWORD_HASH.hash("a-long-enough-password")

    assert security.verify_password("a-long-enough-password", production_hash)
