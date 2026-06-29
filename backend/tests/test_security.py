"""認証基盤（app/security/token.py, passwords.py）のユニットテスト。

JWTの往復・期限切れ拒否・改竄拒否と、bcryptのハッシュ/検証を検証する。
外部依存なし。
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.security.passwords import hash_password, verify_password
from app.security.token import create_access_token, decode_access_token


class TestToken:
    def test_round_trip(self):
        token = create_access_token(42)
        assert decode_access_token(token) == 42

    def test_sub_is_string_in_payload(self):
        token = create_access_token(7)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "7"
        assert "exp" in payload and "iat" in payload

    def test_expired_token_rejected(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "1",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(jwt.JWTError):
            decode_access_token(token)

    def test_wrong_secret_rejected(self):
        token = jwt.encode({"sub": "1"}, "not_the_real_secret", algorithm=settings.jwt_algorithm)
        with pytest.raises(jwt.JWTError):
            decode_access_token(token)

    def test_missing_sub_raises_value_error(self):
        token = jwt.encode(
            {"iat": int(datetime.now(timezone.utc).timestamp())},
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(ValueError):
            decode_access_token(token)


class TestPasswords:
    def test_hash_then_verify(self):
        h = hash_password("s3cret-password")
        assert h != "s3cret-password"        # 平文を保存しない
        assert verify_password("s3cret-password", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correct horse")
        assert verify_password("battery staple", h) is False

    def test_salt_makes_hashes_unique(self):
        assert hash_password("same") != hash_password("same")

    def test_invalid_hash_returns_false_not_raise(self):
        # 壊れたハッシュでも例外を投げず False。
        assert verify_password("anything", "not-a-bcrypt-hash") is False

    def test_over_72_bytes_truncated(self):
        # bcryptの72バイト上限。先頭72バイトが同じなら一致する（切り詰め仕様の明示）。
        base = "a" * 72
        h = hash_password(base)
        assert verify_password(base + "EXTRA_IGNORED_TAIL", h) is True
