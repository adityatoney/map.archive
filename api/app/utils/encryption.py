"""PHI encryption/decryption utilities using Fernet symmetric encryption."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _get_fernet() -> Fernet:
    """Get Fernet instance from settings encryption key."""
    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    # If the key isn't a valid Fernet key, generate one deterministically for dev
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, Exception):
        # In development with placeholder key, generate a consistent one
        import hashlib
        import base64
        derived = hashlib.sha256(key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        return Fernet(fernet_key)


def encrypt_phi(plaintext: str) -> str:
    """Encrypt a PHI string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_phi(ciphertext: str) -> str:
    """Decrypt a PHI ciphertext. Returns plaintext string."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return "[DECRYPTION_ERROR]"
