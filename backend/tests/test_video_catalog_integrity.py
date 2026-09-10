"""動画カタログの整合性ガード（docs/106 §1A）。

同一URLを別の練習に使い回すと、練習Aの提案に練習Bの動画が付く取り違えが起きる
（実例: ストロー発声の提案にリップロール動画・docs/93 §0 と合わせて2度目）。
個別の貼り替えではなく「重複登録は許可リスト以外禁止」を機械的に強制する。
"""
from collections import defaultdict

from app.coaching.taxonomy import SHARED_VIDEO_ALLOWLIST, TASKS


def _video_registrations() -> dict[str, set[str]]:
    """カタログ全体の URL → その URL を登録している練習名の集合。"""
    reg: dict[str, set[str]] = defaultdict(set)
    for task in TASKS:
        for prac in task.get("practices") or []:
            url = (prac.get("video") or {}).get("url")
            if url:
                reg[url].add(prac["name"])
    return reg


def test_no_duplicate_video_url_outside_allowlist():
    """同一URLの重複登録は、明示的な許可リストにある組み合わせだけ通す。"""
    violations = []
    for url, names in _video_registrations().items():
        if len(names) <= 1:
            continue
        allowed = SHARED_VIDEO_ALLOWLIST.get(url)
        if allowed is None:
            violations.append(f"{url} が複数の練習に登録されている: {sorted(names)}")
        elif names != set(allowed):
            violations.append(
                f"{url} の共有練習が許可リストと不一致: 実際={sorted(names)} 許可={sorted(allowed)}"
            )
    assert not violations, (
        "動画URLの重複登録を検出。動画の内容がその練習そのものの実演でないなら"
        "使い回さず video を外す（found=False で search_practice_video に委ねる）。"
        "内容が本当に共有可能なら SHARED_VIDEO_ALLOWLIST に明示追加する:\n"
        + "\n".join(violations)
    )


def test_allowlist_entries_are_live():
    """許可リストの練習名が実在しなくなったら落とす（改名・削除への追随忘れ検知）。"""
    reg = _video_registrations()
    stale = []
    for url, allowed in SHARED_VIDEO_ALLOWLIST.items():
        actual = reg.get(url, set())
        missing = set(allowed) - actual
        if missing:
            stale.append(f"{url}: カタログに存在しない練習名 {sorted(missing)}")
    assert not stale, "SHARED_VIDEO_ALLOWLIST が古い:\n" + "\n".join(stale)


def test_mistaken_reuse_urls_are_not_reattached():
    """docs/106 §1A で撤去した取り違えの再登録を名指しで禁止する回帰テスト。

    リップロール動画（TakKKIdIGgQ）はリップロール系の練習だけ、
    あくび声トレ動画（tE_JxKjWka4）はあくび系の練習だけに付いてよい。
    """
    reg = _video_registrations()
    lip = reg.get("https://www.youtube.com/watch?v=TakKKIdIGgQ", set())
    assert all("リップロール" in n for n in lip), f"リップロール動画が別練習に登録: {sorted(lip)}"
    yawn = reg.get("https://www.youtube.com/watch?v=tE_JxKjWka4", set())
    assert all("あくび" in n for n in yawn), f"あくび動画が別練習に登録: {sorted(yawn)}"
