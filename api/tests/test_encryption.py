"""PHI encryption/decryption tests."""

import pytest
from app.utils.encryption import encrypt_phi, decrypt_phi


def test_encrypt_decrypt_roundtrip():
    """Encrypting then decrypting should return the original text."""
    original = "John Doe"
    encrypted = encrypt_phi(original)
    decrypted = decrypt_phi(encrypted)
    assert decrypted == original
    assert encrypted != original


def test_encrypt_empty_string():
    """Encrypting empty string should return empty string."""
    assert encrypt_phi("") == ""
    assert decrypt_phi("") == ""


def test_different_inputs_different_ciphertexts():
    """Different inputs should produce different ciphertexts."""
    enc1 = encrypt_phi("Alice")
    enc2 = encrypt_phi("Bob")
    assert enc1 != enc2


def test_decrypt_invalid_ciphertext():
    """Decrypting invalid ciphertext should return error marker."""
    result = decrypt_phi("not-a-valid-ciphertext")
    assert result == "[DECRYPTION_ERROR]"
