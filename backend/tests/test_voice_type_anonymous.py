"""声タイプ診断の匿名アクセス契約テスト（docs/35 課題1 / docs/47 TC-01）。

DB不要（get_db をダミーに差し替え）。匿名（Cookie無し）で analyze を叩いても
401 を返さない＝「未登録でも1回お試し」が許可されていることを検証する。
非対応拡張子で送ることで、重い音声解析（ffmpeg/librosa）に到達する前の
400 BAD_REQUEST で確定させ、テストを hermetic に保つ。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_voice_type_anonymous -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402


def _dummy_db():
    # 400(拡張子不正)パスでは DB を触らないので None で十分。
    yield None


class VoiceTypeAnonymousTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.dependency_overrides[get_db] = _dummy_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_anonymous_analyze_is_not_401(self):
        """Cookie無し（未ログイン）でも 401 を返さない（匿名お試しが許可されている）。"""
        resp = self.client.post(
            "/api/v1/voice-type/analyze",
            files={"audio_file": ("note.txt", b"not audio", "text/plain")},
        )
        self.assertNotEqual(
            resp.status_code, 401,
            f"匿名解析が401で弾かれている（課題1の回帰）: {resp.status_code} {resp.text}",
        )
        # 認証は通過し、入力バリデーション（非対応拡張子）で 400 になるのが期待。
        # 例外は共通ハンドラで {code, message, ...} に整形されてトップレベルに出る。
        self.assertEqual(resp.status_code, 400, resp.text)
        self.assertEqual(resp.json().get("code"), "BAD_REQUEST", resp.text)


if __name__ == "__main__":
    unittest.main()
