#!/usr/bin/env python3
"""VAPID鍵ペアを生成して .env 用の3行を出力する（PWAプッシュ通知。docs/73〜75）。

出力の VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT を docker/.env に貼る。
VAPID_PUBLIC_KEY は compose が frontend の NEXT_PUBLIC_VAPID_PUBLIC_KEY へ自動で渡す。

使い方:
    python3 scripts/ops/gen_vapid_keys.py [mailto:you@example.com]

秘密鍵を出力するので、実行結果はチャット/ログ/コミットに残さないこと（.env のみに置く）。
依存: cryptography（backend の python-jose[cryptography] 経由で導入済み）。
pywebpush はこの base64url raw 形式の秘密鍵をそのまま受理する（送信段まで到達を実測済み）。
"""
import base64
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "mailto:admin@example.com"

    priv = ec.generate_private_key(ec.SECP256R1())
    # 秘密鍵: 32byte スカラーの base64url（pywebpush が受理する raw 形式）
    private_key = _b64url(priv.private_numbers().private_value.to_bytes(32, "big"))
    # 公開鍵: 非圧縮点(65byte)の base64url（ブラウザ applicationServerKey 形式）
    public_key = _b64url(
        priv.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )

    print("# --- docker/.env に貼る（秘密鍵はここだけに置く） ---")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print(f"VAPID_SUBJECT={subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
