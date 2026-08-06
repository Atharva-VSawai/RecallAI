"""Small authenticated encryption wrapper for integration credentials."""
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings


def _key() -> bytes:
    return hashlib.sha256(settings.teams_token_encryption_key.encode("utf-8")).digest()


def encrypt(value: str) -> str:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt(value: str) -> str:
    raw = base64.urlsafe_b64decode(value.encode("ascii"))
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode("utf-8")
