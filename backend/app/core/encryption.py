from __future__ import annotations

import base64
import hashlib
import os
import stat
import sys

from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


_MASTER_KEY: str | None = None
_SALT: bytes | None = None


def _set_restrictive_permissions(path: Path) -> None:
    if sys.platform == "win32":
        try:
            import win32security
            import ntsecuritycon as con
            import win32api

            sd = win32security.GetFileSecurity(
                str(path), win32security.DACL_SECURITY_INFORMATION
            )
            dacl = win32security.ACL()
            user_sid = win32security.GetTokenInformation(
                win32security.OpenProcessToken(
                    win32api.GetCurrentProcess(), win32security.TOKEN_QUERY
                ),
                win32security.TokenUser,
            )[0]
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE,
                user_sid,
            )
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                str(path), win32security.DACL_SECURITY_INFORMATION, sd
            )
        except ImportError:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _get_or_create_salt() -> bytes:
    global _SALT
    if _SALT is not None:
        return _SALT
    salt_path = _get_salt_path()
    if salt_path.exists():
        _SALT = salt_path.read_bytes()
    else:
        _SALT = os.urandom(16)
        salt_path.write_bytes(_SALT)
        _set_restrictive_permissions(salt_path)
    return _SALT


def _get_salt_path():
    from pathlib import Path

    config_dir = Path.home() / ".opsv-kits"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / ".enc_salt"


def _get_or_create_key() -> str:
    global _MASTER_KEY
    if _MASTER_KEY is not None:
        return _MASTER_KEY
    key_path = _get_key_path()
    if key_path.exists():
        _MASTER_KEY = key_path.read_text().strip()
    else:
        _MASTER_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()
        key_path.write_text(_MASTER_KEY)
        _set_restrictive_permissions(key_path)
    return _MASTER_KEY


def _get_key_path():
    from pathlib import Path

    config_dir = Path.home() / ".opsv-kits"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / ".enc_master_key"


def _derive_key_cryptography(master_key: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))


def _derive_key_fallback(master_key: str, salt: bytes) -> bytes:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        master_key.encode(),
        salt,
        600000,
        dklen=32,
    )
    return derived


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    master_key = _get_or_create_key()
    salt = _get_or_create_salt()

    if _HAS_CRYPTOGRAPHY:
        key = _derive_key_cryptography(master_key, salt)
        f = Fernet(key)
        token = f.encrypt(plaintext.encode())
        return token.decode()
    else:
        derived = _derive_key_fallback(master_key, salt)
        iv = os.urandom(16)
        encrypted = _xor_cipher(plaintext.encode(), derived, iv)
        result = iv + encrypted
        return base64.urlsafe_b64encode(result).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    master_key = _get_or_create_key()
    salt = _get_or_create_salt()

    if _HAS_CRYPTOGRAPHY:
        key = _derive_key_cryptography(master_key, salt)
        f = Fernet(key)
        return f.decrypt(ciphertext.encode()).decode()
    else:
        derived = _derive_key_fallback(master_key, salt)
        raw = base64.urlsafe_b64decode(ciphertext.encode())
        iv = raw[:16]
        cipher_data = raw[16:]
        return _xor_cipher(cipher_data, derived, iv).decode()


def _xor_cipher(data: bytes, key: bytes, iv: bytes) -> bytes:
    result = bytearray()
    for i, byte in enumerate(data):
        k = key[(i + iv[0]) % len(key)]
        result.append(byte ^ k)
    return bytes(result)
