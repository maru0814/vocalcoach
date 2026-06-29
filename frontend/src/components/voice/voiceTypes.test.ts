import { describe, expect, it } from "vitest";
import { VOICE_TYPE_LIST, VOICE_TYPE_META, VTYPE_STYLE } from "./voiceTypes";

// バックエンドの VOICE_TYPES と一致させる 8 タイプ。3つの定義テーブル間で id が
// ズレるとUI崩れ/欠落になるため、整合性を固定する。
const EXPECTED_IDS = [
  "rock", "groovy", "pop", "mysterious", "crystal", "dramatic", "whisper", "moody",
];

describe("voiceTypes データ整合性", () => {
  it("8タイプが定義されている", () => {
    expect(VOICE_TYPE_LIST).toHaveLength(8);
    expect(new Set(VOICE_TYPE_LIST.map((t) => t.id))).toEqual(new Set(EXPECTED_IDS));
  });

  it("LIST / META / STYLE の id 集合が一致する", () => {
    const listIds = new Set(VOICE_TYPE_LIST.map((t) => t.id));
    expect(new Set(Object.keys(VOICE_TYPE_META))).toEqual(listIds);
    expect(new Set(Object.keys(VTYPE_STYLE))).toEqual(listIds);
  });

  it("META は name/emoji/desc を全タイプ持つ", () => {
    for (const id of EXPECTED_IDS) {
      const m = VOICE_TYPE_META[id];
      expect(m.name).toBeTruthy();
      expect(m.emoji).toBeTruthy();
      expect(m.desc).toBeTruthy();
    }
  });
});
