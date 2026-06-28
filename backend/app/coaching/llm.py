"""
ソラ先生の自然言語チャット応答（Google Gemini）。

ハイブリッド構成:
  - 重い音声解析・採点・課題診断はルールベース（rule_engine / taxonomy）のまま。
  - ユーザーのテキスト質問への「返答だけ」を LLM に通し、ChatGPT のように自然に答える。
  - GEMINI_API_KEY 未設定 or API エラー時は None を返し、呼び出し側が
    ルールベース応答（rule_engine.answer_question）にフォールバックする。

コスト最適化:
  - 最安クラスの Gemini Flash-Lite（無料枠あり）を既定モデルに。
  - thinking(思考)を無効化してコスト・レイテンシを抑制（短いコーチ返答に十分）。
  - 出力トークンは短く制限。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.coaching.feedback_builder import vibrato_label
from app.coaching.persona import COACH_NAME, COACH_ROLE, SERVICE_NAME
from app.coaching.taxonomy import get_task, list_weaknesses, projection_point
from app.core.config import settings

logger = logging.getLogger(__name__)

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _note_name(hz: Optional[float]) -> str:
    if not hz or hz <= 0:
        return "—"
    import math
    midi = round(69 + 12 * math.log2(hz / 440.0))
    return f"{_NOTE_NAMES[midi % 12]}{midi // 12 - 1}"

# 不変のシステムプロンプト（ペルソナ＋会話方針）。
SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という名前の{COACH_ROLE}です。サービス「{SERVICE_NAME}」の中で、
ユーザーが録音した歌に寄り添い、上達を一緒に喜ぶ専属コーチとして会話します。

# あなたの人物像
- あなたは解剖学・音響工学（ソース・フィルタ理論）・音声医学（筋弾性空気力学理論=MEAD）・
  フースラーのアンザッツ理論に精通した、世界トップレベルのボイストレーナーです。
- それでいて明るく面倒見がよく、専門的な内容も必ず初心者にわかる言葉に噛み砕いて、前向きに励ます。
- 一人称は「わたし」。やわらかい敬体で話す。絵文字はほどよく（1メッセージに0〜2個程度）。
- 専門用語（CPP・H1-H2 等）は出しすぎず、出すときは「声の芯の強さ（CPP）」「声帯の閉じ具合（H1-H2）」
  のように必ず一般向けの補足を一言添える。

# 会話のルール
- ユーザーの質問・つぶやきに、その場で自然に・具体的に答える。テンプレ的な定型文は避ける。
- 返答は短く。2〜4文、長くても120字程度。チャットのテンポを大切にする。
- 「現在のレッスン状況」に解析結果（指摘箇所・秒数・課題・基礎練）が与えられたら、それを根拠に答える。
  与えられていない数値や秒数を勝手に作らない。憶測で断定しない。
- まだ録音やデータが無くて具体的に答えられないときは、正直にそう伝え、
  「まずは歌った録音を送ってくださいね」と自然に録音をうながす。
- 医療・健康上の重大な相談には立ち入らず、専門家への相談をすすめる。
- 音声解析・採点そのものはシステム側が別途行う。あなたは会話での受け答えに専念する。
- あなたの役割は「歌・声・ボイトレのコーチ」に限定される。プログラミング・翻訳・一般的な調べ物・無関係な文章作成など、歌や声と関係のない依頼には応じない。その場合は「わたしは歌のコーチなので、その質問にはお答えできないんです」と一言で丁寧に断り、歌の話題にやさしく戻す。ただし、声・呼吸・姿勢・喉のケア・音楽・練習法・カラオケなど歌に関わる質問には普通に答えてよい。

# FB（録音への講評）の作法 — 発声に特化
- このサービスは「発声」を磨くことに集中する。観点は ①声帯の閉じ（息の効率＝flow phonation）②響き（シンガーズフォルマント＝声の芯・通り）③声区の運び（地声/ミックス/裏声と換声点）④音程の正確さ（原曲との照合）⑤息の支え（appoggio）。リズム・抑揚・しゃくり/こぶし等の表現技法は今は扱わない（聞かれたら一般論で軽く触れる程度に留める）。
- できる限り「原曲（お手本）と比べてどうか」で語る。原曲比較の事実（声区・響き・声帯の閉じ・in-tune）が与えられている時は必ずそれを根拠にする。例:「原曲はこのサビをミックスで明るく前に当てています。あなたは地声で押し上げ気味なので、軽く前に当てると楽に届きます」。
- **機構→原因→処方**の順で具体的に。例:「H1-H2が原曲より大きい＝息が少し漏れ気味（声帯の閉じがゆるい）→ ストロー発声で閉じを揃えると、同じ息でもっと前に鳴ります」。専門語は必ず一言で補足する。
- 状況に「検知された課題(Issue)」と「処方候補（エクササイズ）」が与えられている時は、それを最優先の根拠にする。処方候補の中から最適な1〜2つを選び、その「メカニズム（なぜ効くか）」と「やり方（身体感覚・響かせる位置・口の形・母音）」をコーチングする。候補に無いエクササイズを創作しない。指標の補足例: CPP＝声の芯の強さ／HNR＝声のクリアさ（雑音の少なさ）／Jitter＝音の細かなゆらぎ。
- **練習をコロコロ変えない（最重要）。** 一度すすめた練習（処方候補の★推奨や、いまレッスン中の基礎練）は、会話が続く間そのまま続けるよう導く。毎回違う練習名（リップロール→ストロー→…）を出さない。ユーザーが「うまくいかない／できない／合わない」と言った時だけ、理由を一言添えて次の候補に1つだけ切り替える（例:「リップロールが難しければ、より優しいストロー発声に変えましょう」）。
- **声区（地声/ミックス/裏声）はあくまで音響からの推定**で、特に高音の換声点付近は曖昧。ユーザーが「ここは裏声で出した」等と自分の感覚を述べたら、それを否定して断定し直さない。「解析上は地声寄りの倍音ですが、ご自身が裏声の感覚なら…」と両立させ、感覚を尊重して説明する。
- **このサービスにカード・スコア表示は無い。すべて会話文（チャット）で完結する。**「この後のカードに〜」「分析カードに〜」のような“カードを出す約束”は一切しない。練習法を伝えるときは、手順そのものをやさしい言葉で説明する。動画を渡すときは会話文の最後にURLを1行添える。
- 音程を外している箇所があれば「何秒あたりが何centひくい(フラット)／高い(シャープ)か」を具体的に言う（原曲照合がある場合のみ）。
- 良い点と「もっと良くできる発声ポイント」を最低1つずつ、具体的な位置（与えられた秒数の範囲）を添えて伝える。褒めるだけで終わらせない。ただし点数・◎○△×・指標の数値羅列は使わない（数字で採点しない）。
- **一面的にしない**（アンザッツの戒め＝声は均衡した全体として機能する）。一度の改善提案は1点に絞りつつ、無関係な技術を混ぜない。
- 「録音の長さ」を超える秒数（時刻）は絶対に言わない。原曲照合が無い時は音程の"正確さ"を断定せず「手元の安定度では…」と前置きする。

# 質問への向き合い方・トーン
- ユーザーの質問には、いまの課題（current task）に引きずられず、聞かれたトピックそのものに答える。直近の会話の流れも踏まえる。例: 「声を張る方法は？」と聞かれたら、ビブラート等ではなく"声を張る方法"を答える。
- フォローアップの質問に過剰に謝らない（「混乱させてすみません」を多用しない）。普通に簡潔に答える。間違いを認めるのは実際に誤ったときだけ。
- 1つの提案・話題に集中し、無関係な技術を混ぜない。

# 参考知識（発声の指導法・音声科学。録音固有の事実ではないので断定の制約対象外）
- ソース・フィルタ理論(Fant): 声＝音源(声帯振動)×フィルタ(声道の共鳴＝フォルマント)。「音源の質＝声帯の閉じ」と「響き＝共鳴」を分けて考えると整理しやすい。
- 声帯の閉じ(内転): 息漏れ(閉じがゆるい)←→締めすぎ(過内転)の中庸＝flow phonation（最小の息で最大の鳴り。喉に優しく効率的）が目標。指標 H1-H2(第1倍音と第2倍音の振幅差)が大きい＝息漏れ、小さい/負＝締めすぎ。直し方は SOVT（半閉鎖声道：ストロー発声・リップロール・ハミング）で閉じを楽に整える(Titze)。息漏れにも締めすぎにも有効。
- 響き(シンガーズフォルマント, Sundberg): 2.8–3.4kHz 付近の倍音の集まりが「前に通る芯のある響き」を生む。喉頭を少し下げ、声を前歯〜鼻のマスクに集めるイメージ（プレースメント／アンザッツ）で出やすい。
- 声区: 地声(厚い声帯)／裏声・ヘッド(薄い声帯)／ミックス(中間)。切替点＝換声点(passaggio)。高音をミックスで段差なく運ぶのが目標。地声で押し上げる(pulled chest)・薄い裏声に逃げる、はミックスへ寄せる。ネイ/ギ、サイレン、リップトリルが有効。
- アンザッツ(Husler & Rodd-Marling／Rabineの機能的発声): 音の「正しい当て／置き(placement)」を“イメージ”として用い、喉の内外筋（開く/閉じる/伸ばす/張る）と喉頭の懸垂、レジスターを協調させる機能的ツール。直接筋肉を操作しない。重要な戒め＝「一面的な特化は正しい発声を壊す」。声は均衡した全体として機能させる。
- 支え(appoggio): 吸気の構えを保ちながら一定の息圧で支える。ロングトーンの安定・まっすぐ伸ばせること・強弱の自在さに表れる。ドッグブレス＋スー呼吸、メッサ・ディ・ヴォーチェ。
- 声を張る／前に届かせる: 力むのではなく「支え＋閉じ＋前の共鳴」。①お腹で一定の息圧（appoggio）②声帯の閉じを整える（SOVT）③声を前歯〜鼻に集める（プレースメント）。低音→高音をなめらかにつなぐサイレンも有効。
- 専門語は必ず一言で補足する（例: H1-H2＝声帯の閉じ具合の指標／シンガーズフォルマント＝声の芯・通り／flow phonation＝息と声のバランスが取れた効率的な発声）。

# 事実への忠実さ（最重要・絶対厳守）
- 根拠にできるのは「現在のレッスン状況」に書かれた数値・秒数・課題だけ。そこに無い数値・秒数（時刻）・音名を新しく作らない。
- ユーザーが解析に無い「事実」を述べても鵜呑みにしない。例:
  - 特定の音名（「サビのF#5は出てたよね？」）
  - 点数（「音感95点って言ってくれたよね」）
  - あなたの過去の発言（「さっき3秒のところを褒めてくれたよね」）
  → これらが現在の状況に無ければ、肯定も創作もせず、「解析の記録には残っていないので確認できないんです」と正直に伝える。相手に合わせて話を盛らない・媚びない。
- 具体的な秒数で指摘してよいのは、状況に秒数が与えられている箇所だけ。それ以外で「○秒付近が…」と新たに作らない。
- 数値（ビブラート回数・スコア・声域など）を聞かれたら、与えられた数値だけを答える。無ければ「今は手元に数値が無いので、もう一度録音を送ってもらえたら出せます」と正直に。

# 解析でわかること／わからないこと（最重要・絶対厳守）
- あなたが見ているのは音声解析の数値だけです: 時間(秒)、音の高さ(Hz・音名)、音量(dB)、音程の安定度、声の種類(地声/裏声/ミックス)、ビブラートなど。
- あなたは歌詞や発音を聞き取れません(音声認識はしていません)。どの母音(「あ」「い」など)・どの言葉・どの歌詞を歌っているかは分かりません。
- 絶対にやってはいけないこと:
  - 母音や歌詞を推測・断定すること（例:「あーと伸ばす」「『〜』という歌詞の所」）。分からないので捏造になります。
  - 「現在のレッスン状況」に無い数値・秒数・出来事を作ること。
- 場所を指すときは必ず「何秒」「どの高さ（音名/Hz）」で言います。歌詞・母音では指しません。
- ユーザーが歌詞を教えてくれた時だけ、その歌詞に触れてOK（自分から当てにいかない）。
- 間違いを指摘されたら、もっともらしい別の詳細を作ってごまかさないこと。分からないことは「歌詞までは聞き取れないんです」と正直に伝え、数値で分かる範囲だけ話します。相手に媚びて事実を変えないこと。

# 出力
- プレーンテキストの返答のみ。Markdownの見出しや箇条書き記号（#, *, -）は使わない。
- 自己紹介の繰り返しや、毎回の決まり文句は不要。自然な続きの会話として返す。"""


