import base64
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_encryption_globals():
    import app.core.encryption as enc_mod

    orig_key = enc_mod._MASTER_KEY
    orig_salt = enc_mod._SALT
    enc_mod._MASTER_KEY = None
    enc_mod._SALT = None
    yield
    enc_mod._MASTER_KEY = orig_key
    enc_mod._SALT = orig_salt


class TestEncryptDecrypt:
    def test_encrypt_decrypt_roundtrip(self):
        from app.core.encryption import decrypt, encrypt

        plaintext = "hello world"
        cipher = encrypt(plaintext)
        assert cipher != plaintext
        result = decrypt(cipher)
        assert result == plaintext

    def test_encrypt_empty_string(self):
        from app.core.encryption import encrypt

        assert encrypt("") == ""

    def test_decrypt_empty_string(self):
        from app.core.encryption import decrypt

        assert decrypt("") == ""

    def test_encrypt_unicode(self):
        from app.core.encryption import decrypt, encrypt

        plaintext = "你好世界 🌍"
        cipher = encrypt(plaintext)
        assert decrypt(cipher) == plaintext

    def test_encrypt_long_text(self):
        from app.core.encryption import decrypt, encrypt

        plaintext = "a" * 10000
        cipher = encrypt(plaintext)
        assert decrypt(cipher) == plaintext

    def test_encrypt_special_chars(self):
        from app.core.encryption import decrypt, encrypt

        plaintext = "password!@#$%^&*()_+-={}[]|\\:\";<>?,./"
        cipher = encrypt(plaintext)
        assert decrypt(cipher) == plaintext

    def test_different_plaintexts_different_ciphertexts(self):
        from app.core.encryption import encrypt

        c1 = encrypt("text1")
        c2 = encrypt("text2")
        assert c1 != c2


class TestGetOrCreateKey:
    def test_creates_new_key(self, tmp_path):
        from app.core.encryption import _get_or_create_key

        with patch("app.core.encryption._get_key_path", return_value=tmp_path / "key"):
            key = _get_or_create_key()
            assert key is not None
            assert len(key) > 0

    def test_reuses_existing_key(self, tmp_path):
        from app.core.encryption import _get_or_create_key

        key_path = tmp_path / "key"
        with patch("app.core.encryption._get_key_path", return_value=key_path):
            key1 = _get_or_create_key()
            key2 = _get_or_create_key()
            assert key1 == key2

    def test_caches_key_in_memory(self, tmp_path):
        from app.core.encryption import _get_or_create_key
        import app.core.encryption as enc_mod

        with patch("app.core.encryption._get_key_path", return_value=tmp_path / "key"):
            key1 = _get_or_create_key()
            enc_mod._MASTER_KEY = None
            key2 = _get_or_create_key()
            assert key1 == key2


class TestGetOrCreateSalt:
    def test_creates_new_salt(self, tmp_path):
        from app.core.encryption import _get_or_create_salt

        with patch("app.core.encryption._get_salt_path", return_value=tmp_path / "salt"):
            salt = _get_or_create_salt()
            assert isinstance(salt, bytes)
            assert len(salt) == 16

    def test_reuses_existing_salt(self, tmp_path):
        from app.core.encryption import _get_or_create_salt

        salt_path = tmp_path / "salt"
        with patch("app.core.encryption._get_salt_path", return_value=salt_path):
            salt1 = _get_or_create_salt()
            salt2 = _get_or_create_salt()
            assert salt1 == salt2


class TestDeriveKey:
    def test_derive_key_cryptography(self):
        from app.core.encryption import _derive_key_cryptography

        key = _derive_key_cryptography("test_master_key", b"\x00" * 16)
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_derive_key_fallback(self):
        from app.core.encryption import _derive_key_fallback

        key = _derive_key_fallback("test_master_key", b"\x00" * 16)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_derive_keys_deterministic(self):
        from app.core.encryption import _derive_key_cryptography, _derive_key_fallback

        k1 = _derive_key_cryptography("key", b"salt")
        k2 = _derive_key_cryptography("key", b"salt")
        assert k1 == k2

        f1 = _derive_key_fallback("key", b"salt")
        f2 = _derive_key_fallback("key", b"salt")
        assert f1 == f2


class TestXorCipher:
    def test_xor_cipher_roundtrip(self):
        from app.core.encryption import _xor_cipher

        data = b"hello world"
        key = b"\xab" * 32
        iv = b"\x00" * 16
        encrypted = _xor_cipher(data, key, iv)
        decrypted = _xor_cipher(encrypted, key, iv)
        assert decrypted == data

    def test_xor_cipher_empty(self):
        from app.core.encryption import _xor_cipher

        result = _xor_cipher(b"", b"\x00" * 32, b"\x00" * 16)
        assert result == b""


class TestFallbackPath:
    def test_encrypt_decrypt_without_cryptography(self):
        import app.core.encryption as enc_mod

        orig = enc_mod._HAS_CRYPTOGRAPHY
        enc_mod._HAS_CRYPTOGRAPHY = False
        enc_mod._MASTER_KEY = None
        enc_mod._SALT = None
        try:
            plaintext = "fallback test"
            cipher = enc_mod.encrypt(plaintext)
            result = enc_mod.decrypt(cipher)
            assert result == plaintext
        finally:
            enc_mod._HAS_CRYPTOGRAPHY = orig


class TestSetRestrictivePermissions:
    def test_set_permissions_non_windows(self):
        from app.core.encryption import _set_restrictive_permissions

        with patch("app.core.encryption.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch("app.core.encryption.os.chmod") as mock_chmod:
                from pathlib import Path

                _set_restrictive_permissions(Path("/tmp/test"))
                mock_chmod.assert_called()

    def test_set_permissions_windows_with_win32(self, tmp_path):
        from app.core.encryption import _set_restrictive_permissions

        test_file = tmp_path / "test_perm"
        test_file.write_text("test")

        with patch("app.core.encryption.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch.dict("sys.modules", {"win32security": MagicMock(), "ntsecuritycon": MagicMock(), "win32api": MagicMock()}):
                _set_restrictive_permissions(test_file)

    def test_set_permissions_windows_fallback(self, tmp_path):
        from app.core.encryption import _set_restrictive_permissions

        test_file = tmp_path / "test_perm2"
        test_file.write_text("test")

        with patch("app.core.encryption.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("app.core.encryption.os.chmod") as mock_chmod:
                import stat

                _set_restrictive_permissions(test_file)
                mock_chmod.assert_called()
