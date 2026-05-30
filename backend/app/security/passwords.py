"""
Password hashing via bcrypt directly.

passlib 1.7.4 は bcrypt 5.x と非互換（backend検出時に ValueError）。
依存を減らすため bcrypt を直接利用する。bcrypt は72バイト上限なので切り詰める。
"""

import bcrypt

_MAX_BCRYPT_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_truncate(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