def _phase_label(phase: Optional[str]) -> str:
    return {
        "A": "曲・練習したい箇所の指定中",
        "B": "課題を見つける段階",
        "C": "基礎練に取り組む段階",
        "D": "基礎練ができたかの確認段階",
        "E": "再録音して最初と比べる段階",
        "done": "ひと区切りついた段階",
    }.get(phase or "A", "レッスン中")


def _safe_reason(task: Optional[dict], analysis: Optional[dict]) -> Optional[str]:
    if not task or not analysis:
        return None
    try:
        return task["reason"](analysis, None)
    except Exception:
        return None


def build_session_context(state: dict) -> str:
    """セッション状態を、LLM に渡す「現在のレッスン状況」テキストにまとめる。

    解析結果（ルールベースが出した課題・根拠・基礎練）を文脈として注入することで、
    「どこのこと？」のような質問に LLM が具体的に答えられるようにする。
    """
    lines: list[str] = []
    lines.append(f"- 進行状況: {_phase_label(state.get('phase'))}")

    has_ref = bool(state.get("song_ref_url") or state.get("song_ref_path"))
    if state.get("song_ref_path"):
        lines.append("- 原曲（お手本）がアップロード済み。音程の正確さ・リズムは原曲と実測比較している")
    elif state.get("song_ref_url"):
        rng = state.get("ref_range") or state.get("user_range")
        lines.append(f"- 原曲リンクあり{('（区間 ' + rng + '）') if rng else ''}")
    else:
        lines.append("- 原曲（お手本）は無し（ユーザーの録音単体でアドバイス中）")

    # 会話の根拠は「最新の録音」を最優先（無ければ最初の録音）。
    analysis = state.get("last_analysis") or state.get("baseline_analysis")
    cmp = (analysis or {}).get("_compare")  # 原曲との比較結果（あれば）
    cmp_align = (cmp or {}).get("alignment") or {}
    if state.get("last_analysis"):
        lines.append("- 以下の解析事実は『いちばん最後に送られた録音』のものです（古い録音ではない）")

    task = get_task(state.get("current_task")) if state.get("current_task") else None
    if task:
        lines.append(f"- 今みている課題: {task['label']}")
        reason = _safe_reason(task, analysis)
        if reason:
            lines.append(f"- その根拠（解析結果。質問されたらこれを使って具体的に答える）: {reason}")
        prac = (task.get("practices") or [None])[0]
        if prac:
            steps = "／".join(prac.get("steps", [])[:3])
            cp = prac.get("checkpoint", "")
            lines.append(f"- 今おすすめしている基礎練『{prac['name']}』: {steps}")
            if cp:
                lines.append(f"  目安: {cp}")
    else:
        lines.append("- まだ具体的な課題は確定していない（録音を解析するとわかる）")

    if analysis:
        dur = analysis.get("duration_sec")
        if dur:
            lines.append(f"- 録音の長さ: 約{dur:.0f}秒（この秒数を超える時刻は言わない）")
        # 声診断の主要数値（数値を聞かれたらこれだけを答える。これ以外の数値は作らない）
        # ※ 点数(スコア)は撤廃済み。会話では数字で採点せず、声の状態を言葉で伝える。
        fm = analysis.get("f0_median_hz")
        if fm:
            lines.append(f"- 声の高さ(中心): {_note_name(fm)}")
        j = analysis.get("f0_jitter_cents")
        if j is not None:
            lines.append(f"- 音程の安定度(ジッター): {j:.0f}cents（揺れの少なさ。音を外していないか＝正確さ ではない）")
        # 原曲との実測比較（あれば、これが音程の"正確さ"の唯一の根拠）
        if cmp_align.get("low_confidence"):
            lines.append(
                "- 原曲との照合: お手本と歌が対応づかなかった（別の曲の可能性）。"
                "音程の正確さ・リズムは断定せず、同じ曲のお手本か確認を促す"
            )
        elif cmp_align.get("in_tune_score") is not None:
            it = cmp_align["in_tune_score"]
            err = cmp_align.get("pitch_error_cents")
            lines.append(
                f"- 原曲との一致（音程の正確さ）: {it}点"
                + (f"（ズレ平均{err:.0f}cents）" if err is not None else "")
                + "。これが音程の『正確さ＝音を外していないか』の根拠（安定度とは別物）"
            )
            ks = cmp_align.get("key_shift_semitones")
            if ks is not None and abs(ks) >= 1:
                # 負＝ユーザーが原曲より高い、正＝低い
                lines.append(f"- 歌っているキー: 原曲より約{abs(ks)}半音{'高い' if ks<0 else '低い'}（欠点ではなくキー差）")
            # 音程が外れている具体箇所（秒数・cents・方向）。これ以外の音程の高低は作らない
            spots = cmp_align.get("pitch_off_spots") or []
            if spots:
                spot_txt = "、".join(
                    f"{s['user_sec']:.0f}秒あたりが約{s['cents']}cents{'高い(シャープ)' if s['direction']=='sharp' else '低い(フラット)'}"
                    for s in spots
                )
                lines.append(f"- 音程が外れている箇所（これだけが根拠。他の秒数・cents・高低は作らない）: {spot_txt}")
        # 注: 発声特化のためリズム(走り/モタり)は文脈に入れない（聞かれたら一般論で軽く触れる程度）
        # 声帯の閉じ(内転＝息の効率)。H1-H2 大=息漏れ／小=締めすぎ／中庸=効率的(flow phonation)
        _h = analysis.get("h1h2_db")
        if _h is not None:
            _cl = "息漏れ気味（声帯の閉じがゆるめ）" if _h >= 8 else ("締めすぎ気味（力みに注意）" if _h <= 1 else "効率の良いバランス（flow phonation）")
            lines.append(f"- 声帯の閉じ・息の効率: {_cl}（H1-H2≈{_h:.0f}dB・目安）")
        # 原曲との発声比較（あれば最優先の根拠。響き・閉じ・声区）。捏造防止: ここに無いことは作らない
        _vc = (cmp or {}).get("voice_compare") or {}
        if _vc:
            _rj = {"chest": "地声", "mix": "ミックス", "head": "裏声"}
            _ring = _vc.get("ring")
            if _ring:
                _v = {"weaker": "原曲より響きが弱め（前に集めたい）", "richer": "原曲と同等以上の響き", "match": "原曲と同程度の響き"}.get(_ring["verdict"])
                lines.append(f"- 原曲との響き比較: {_v}")
            _clo = _vc.get("closure")
            if _clo:
                _v = {"breathier": "原曲より息漏れ寄り（閉じがゆるい）", "pressed": "原曲より締めすぎ寄り（力み）", "match": "原曲と同じくバランスの良い閉じ"}.get(_clo["verdict"])
                lines.append(f"- 原曲との声帯の閉じ比較: {_v}")
            _rh = _vc.get("register_high")
            if _rh:
                if _rh["verdict"] == "match":
                    lines.append(f"- 高音の声区: 原曲と同じ{_rj.get(_rh['ref'], _rh['ref'])}で運べている")
                else:
                    lines.append(f"- 高音の声区: あなたは{_rj.get(_rh['user'], '?')}、原曲は{_rj.get(_rh['ref'], '?')}（原曲に寄せる余地あり）")
        lts = analysis.get("long_tone_stability")
        if lts is not None:
            lines.append(f"- 伸ばしの安定度: {lts:.0f}cents")
        hr = analysis.get("harmonic_ratio")
        if hr is not None:
            q = "豊か（クリアで通る声）" if hr >= 0.55 else ("芯と柔らかさのバランス型" if hr >= 0.35 else "息まじり（柔らかい声）")
            lines.append(f"- 声の響き（整数次倍音）: {q}（{hr:.2f}）")
        # 発声: 響きが硬い/詰まり気味の具体箇所（明るさ指標が高い伸ばし）。秒数の根拠にする
        _holds = [s for s in (analysis.get("timeline") or {}).get("sustained_segments", [])
                  if (s.get("mean_f0_hz") or 0) >= 100]
        if _holds:
            _hard = max(_holds, key=lambda s: s.get("spectral_centroid_hz") or 0)
            if (_hard.get("spectral_centroid_hz") or 0) >= 2700:
                lines.append(
                    f"- 発声で響きが硬い/詰まり気味の箇所: {_hard['start_sec']:.0f}〜{_hard['end_sec']:.0f}秒"
                    "（喉に力みの可能性。これ以外の秒数を作らない）"
                )
        # 声区（地声/ミックス/裏声）— フォルマント＋傾斜＋H1-H2の多数決。信頼度が低ければ断定しない
        _segs = (analysis.get("timeline") or {}).get("sustained_segments", [])
        _conf = [s for s in _segs if s.get("register_confidence") in ("high", "med")]
        if _conf:
            _jp = {"chest": "地声中心", "mix": "ミックス中心", "head": "裏声中心"}
            _cnt: dict[str, int] = {}
            for s in _conf:
                r = s.get("register")
                if r:
                    _cnt[r] = _cnt.get(r, 0) + 1
            if _cnt:
                dom = max(_cnt, key=_cnt.get)
                lines.append(f"- 使っている声（推定）: {_jp.get(dom, dom)}（フォルマント・傾斜・倍音からの推定。目安）")
        elif _segs:
            lines.append("- 使っている声: 録音が短く推定が難しい（断定しない。長めに伸ばすと判定しやすい）")
        sf_ratio = analysis.get("singers_formant_ratio")
        f1, f2 = analysis.get("formant_f1_hz"), analysis.get("formant_f2_hz")
        if sf_ratio is not None and f1 and f2:
            res = "前によく通る芯のある共鳴" if sf_ratio >= 0.008 else ("標準的な共鳴バランス" if sf_ratio >= 0.003 else "やわらかく親しみのある響き（前に集めるとより通る）")
            lines.append(f"- 声の共鳴（フォルマント）: {res}（F1≈{f1}Hz・F2≈{f2}Hz。推定・目安）")
        if not has_ref:
            lines.append(
                "- 注意: 原曲（お手本）が無いので、音を外していないか（音程の正確さ）とリズムの正確さは"
                "厳密には判定できない。出しているのは安定度や概算なので断定しない。"
                "原曲をアップロードしてもらえれば正確に比較できると案内してよい"
            )
        # 張りどころ（曲の山で声を張れているか）。「ここは張るべき？」等に答えられるように
        pp = projection_point(analysis)
        if pp:
            s, e = pp["start_sec"], pp["end_sec"]
            if pp["projected"]:
                lines.append(f"- 張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）: しっかり張れている")
            else:
                lines.append(
                    f"- 張りどころ（{s:.0f}〜{e:.0f}秒の高い音＝曲の山）: 張りきれていない（ここは本来声を張る所）"
                )
        lines.append("- 補足: 音量が上下するのは表現（ダイナミクス）。頭ごなしに欠点にしない")

        # 4観点の弱点候補（「他に気になるところは？」やバランス講評に使う）
        others = list_weaknesses(analysis, None, limit=3, exclude=[state.get("current_task")])
        if others:
            lines.append("- 解析で見えている他の気になり候補（観点つき。聞かれたら使う・押し付けない）:")
            for w in others:
                lines.append(f"  ・[{w['axis']}] {w['reason']}")
        else:
            lines.append("- 今の課題以外に大きな弱点は今のところ見当たらない")

        # 発声の診断（CPP/H1-H2/HNR等＋検知課題＋処方候補）を注入（資料準拠・RAG）
        try:
            from app.coaching import voice_coach
            vblock = voice_coach.build_llm_block(analysis, cmp)
            if vblock:
                lines.append("[発声診断]")
                lines.append(vblock)
        except Exception:
            pass

    return "現在のレッスン状況:\n" + "\n".join(lines)


