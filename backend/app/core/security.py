"""
Password hashing and session tokens — standard library only.

Passwords are never stored. We keep a salted scrypt hash: a one-way,
deliberately slow fingerprint. Login hashes what was typed and compares.

Sessions are signed tokens (HMAC-SHA256) kept in an HttpOnly cookie.
They can't be forged without SESSION_SECRET, and they expire.
Changing SESSION_SECRET logs out every session at once.
"""

import base64
import hashlib
import hmac
import secrets
import time

SESSION_COOKIE = "awm_session"

# scrypt cost: ~16 MB of memory per attempt. Instant for one login,
# expensive for anyone trying millions of guesses.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """Return 'scrypt:N:r:p:salt:hash' — safe to store, impossible to reverse."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt:{SCRYPT_N}:{SCRYPT_R}:{SCRYPT_P}:{_b64(salt)}:{_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """True if `password` matches the stored hash. Constant-time comparison."""
    try:
        scheme, n, r, p, salt, expected = stored.split(":")
        if scheme != "scrypt":
            return False
        expected_bytes = _unb64(expected)
        digest = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected_bytes)
        )
        return hmac.compare_digest(digest, expected_bytes)
    except Exception:
        return False


def _sign(secret: str, payload: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def make_session_token(secret: str, days: int) -> str:
    """A signed token: version, expiry, random nonce, signature."""
    expires = int(time.time()) + days * 86400
    payload = f"v1.{expires}.{secrets.token_urlsafe(12)}"
    return f"{payload}.{_sign(secret, payload)}"


def is_valid_session(token: str | None, secret: str) -> bool:
    """True if the token is ours, untampered, and not expired."""
    if not token or not secret:
        return False
    try:
        version, expires, nonce, signature = token.split(".")
    except ValueError:
        return False
    payload = f"{version}.{expires}.{nonce}"
    if version != "v1" or not hmac.compare_digest(signature, _sign(secret, payload)):
        return False
    return int(expires) > time.time()