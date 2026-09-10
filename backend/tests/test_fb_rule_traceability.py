"""FB品質ルール（docs/42）の来歴トレーサビリティ強制（docs/107）。

「docs/42 にルールを書いたが、プロンプトにもテストにも検査にも落とさなかった」
という“書いただけ”事故（生の数値ルール・動画取り違えで実際に2度発生）を機械的に落とす。

- 順方向: docs/42 の全ルールIDが、実装側のどこか（プロンプト/コードのコメント・
  テスト docstring・checkers の RULES）で宣言されていること
- 逆方向: 実装側で宣言された ID が docs/42 に実在すること（typo・削除済みルールの残骸検出）

宣言は「どこに実装したかを一度は考えて書いた」ことしか保証しない。意味的な正しさは
soar_eval・レビュー・ブラインド判定の仕事（docs/107 §2）。
"""
import re
from pathlib import Path

# backend/ を起点にリポジトリルートを解決（run.sh と同じ cwd 前提を置かない）
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent

DOCS_42 = _ROOT / "docs" / "42_FB品質基準_単一ソース.md"

# ID宣言を探しに行く実装側ファイル（docs/107 §1.2）
IMPL_PATHS = [
    _BACKEND / "app" / "coaching",            # プロンプト・ガード・注入のコメント
    _BACKEND / "tests",                        # テスト docstring
    _ROOT / "scripts" / "soar_eval" / "checkers.py",  # RULES の宣言
    _ROOT / ".claude" / "skills" / "vocal-trainer" / "SKILL.md",  # skill版
]

_ID_RE = re.compile(r"FB-042-[0-9]{2}(?:\.[0-9]+)?-[0-9]+")


def _ids_in(path: Path) -> set[str]:
    if path.is_dir():
        out: set[str] = set()
        for p in sorted(path.rglob("*")):
            if p.suffix in (".py", ".md") and p.is_file():
                out |= set(_ID_RE.findall(p.read_text(encoding="utf-8")))
        return out
    return set(_ID_RE.findall(path.read_text(encoding="utf-8")))


def _docs_ids() -> set[str]:
    return _ids_in(DOCS_42)


def _impl_ids() -> set[str]:
    out: set[str] = set()
    for p in IMPL_PATHS:
        ids = _ids_in(p)
        if p.name == "tests":
            # 自分自身（このテスト）の本文は宣言に数えない
            ids -= set(_ID_RE.findall(Path(__file__).read_text(encoding="utf-8")))
        out |= ids
    return out


def test_docs42_has_rule_ids():
    """docs/42 に ID が振られていること（全消し・正規表現の空振りをまず検出）。"""
    ids = _docs_ids()
    assert len(ids) >= 40, f"docs/42 のルールIDが少なすぎる（{len(ids)}件）。ID体系が壊れていないか確認"


def test_every_docs42_rule_is_declared_in_implementation():
    """順方向: docs/42 の全ルールに実装側の宣言があること（docs/107 §1.3-1）。

    落ちたら: そのルールをどこに実装したか（プロンプト/ガード/テスト/チェッカ）を確認し、
    実装箇所のコメント・docstring・RULES に同じ ID を書く。実装が本当に無いなら
    それが「書いただけ」事故そのもの＝実装してから ID を宣言する。
    """
    missing = sorted(_docs_ids() - _impl_ids())
    assert not missing, (
        "docs/42 にあるが実装側のどこにも宣言が無いルールID（書いただけ事故の候補）:\n"
        + "\n".join(missing)
    )


def test_no_stale_ids_in_implementation():
    """逆方向: 実装側の宣言 ID が docs/42 に実在すること（docs/107 §1.3-2）。

    落ちたら: typo か、docs/42 からルールを消したのに実装側の宣言が残っている
    （SSOT逸脱）。docs/42 と実装側の宣言を揃える。
    """
    stale = sorted(_impl_ids() - _docs_ids())
    assert not stale, (
        "実装側で宣言されているが docs/42 に存在しないルールID（typo/削除済みの残骸）:\n"
        + "\n".join(stale)
    )