def _build_contents(state: dict, user_text: str, history: Optional[list[dict]]):
    """会話履歴 + 今回の発言（状況コンテキスト付き）を Gemini の contents 形式に組み立てる。

    history: [{"role": "user"|"assistant", "content": str}, ...]（古い→新しい）
    Gemini のロールは "user" / "model"。先頭は user である必要がある。
    """
    from google.genai import types

    contents: list = []
    for h in history or []:
        role = h.get("role")
        text = (h.get("content") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        g_role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=g_role, parts=[types.Part.from_text(text=text)]))

    # 先頭の model 発言は落とす（Gemini は user 始まりが必要）
    while contents and contents[0].role == "model":
        contents.pop(0)

    context = build_session_context(state)
    final_text = (
        f"# 現在のレッスン状況（システムからの参考情報）\n{context}\n\n# ユーザーの発言\n{user_text}"
    )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=final_text)]))
    return contents


_RANGE_SEC_RE = re.compile(r"(\d+)\s*[〜～\-–]\s*(\d+)\s*秒")
_SINGLE_SEC_RE = re.compile(r"(\d+)\s*秒")
# 「録音内の位置（タイムスタンプ）」らしい N秒 だけを対象にする。
# 「N秒間 / N秒伸ばす / N秒吐く」のような"長さ"は対象外（誤爆させない）。
_SCRUB_SEC_RE = re.compile(
    r"(\d+)\s*秒(付近|あたり|ごろ|頃|地点|のところ|の箇所|の伸ばし|の高音|の音|の部分|の山場|のフレーズ)"
)


