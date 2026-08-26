"""QA harness: 投稿内容のローテ（同内容の短周期再登場を防ぐ）。
rotation_index（型の通算出番）と弾倉の一巡を検証する。ネットワークは呼ばない。"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

os.environ["SNS_IMAGE"] = "0"
os.environ.pop("GEMINI_API_KEY", None)

import themes
import infographic

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


BASE = datetime.date(2026, 8, 17)  # 月曜
SLOTS_CHRONO = (3, 1, 2)  # 朝→昼→夜


def occurrences(pillar, weeks=6):
    """weeks週ぶんのスケジュールから、その型の出番を時系列で列挙する。"""
    out = []
    for d in range(weeks * 7):
        day = BASE + datetime.timedelta(days=d)
        for slot in SLOTS_CHRONO:
            if themes.pillar_for(day.weekday(), slot) == pillar:
                out.append((day, slot))
    return out


ALL_PILLARS = ("tip", "contrarian", "voice_type", "self_type", "visual",
               "artist_analysis")

# ---- TC-RT01: rotation_index は出番ごとに +1 で進む（連番＝弾倉を順に一巡） ----
for pillar in ALL_PILLARS:
    occ = occurrences(pillar)
    idxs = [themes.rotation_index(pillar, day, slot) for day, slot in occ]
    seq = all(b - a == 1 for a, b in zip(idxs, idxs[1:]))
    check(f"TC-RT01 連番: {pillar}", seq and len(idxs) > 0,
          f"=> 先頭5個 {idxs[:5]}")

# ---- TC-RT02: 弾数ぶんの連続する出番で、本文が全て異なる（一巡まで重複なし） ----
POOL = {"tip": len(themes.TIPS), "contrarian": len(themes.CONTRARIAN),
        "voice_type": len(themes.VOICE_TYPES),
        "artist_analysis": len(themes.ARTIST_ANALYSIS),
        "self_type": 5, "visual": 3}
for pillar in ALL_PILLARS:
    occ = occurrences(pillar)
    n = POOL[pillar]
    texts = []
    for day, slot in occ[:n]:
        i = themes.rotation_index(pillar, day, slot)
        p = themes.template_post(pillar, i, "https://x.test")
        texts.append(p["text"] + "\n----\n" + (p.get("reply") or ""))
    check(f"TC-RT02 一巡まで重複なし: {pillar}（弾数{n}）",
          len(set(texts)) == len(texts),
          f"=> {len(set(texts))}/{len(texts)}種")

# ---- TC-RT03: 旧バグ再現条件 — 同週の contrarian（月夜/木昼/水朝/土朝）が全て別内容 ----
week1 = [(day, slot) for day, slot in occurrences("contrarian") if (day - BASE).days < 7]
texts = []
for day, slot in week1:
    i = themes.rotation_index("contrarian", day, slot)
    texts.append(themes.template_post("contrarian", i, "https://x.test")["text"])
check("TC-RT03 同週contrarian全て別内容", len(set(texts)) == len(texts) == 4,
      f"=> {len(set(texts))}/{len(texts)}種")

# ---- TC-RT04: 弾数はローテの週次出番より多い（1週間以内に同内容が再登場しない） ----
for pillar in ALL_PILLARS:
    per_week = len([1 for day, slot in occurrences(pillar) if (day - BASE).days < 7])
    check(f"TC-RT04 弾数>週次出番: {pillar}", POOL[pillar] > per_week,
          f"=> 弾数{POOL[pillar]} / 週{per_week}回")

# ---- TC-RT05: 診断導線フックにも変奏があり、いずれも実名・リプ案内・URLなしを守る ----
for pillar, n in (("self_type", 5), ("visual", 3)):
    canon = {name for a in themes.ARTISTS_BY_ID.values()
             for names in a.values() for name in names}
    for i in range(n):
        t = themes.template_post(pillar, i, "https://x.test")["text"]
        has_name = any(name in t for name in canon)
        check(f"TC-RT05 {pillar}[{i}] 実名あり", has_name)
        check(f"TC-RT05 {pillar}[{i}] リプ案内あり", "リプに" in t)
        check(f"TC-RT05 {pillar}[{i}] URLなし", "http" not in t)

# ---- TC-RT06: 追加した弾（tip/contrarian）が図解データとして成立する ----
for i in range(len(themes.TIPS)):
    d = infographic.build_data("tip", i)
    check(f"TC-RT06 tip[{i}] 図解OK",
          d.get("type") == "tip" and len(d.get("steps", [])) >= 2 and d.get("title"),
          f"=> steps={len(d.get('steps', []))}")
for i in range(len(themes.CONTRARIAN)):
    d = infographic.build_data("contrarian", i)
    check(f"TC-RT06 contrarian[{i}] 図解OK",
          d.get("type") == "contrarian" and len(d.get("reasons", [])) == 2
          and d.get("title") and d.get("verdict"),
          f"=> verdict={d.get('verdict')!r}")

# ---- TC-RT07: スケジュール外（手動 --pillar / 不正slot）は例外を出さず日替わりで返す ----
i1 = themes.rotation_index("artist_analysis", BASE, 1)  # 月昼にartist_analysisは無い
i2 = themes.rotation_index("tip", BASE, 9)              # 不正slot
check("TC-RT07 スケジュール外でも動く", isinstance(i1, int) and i2 == BASE.toordinal())

failed = [tc for tc, ok, _ in results if not ok]
print("\n" + "─" * 40)
print(f"{len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
