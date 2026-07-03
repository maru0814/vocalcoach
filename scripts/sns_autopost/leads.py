#!/usr/bin/env python3
"""リード探索のSSOT（docs/55 FR-01/FR-02、docs/56）。

「歌の悩みを今まさに言語化している人」を捕まえる検索クエリと、候補を絞り込む
選別基準をここに一元管理する（themes.py と同格の静的定義）。

バン安全性の原則（不変条件）: このモジュール群が扱うのは read（探す・絞る）だけ。
フォロー/返信/DM の write 自動実行はリード獲得のどのモジュールにも存在しない。
実行は常に運用者がXアプリで手動（docs/56 §2.3）。
"""
import os
import re

# --- 探索クエリの正本（FR-01）。query はX検索にそのまま渡す語。 -----------------
# keywords は「本文がこの悩み文脈か」を機械判定するための語（1つ以上ヒットで通過）。
# 改定は growth-operator が lead_metrics.py のクエリ別フォロバ率を見て行う。
LEAD_QUERIES = [
    {"id": "highnote",   "query": "高音 出ない",          "intent": "高音が出ない悩み",
     "keywords": ["高音", "出ない", "届かない", "きつい", "苦しい"]},
    {"id": "flip",       "query": "声 裏返る",            "intent": "換声点で裏返る悩み",
     "keywords": ["裏返る", "ひっくり返る", "換声点", "喚声点"]},
    {"id": "mix",        "query": "ミックスボイス できない", "intent": "ミックスボイス習得の悩み",
     "keywords": ["ミックスボイス", "ミックス", "地声", "裏声"]},
    {"id": "onchi",      "query": "音痴 直したい",         "intent": "音程への自信のなさ",
     "keywords": ["音痴", "直したい", "音程", "外れる", "ずれる"]},
    {"id": "pitch",      "query": "音程 不安定",           "intent": "ピッチが不安定な悩み",
     "keywords": ["音程", "ピッチ", "不安定", "ぶれる", "合わない"]},
    {"id": "karaoke",    "query": "精密採点 点数",         "intent": "カラオケ採点で伸び悩み",
     "keywords": ["精密採点", "採点", "点", "カラオケ"]},
    {"id": "falsetto",   "query": "裏声 出ない",           "intent": "裏声が出ない悩み",
     "keywords": ["裏声", "ファルセット", "出ない", "かすれる"]},
    {"id": "throat",     "query": "喉声 治したい",         "intent": "喉声・喉締めの悩み",
     "keywords": ["喉声", "喉締め", "喉が痛い", "苦しい"]},
    {"id": "longtone",   "query": "ロングトーン 続かない",  "intent": "息・ロングトーンの悩み",
     "keywords": ["ロングトーン", "息が続かない", "息継ぎ", "ブレス"]},
    {"id": "utattemita", "query": "歌ってみた 下手",        "intent": "歌ってみた勢の伸び悩み",
     "keywords": ["歌ってみた", "下手", "うまくなりたい", "上手くなりたい"]},
    # エンゲージ起点（自分の投稿へのリプ/引用）。検索語は使わない特別ソース。
    # すでに興味を示した最高熱度のリードなので intent 判定はスキップされる（select参照）。
    {"id": "mention",    "query": "",                      "intent": "自投稿へのエンゲージ",
     "keywords": []},
]

if not LEAD_QUERIES:  # 無音運用防止（FR-01 例外）
    raise RuntimeError("LEAD_QUERIES が空です。leads.py を確認してください。")

QUERY_BY_ID = {q["id"]: q for q in LEAD_QUERIES}

# X検索に付ける共通の絞り込み（RT除外・URL付き除外＝宣伝を減らす・日本語）
SEARCH_SUFFIX = " lang:ja -is:retweet -has:links"


def search_queries() -> list[dict]:
    """X検索に回すクエリ（mention 疑似ソースを除く）。"""
    return [q for q in LEAD_QUERIES if q["query"]]


# --- 選別基準（FR-02）------------------------------------------------------------

def _exclude_words() -> list[str]:
    raw = os.getenv("LEAD_EXCLUDE_KEYWORDS", "相互,フォロバ100,相互フォロー")
    return [w.strip() for w in raw.split(",") if w.strip()]


def followers_range() -> tuple[int, int]:
    return (int(os.getenv("LEAD_FOLLOWERS_MIN", "30")),
            int(os.getenv("LEAD_FOLLOWERS_MAX", "3000")))


_JA_RE = re.compile(r"[ぁ-んァ-ヶ一-龠]")


def is_japanese(text: str) -> bool:
    """かな・漢字が一定割合含まれるか（簡易判定）。"""
    if not text:
        return False
    ja = len(_JA_RE.findall(text))
    return ja >= 3 and ja / max(len(text), 1) >= 0.15


def intent_match(query_id: str, text: str) -> bool:
    """本文がクエリの悩み文脈に合うか（keywords 1つ以上ヒット）。"""
    q = QUERY_BY_ID.get(query_id)
    if not q or not q["keywords"]:
        return True  # mention など keywords を持たないソースは文脈判定なし
    return any(k in (text or "") for k in q["keywords"])


def select(cand: dict, engaged_handles: set[str]) -> tuple[bool, str]:
    """候補1件を選別する（docs/56 §3.2。すべてANDで通過）。

    cand: {text, handle, query_id, source, followers(optional int|None), bio(optional)}
    returns (ok, reason)。reason は除外理由 or 通過時の注記。
    """
    text = (cand.get("text") or "").strip()
    handle = (cand.get("handle") or "").lstrip("@").lower()
    bio = cand.get("bio") or ""
    qid = cand.get("query_id", "")

    if not text:
        return False, "本文なし（取得失敗）"
    if not is_japanese(text):
        return False, "日本語でない"
    # エンゲージ起点はすでに興味を示しているので intent 判定をスキップ
    if cand.get("source") != "mention" and not intent_match(qid, text):
        return False, f"文脈不一致（{qid}）"
    for w in _exclude_words():
        if w in text or w in bio or w in handle:
            return False, f"相互狙いワード（{w}）"
    if handle in engaged_handles:
        return False, "対応済み（重複）"
    lo, hi = followers_range()
    followers = cand.get("followers")
    if followers is None:
        return True, "followers:unknown(skipped)"  # 取得なし＝本条件スキップ（設計 §2.1）
    if not (lo <= int(followers) <= hi):
        return False, f"フォロワー数 {followers} が範囲外（{lo}〜{hi}）"
    return True, "ok"