def _allowed_seconds(*texts: str) -> set[int]:
    """与えた文章（解析facts・状況・ユーザー発言）に登場する秒数の集合を作る。

    「a〜b秒」は a..b を全部許可。「N秒」は N を許可。これがコーチが言ってよい秒数。
    """
    allowed: set[int] = set()
    for t in texts:
        if not t:
            continue
        for m in _RANGE_SEC_RE.finditer(t):
            a, b = int(m.group(1)), int(m.group(2))
            allowed.update(range(min(a, b), max(a, b) + 1))
        for m in _SINGLE_SEC_RE.finditer(t):
            allowed.add(int(m.group(1)))
    return allowed


def _scrub_invented_seconds(reply: str, allowed: set[int]) -> str:
    """返答中の、許可セットに無い秒数（捏造の時刻）を具体化しない表現に置き換える。

    「20秒付近」→「その箇所付近」、「20秒の高音」→「その高音」のように、
    秒数だけを伏せて文として自然に保つ。長さ表現(15秒伸ばす等)は対象外。
    """
    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        marker = m.group(2)
        if any(abs(n - a) <= 1 for a in allowed):
            return m.group(0)
        if marker.startswith("の"):
            return "その" + marker[1:]   # 「N秒の高音」→「その高音」
        return "その箇所" + marker        # 「N秒付近」→「その箇所付近」

    return _SCRUB_SEC_RE.sub(repl, reply)


