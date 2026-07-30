"""声タイプ3軸バーの位置と軸ラベルの契約テスト（docs/83 §2・§4）。

DB・音声ファイル不要（classify_voice_type は解析結果 dict を受けるだけ）。
バーは 0=左ラベルの極 / 0.5=どちらとも言えない / 1=右ラベルの極 で描くため、
その写像とラベル文言が崩れていないことを固定する。

実行:
    cd backend && ./.venv/bin/python -m unittest tests.test_voice_type_axes -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.coaching.voice_coach import _AXIS_JP, classify_voice_type  # noqa: E402


def _analysis(h1h2: float, cpp: float, hnr: float, tilt: float, sf: float, register: str) -> dict:
    return {
        "h1h2_db": h1h2,
        "cpp_db": cpp,
        "hnr_db": hnr,
        "spectral_tilt_db_oct": tilt,
        "singers_formant_ratio": sf,
        "voice": {"register_high": {"register": register}},
    }


# 地声・パワフル・明るめ側に強く振れる入力
STRONG_LEFT = _analysis(h1h2=0.0, cpp=14.0, hnr=22.0, tilt=-6.0, sf=0.012, register="chest")
# 裏声・ソフト・暗め側に強く振れる入力
STRONG_RIGHT = _analysis(h1h2=10.0, cpp=4.0, hnr=8.0, tilt=-14.0, sf=0.001, register="head")
# 各指標をしきい値ぴったりに置いた境界入力
BOUNDARY = _analysis(h1h2=4.0, cpp=8.0, hnr=14.0, tilt=-9.0, sf=0.004, register="")


class TestAxisLabels(unittest.TestCase):
    def test_labels_are_the_specified_words(self):
        """docs/83 §2 のラベル。旧「エアリー（息まじり）」等に戻っていないこと。"""
        self.assertEqual(
            _AXIS_JP,
            {
                "chest": "地声寄り",
                "head": "裏声寄り",
                "power": "パワフル",
                "airy": "ソフト",
                "clear": "明るめ",
                "deep": "暗め",
            },
        )


class TestAxesPos(unittest.TestCase):
    def test_strong_left_is_at_left_pole(self):
        r = classify_voice_type(STRONG_LEFT)
        self.assertEqual(r["id"], "rock")
        self.assertEqual(r["axes_pos"], {"register": 0.0, "power": 0.0, "color": 0.0})

    def test_strong_right_is_at_right_pole(self):
        r = classify_voice_type(STRONG_RIGHT)
        self.assertEqual(r["id"], "moody")
        self.assertEqual(r["axes_pos"], {"register": 1.0, "power": 1.0, "color": 1.0})

    def test_boundary_sits_at_center_and_flags_near(self):
        """境界＝中央。near も立ち、コピー側で「やや」と表現できること。"""
        r = classify_voice_type(BOUNDARY)
        self.assertEqual(r["axes_pos"], {"register": 0.5, "power": 0.5, "color": 0.5})
        self.assertEqual(r["near"], {"register": True, "power": True, "color": True})

    def test_pos_is_clamped_within_unit_range(self):
        """外れ値でも 0〜1 を外さない（バーが枠外に出ない）。"""
        extreme = _analysis(h1h2=-50.0, cpp=99.0, hnr=99.0, tilt=99.0, sf=1.0, register="chest")
        for v in classify_voice_type(extreme)["axes_pos"].values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_pos_matches_binary_axis(self):
        """axes（二値）と axes_pos（位置）が食い違わないこと。左極なら 0.5 未満。"""
        for analysis in (STRONG_LEFT, STRONG_RIGHT):
            r = classify_voice_type(analysis)
            left_side = {"chest", "power", "clear"}
            for key, label in r["axes"].items():
                pos = r["axes_pos"][key]
                if label in left_side:
                    self.assertLess(pos, 0.5, f"{key}={label} なのに pos={pos}")
                else:
                    self.assertGreater(pos, 0.5, f"{key}={label} なのに pos={pos}")

    def test_no_axes_when_analysis_is_insufficient(self):
        """解析不足なら None（フロントはバーを描かない）。"""
        self.assertIsNone(classify_voice_type({}))


if __name__ == "__main__":
    unittest.main()