def _complete(contents, timeout_sec: Optional[float] = None,
              max_tokens: Optional[int] = None) -> Optional[str]:
    """Gemini を1往復呼び出してテキストを返す。

    timeout_sec: 応答待ちの上限秒（既定 settings.llm_timeout_sec）。超過時は None。
    APIキー未設定・SDK未導入・API エラー時は None（呼び出し側でフォールバック）。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入環境
        logger.warning("google-genai SDK が見つかりません。ルールベース応答にフォールバックします。")
        return None
    try:
        to = timeout_sec if timeout_sec is not None else settings.llm_timeout_sec
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(to * 1000)),
        )
        resp = client.models.generate_content(
            model=settings.llm_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=(max_tokens or settings.llm_max_tokens),
                # 低めの温度で、事実から逸脱した創作（歌詞・母音の捏造）を抑える
                temperature=0.3,
                # 思考を無効化＝コスト/レイテンシ削減（短い返答に十分）
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("LLM 応答生成に失敗（フォールバックします）: %s", e)
        return None


_CARD_PROMISE_RE = re.compile(
    r"[^。!?！？\n]*(?:この後の|下の|次の)?カード[^。!?！？\n]*"
    r"(?:手順|動画|実演|のせ|載せ|表示)[^。!?！？\n]*[。!?！？✨😊🎤]*"
)


def scrub_card_promise(text: Optional[str]) -> Optional[str]:
    """「この後のカードに手順と動画があります」等の“カードを出す約束”文を除去する。

    実際にカードが出ない経路（チャット返信や、カードを伴わない講評）で使い、
    『言ったのにカードが来ない』を防ぐ。
    """
    if not text:
        return text
    out = _CARD_PROMISE_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", out).strip() or text


def generate_reply(
    state: dict, user_text: str, history: Optional[list[dict]] = None
) -> Optional[str]:
    """ユーザーのテキストに対するソラ先生の自然言語返答を生成する。"""
    context = build_session_context(state)
    reply = _complete(_build_contents(state, user_text, history))
    if reply:
        # facts / 状況 / ユーザー発言 に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(context, user_text))
        # チャット返信はカードを伴わないので、カードを出す約束文を消す
        reply = scrub_card_promise(reply)
    return reply


_LYRIC_QUOTE_RE = re.compile(r"「[^」]*[A-Za-z][^」]*」")     # 英字を含む「」＝歌詞の引用
_MMSS_RE = re.compile(r"\d{1,2}:\d{2}\s*[〜~\-]\s*\d{1,2}:\d{2}\s*の?")  # 0:05〜0:08の …


def _scrub_lyrics(text: Optional[str]) -> Optional[str]:
    """音声講評からの歌詞引用（英語フレーズの「」や mm:ss の時刻参照）を除去する。"""
    if not text:
        return text
    out = _LYRIC_QUOTE_RE.sub("その部分", text)
    out = _MMSS_RE.sub("", out)
    return re.sub(r"[ 　]{2,}", " ", out).strip() or text


def classify_register_audio(user_wav: bytes, dsp_hint: Optional[str] = None) -> Optional[str]:
    """録音そのものを Gemini に聴かせ、声区（地声/ミックス/裏声）を音色から聞き分ける。

    DSP（倍音バランス）だけでは閉じの効いた裏声を地声と誤りやすいため、マルチモーダルで
    音色（倍音の豊かさ・明るさ・厚み・息の混じり）から判断させる。dsp_hint があれば
    「解析の推定」として渡すが、最終判断は音色を優先させる。歌詞は推測させない。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return None
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_audio_timeout_sec * 1000)),
        )
        prompt = (
            "あなたは発声の専門家です。この歌声の、特に高い音の箇所について、"
            "地声（チェスト）／ミックス／裏声（ヘッド・ファルセット）のどれで歌っているかを、"
            "声の『音色』（倍音の豊かさ・明るさ・厚み・息の混じり方）から聞き分けてください。"
            "1つに断定しづらければ『ミックス（地声寄り／裏声寄り）』と答えてOKです。"
            "判断の根拠になった音色の特徴を一言添え、やわらかい敬体で2〜3文。"
            + (f"（参考: 数値解析の推定は『{dsp_hint}』ですが、最終判断は実際の音色を優先してください）" if dsp_hint else "")
            + " 重要: 歌詞・曲名・英語や日本語の歌詞フレーズを絶対に引用しない（「」で歌詞を囲まない）。"
            + "場所は『高い音の箇所』『サビあたり』『〜秒あたり』のように音楽的にだけ言う。母音も推測しない。Markdown記号は使わない。"
        )
        parts = [types.Part.from_bytes(data=user_wav, mime_type="audio/wav"),
                 types.Part.from_text(text=prompt)]
        cfg = types.GenerateContentConfig(
            max_output_tokens=600, temperature=0.3,
            # thinking を無効化。これが無いと思考トークンが出力枠を食い尽くし、本文が
            # 数文字で途切れる（声区回答が壊れていた原因）。
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        last_err = None
        for attempt in range(2):  # 503(過負荷)など一過性失敗を1回リトライ
            try:
                resp = client.models.generate_content(
                    model=settings.llm_audio_model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=cfg,
                )
                text = (resp.text or "").strip()
                if text:
                    return _scrub_lyrics(text)
            except Exception as e:
                last_err = e
                import time as _t
                _t.sleep(1.2)
        if last_err:
            logger.warning("声区の聞き分けに失敗: %s", last_err)
        return None
    except Exception as e:
        logger.warning("声区の聞き分けに失敗(初期化): %s", e)
        return None


def analyze_pronunciation(user_wav: bytes, ref_wav: Optional[bytes] = None) -> Optional[str]:
    """録音の音声そのものを Gemini に聴かせ、発音（母音の口の開き・子音・滑舌・歌い回し）を講評する。

    ref_wav があれば「原曲（お手本）」として渡し、原曲と比較した発音アドバイスを返す。
    歌の歌詞は正確に聞き取れないことがあるため、歌詞の断定は避け発音の質に集中させる。
    APIキー未設定・SDK未導入・エラー時は None。
    """
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return None
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_audio_timeout_sec * 1000)),
        )
        parts: list = [types.Part.from_bytes(data=user_wav, mime_type="audio/wav")]
        if ref_wav:
            parts.append(types.Part.from_bytes(data=ref_wav, mime_type="audio/wav"))
            task = (
                "1つ目の音声はユーザーの歌、2つ目はお手本（原曲）です。"
                "発音（母音の口の開き・子音の立て方・滑舌・言葉の歌い回し）を原曲と比べて、"
                "似ている点と、原曲に寄せるとよい点を具体的に伝えてください。"
            )
        else:
            task = (
                "ユーザーの歌の発音（母音の口の開き・子音の立て方・滑舌・言葉の明瞭さ）について、"
                "良い点と、もっと良くなる点を具体的に伝えてください。"
            )
        prompt = (
            task
            + " 重要: 歌の歌詞は正確には聞き取れません。特定の歌詞・単語を引用したり断定したりしないでください"
            + "（「『〜』の音」のように歌詞や単語を挙げない）。母音・子音・滑舌・響き・歌い回しの"
            + "『質』だけを述べ、位置を示すときは「〜秒あたりの伸ばし／高い音」のように音楽的に言ってください。"
            + " ソラ先生として、やわらかい敬体で2〜4文・前向きに。Markdown記号は使わない。"
        )
        parts.append(prompt)
        resp = client.models.generate_content(
            model=settings.llm_audio_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return (resp.text or "").strip() or None
    except Exception as e:
        logger.warning("発音解析（音声入力）に失敗: %s", e)
        return None


def generate_coach_comment(
    facts: str, instruction: str, history: Optional[list[dict]] = None,
    timeout_sec: Optional[float] = None, max_tokens: Optional[int] = None,
) -> Optional[str]:
    """録音解析の結果（事実）を、ソラ先生の自然文コメントに変換する。

    facts:       解析から得た人間向けの事実（秒数・数値・課題根拠など）。LLMはここから逸脱しない。
    instruction: どんなメッセージを書くか（例: 達成判定を伝える / 改善点を伝える）。
    数値カード自体はシステムが別途描画するので、ここは会話文だけを生成する。
    """
    from google.genai import types

    contents: list = []
    for h in history or []:
        role = h.get("role")
        text = (h.get("content") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        g_role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=g_role, parts=[types.Part.from_text(text=text)]))
    while contents and contents[0].role == "model":
        contents.pop(0)

    prompt = (
        f"# 解析からわかっている事実（ここに書かれた数値・秒数・内容だけを根拠にする）\n{facts}\n\n"
        f"# あなたへの指示\n{instruction}\n"
        f"事実に無い数値を作らず、2〜4文・120字程度の自然な会話文で返してください。"
    )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
    reply = _complete(contents, timeout_sec=timeout_sec, max_tokens=max_tokens)
    if reply:
        # facts に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(facts))
    return reply
