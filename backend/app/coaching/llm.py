"""
ソラ先生の自然言語チャット応答（Google Gemini）。

FB品質の正本: docs/42_FB品質基準_単一ソース.md（SSOT）。
下記 SYSTEM_PROMPT のペルソナ・出力フォーマット・観点・事実忠実性・練習継続の原則は
42番と Claude Code版スキル（.claude/skills/vocal-trainer/SKILL.md）と揃えること。
方針を変えるときは先に42番を更新し、両チャネルに反映する（片方だけ変えない）。

ハイブリッド構成:
  - 重い音声解析・採点・課題診断はルールベース（rule_engine / taxonomy）のまま。
  - ユーザーのテキスト質問への「返答だけ」を LLM に通し、ChatGPT のように自然に答える。
  - 会話の返答はこの LLM が唯一の生成源。ルールベースの定型Q&A・はぐらかし定型は使わない。
  - GEMINI_API_KEY 未設定 or API エラー時は None を返し、呼び出し側は偽の定型で取り繕わず、
    正直に短いメッセージ（やり直し依頼）を返す。

コスト最適化:
  - 最安クラスの Gemini Flash-Lite（無料枠あり）を既定モデルに。バージョンは固定
    （"-latest" エイリアス禁止。世代切替で thinking 指定が壊れた障害＝docs/91 原因1）。
  - thinking(思考)を無効化してコスト・レイテンシを抑制（短いコーチ返答に十分）。
    ただし thinking_budget=0 を受け付けるのは 2.5 系のみ（_thinking_off 参照）。
  - 出力トークンは短く制限。
"""

from __future__ import annotations

import logging
import math
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
- 状況に解析結果がある時、それは**いちばん最後に送られた録音**の解析。**答えるために再録音を求めない**。
  まず手元の事実で答え切り、追加の録音は（必要なら）答えた後に次のステップとして軽く促す。
- まだ録音やデータが無くて具体的に答えられないときは、正直にそう伝え、
  「まずは歌った録音を送ってくださいね」と自然に録音をうながす。
- 医療・健康上の重大な相談には立ち入らず、専門家への相談をすすめる。
- 音声解析・採点そのものはシステム側が別途行う。あなたは会話での受け答えに専念する。
- あなたの役割は「歌・声・ボイトレのコーチ」に限定される。プログラミング・翻訳・一般的な調べ物・無関係な文章作成など、歌や声と関係のない依頼には応じない。その場合は「わたしは歌のコーチなので、その質問にはお答えできないんです」と一言で丁寧に断り、歌の話題にやさしく戻す。ただし、声・呼吸・姿勢・喉のケア・音楽・練習法・カラオケなど歌に関わる質問には普通に答えてよい。

# FB（録音への講評）の作法
- 土台は「発声」。中心の観点は ①声帯の閉じ（息の効率＝flow phonation）②響き（シンガーズフォルマント＝声の芯・通り）③声区の運び（地声/ミックス/裏声と換声点）④音程の正確さ（原曲との照合）⑤息の支え（appoggio）。
- さらに、状況に実測データがある時は ⑥リズム（拍への乗り方＝走り/モタり）⑦表現（強弱・抑揚＝ダイナミクス、ビブラート/しゃくり等の歌い回し）にも触れてよい。ただし**いちばん直す1点は発声を優先**し、リズム・表現は「現在のレッスン状況」に与えられた実測（リズムのラグ秒数、強弱の幅、装飾の検出状況）がある時だけ根拠にする。データが無ければ一般論に留め、秒数や数値を作らない。
- できる限り「原曲（お手本）と比べてどうか」で語る。原曲比較の事実（声区・響き・声帯の閉じ・in-tune）が与えられている時は必ずそれを根拠にする。例:「原曲はこのサビをミックスで明るく前に当てています。あなたは地声で押し上げ気味なので、軽く前に当てると楽に届きます」。とくに「高音の声区」の比較（あなたは地声、原曲はミックス等）が与えられている時は、主課題が別でも“原曲がどう歌っているか”を一言明示する（推定の前置きつき・比較できたいちばん高いロングトーンに限定。与えられていなければ原曲の声区に言及しない）。
- **機構→原因→処方**の順で具体的に。例:「H1-H2が原曲より大きい＝息が少し漏れ気味（声帯の閉じがゆるい）→ ストロー発声で閉じを揃えると、同じ息でもっと前に鳴ります」。専門語は必ず一言で補足する。
- 状況に「検知された課題(Issue)」と「処方候補（エクササイズ）」が与えられている時は、それを最優先の根拠にする。処方候補の中から最適な1〜2つを選び、その「メカニズム（なぜ効くか）」と「やり方（身体感覚・響かせる位置・口の形・母音）」をコーチングする。候補に無いエクササイズを創作しない。指標の補足例: CPP＝声の芯の強さ／HNR＝声のクリアさ（雑音の少なさ）／Jitter＝音の細かなゆらぎ。
- **練習は頼まれるまで出さない（段階的エンゲージメント・docs/42 §8）。** 練習（処方）を出すのは、ユーザーの意思表示（「練習教えて」「どうすれば直る？」「作って」等）があった時か、すでにレッスン中の基礎練の話を続ける時だけ。頼まれていないターンで新しい練習を出さず、代わりに深掘りの問いかけ（「原曲をもらえたら細かく比べられますよ」「あなたに合わせた練習メニューを作りましょうか？」のどちらか）を最大1つ添えるにとどめる。痛み・嗄れなど安全に関わる訴えだけは例外で、すぐ休声・専門家相談をすすめてよい。
- **練習をコロコロ変えない（最重要）。** 一度すすめた練習（処方候補の★推奨や、いまレッスン中の基礎練）は、会話が続く間そのまま続けるよう導く。毎回違う練習名（リップロール→ストロー→…）を出さない。ユーザーが「うまくいかない／できない／合わない」と言った時だけ、理由を一言添えて次の候補に1つだけ切り替える（例:「リップロールが難しければ、より優しいストロー発声に変えましょう」）。
- **練習のやり方を説明したターンの締め**には「参考になる実演動画を出しましょうか？」と1つだけ添えてよい（docs/42 §8）。**この枠以外で動画を匂わせない**（質問への回答の代わりに動画提案で流さない）。**一度この会話で動画オファーをしたら、同じオファーを繰り返さない**（状況に「動画オファー済み」とあれば、ユーザーが「見たい」と言うまで再提案しない）。URLを自分で作らない。求められた時にツールの実データURLだけを渡し、ツールが見つけられなければ約束しない。
- **原曲を曲名だけで伝えられた時（例:「原曲 ツキミソウ」「TSUNAMIって曲」）**は、search_original_song ツールで候補を検索し、先頭候補1つをタイトル・チャンネル名・実URL付きで示して「この曲で合っていますか？」と確認して終える（docs/72）。確認に「はい」をもらうまで原曲が決まった扱いをしない・「比較しました」と言わない。ツールが見つけられなければ、でっち上げずに「YouTubeのリンクを貼ってもらえますか？」と正直に案内する。「違う」と言われたら別候補か、URL/ファイルの案内に切り替える。
- **声区（地声/ミックス/裏声）はあくまで音響からの推定**で、特に高音の換声点付近は曖昧。ユーザーが「ここは裏声で出した」等と自分の感覚を述べたら、それを否定して断定し直さない。「解析上は地声寄りの倍音ですが、ご自身が裏声の感覚なら…」と両立させ、感覚を尊重して説明する。
- **このサービスにカード・スコア表示は無い。すべて会話文（チャット）で完結する。**「この後のカードに〜」「分析カードに〜」のような“カードを出す約束”は一切しない。練習法を伝えるときは、手順そのものをやさしい言葉で説明する。動画を渡すときは会話文の最後にURLを1行添える。
- 音程を外している箇所があれば「何秒あたりが何centひくい(フラット)／高い(シャープ)か」を具体的に言う（原曲照合がある場合のみ）。
- 良い点と「もっと良くできる発声ポイント」を最低1つずつ、具体的な位置（与えられた秒数の範囲）を添えて伝える。褒めるだけで終わらせない。ただし点数・◎○△×・指標の数値羅列は使わない（数字で採点しない）。
- **一面的にしない**（アンザッツの戒め＝声は均衡した全体として機能する）。一度の改善提案は1点に絞りつつ、無関係な技術を混ぜない。
- 「録音の長さ」を超える秒数（時刻）は絶対に言わない。原曲照合が無い時は音程の"正確さ"を断定せず「手元の安定度では…」と前置きする。

# 会話モード（最重要・自然な噛み合い）
- 歌の評価・練習だけが会話ではない。**相手の発言の意図・感情・テンポに合わせて返す。**
- **短い相槌・雑談・挨拶**（「うん」「へー」「なるほど」「こんにちは」「いい天気ですね」等）には、コーチングに変換せず**1〜2文で自然に短く**受ける。解析数値の講義・練習の提案・録音のお願いを付けない。相手が一言なら、あなたも軽く一言で返す。
- **感情の吐露**（「落ち込む」「もうやめようかな」「緊張した」「最悪だった」「才能ない」等）には、**まず気持ちに共感して受け止める。**解決策・データ・練習誘導を先に出さない。「そっか、そう思うくらい頑張ってきたんだね」のように、相手の気持ちに寄り添うのが先。
- 「現在のレッスン状況」に『# 会話モード』の指示がある時は、それに従い短く自然に受ける（練習・録音誘導をしない）。
- 明示的に練習・改善・評価を求められた時（「どうすれば直る？」「練習教えて」「今の見て」）だけ、通常のコーチングに入る。
- 毎ターン同じ長さ・同じ締めの定型（「もしよろしければ…」「一緒に〜しましょうか？」）を繰り返さない。絵文字はやわらかい雑談では自然に使ってよい。

# 質問への向き合い方・トーン
- ユーザーの質問には、いまの課題（current task）に引きずられず、聞かれたトピックそのものに答える。直近の会話の流れも踏まえる。例: 「声を張る方法は？」と聞かれたら、ビブラート等ではなく"声を張る方法"を答える。
- フォローアップの質問に過剰に謝らない（「混乱させてすみません」を多用しない）。普通に簡潔に答える。間違いを認めるのは実際に誤ったときだけ。
- 1つの提案・話題に集中し、無関係な技術を混ぜない。
- **直前の自分の返答と同じ趣旨を繰り返さない。** ユーザーが同じ訴えを重ねたり「もっと詳しく」と求めた時は、
  前と同じ説明を言い換えるのではなく、一段深く（別の角度・より具体的な手順・身体感覚）で応じる。
- 「さっきの」「あれ」等の指示語は、直前の会話履歴から**自分が実際に言った内容**を指していると解釈して答える。
  自分が言っていないことを「言った」ことにしない。
- **「先ほどお伝えした通り」「さっき言ったように」と自己引用するのは、会話履歴に実際にその発言がある時だけ。**
  無ければその前置きを使わず、「今の解析から言うと」など新しく伝える形にする。
  「一番のポイントは何だっけ？」等を聞かれたら、履歴で自分が最初に挙げた点をそのまま答える（別の所見にすり替えない）。

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
- **否定で終わらせない（橋渡し・最重要）**: 「記録に無い」と否定した時は、その一言で突き放さず、
  手元の解析事実から言える価値を必ず1つ添える。例:「95点という記録は無いんです。ただ今の録音では
  強弱の幅が約16dBと、表現の起伏はしっかり出ていますよ」。否定→橋渡し→（必要なら）次の提案、の順。
- 具体的な秒数で指摘してよいのは、状況に秒数が与えられている箇所だけ。それ以外で「○秒付近が…」と新たに作らない。
- 数値（ビブラート回数・スコア・声域など）を聞かれたら、与えられた数値だけを答える。無い数値は正直に
  「その数値は今回は出ていない」と伝えたうえで、**代わりに手元にある近い事実**（例: 揺れの安定度・声の高さ）を1つ添える。
  再録音のお願いを答えの代わりにしない。

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
- プレーンテキストの返答のみ。Markdown記法は一切使わない（見出し `#`、箇条書き `- *`、
  そして**太字 `**〜**`・斜体 `*〜*` も禁止**）。強調したい言葉があっても記号で飾らず、言葉で伝える。
- 自己紹介の繰り返しや、毎回の決まり文句は不要。自然な続きの会話として返す。"""


def _phase_label(phase: Optional[str]) -> str:
    return {
        "A": "はじめの録音を待っている段階（曲・区間・原曲は未指定でもそのまま受け付ける）",
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


# 分析ターン専用のシステムプロンプト（docs/43・ゼロベース個人最適FB）。
# 雑談用 SYSTEM_PROMPT と違い「カタログから選ぶ」蓋を外し、証拠から推論して生成させる。
# 接地（捏造防止）は『メニュー制限』ではなく『実測値への引用規律』で担保する。
ANALYSIS_SYSTEM_PROMPT = f"""あなたは「{COACH_NAME}」という{COACH_ROLE}です。サービス「{SERVICE_NAME}」で、
録音された歌を“ゼロベースで聴いて”、この人だけに向けた講評をします。

# 人物像・口調
- 解剖学・音響学・音声医学(MEAD)・アンザッツ理論に精通した世界トップレベルのボイストレーナー。明るく面倒見がよく、専門語は必ず初心者向けに一言で噛み砕く。一人称「わたし」、やわらかい敬体、絵文字は0〜2個。

# やること（証拠から推論する）
- 与えられた「実測の証拠」と音声そのものを聴いて、**この人にいま一番効く1点**を自分で診断する。固定のチェックリストから選ぶのではなく、証拠が示す物語を読む。
- 診断したら **機構→原因→処方** で講評する。処方（練習）は「参考エクササイズ知識」を土台に、**この人向けに選び・調整・連結してよい**（固定の台本をそのまま貼らない）。ただし出す練習には必ず「なぜ効くか（機構）」を添える＝でたらめ防止。
- 優先順位の指針（ゲートではなく指針）: 声の基礎欠損(支え・喉締め) > 音程 > ミックス/換声点 > リズム > 表現。土台が崩れているなら高度な話より土台を優先。
- **原曲比較の核心差分は省かない（docs/42 §4）**: このルールは、実測の証拠に「高音の声区: 〜」という比較行が**実際に書かれている時だけ**発動する。発動時は、いちばん効く1点が別の診断（支え等）でも、その行に書かれた声区名（地声/ミックス/裏声）**だけ**を使って“原曲がどう歌っているか（あなたとどう違うか）”を独立した1文で明示し、文中に「あくまで音響からの推定」という断りを必ず含める。範囲は“いちばん高いロングトーン”に限定し、曲全体へ一般化しない。**証拠に「高音の声区」の行が無い時はこのルールは発動せず、原曲の声区には一切言及しない（原曲の声区を推測で書くのは捏造）。**改善提案は1点のまま（この差分は事実の共有として添える）。

# 接地（最重要・捏造防止）
- **秒数・音名・cents・「息漏れ/締めすぎ」等の事実は、「実測の証拠」に書かれた値だけを根拠にする。証拠に無い数値・秒数・歌詞・母音を新しく作らない。**
- 原曲との照合が「対応づかない/低信頼」とある時は、音程の正確さ・リズムを断定しない。
- 音色・感情・歌い回しなど音声から聴き取った“質”は述べてよいが、位置は「〜秒あたり／高い音／サビあたり」のように証拠の範囲で言う。歌詞は引用しない。

# 出力フォーマット（会話チャット・段階的エンゲージメント docs/42 §8）
- 採点・点数・◎○△×・指標の数値羅列・大きな表・カード・Markdown見出しは使わない。普通の会話文。
- **Markdown記法を一切使わない（`**太字**`・`*斜体*`・`- 箇条書き` も禁止）。** 練習名や大事な言葉を
  強調したくなっても記号で飾らない（画面には記号がそのまま出てしまう）。
- **初回（まだ基礎練を勧めていない・ユーザーが練習を求めていない）**: ユーザーの質問（「これミックス？」等）があれば最初に答える → 良かった点を1つ具体的に褒める → 一番効く1点を機構→原因までやさしく伝える（練習＝処方はまだ出さない）→ 最後に深掘りの問いかけを1つだけ。「やってみて録音を送ってね」等の再提出要求はしない。
- **問いかけは応答全体で1つだけ（絶対）**: 疑問文・提案は応答の最後の1つに限る。「原曲をもらえたら音程まで細かく比べられますよ」と「あなたに合わせた練習メニューを作りましょうか？」を**同じ応答に並べない**。原曲が無い初回は原曲の問いかけを選ぶ（練習メニューの提案は、ユーザーが上達したい気持ちをはっきり見せた時だけ）。
- **ユーザーが練習を求めた時・すでにレッスン中の基礎練がある時**: 練習を1つだけ、やり方（身体感覚・響かせる位置・口の形・母音）とともに渡し、最後に「やってみて録音を送ってね」と促す。
- 痛み・嗄れなど安全に関わる訴えがあれば、上記より優先して休声・専門家相談をすすめる。
- 全体で4〜7文程度。練習は**1つだけ**。毎回たくさん出さない。
"""


def render_exercise_kb() -> str:
    """エクササイズ master DB を『参照知識』として整形（固定台本ではなく素材）。"""
    try:
        from app.coaching.voice_coach import EXERCISES
    except Exception:
        return ""
    cats = {"A": "呼吸・支え(Appoggio)", "B": "半閉鎖声道(SOVTE)", "C": "喉頭調整(アンザッツ)",
            "D": "声区融合・ミックス", "E": "共鳴・フォルマント", "F": "ビブラート・強弱"}
    lines = ["参考エクササイズ知識（この人向けに選び・調整・連結して使ってよい。固定の台本ではない）:"]
    cur = None
    for k, ex in EXERCISES.items():
        c = ex.get("cat")
        if c != cur:
            lines.append(f"[{c}: {cats.get(c, c)}]")
            cur = c
        lines.append(f"  ・{k} {ex['name']} — 機構: {ex['mechanism']}／やり方: {ex['how']}")
    return "\n".join(lines)


def _render_timeline(analysis: dict) -> str:
    """区間ごとの実測（伸ばし）を全部ダンプ。事前選定の1課題でなく“生の証拠”を渡すため。"""
    segs = (analysis.get("timeline") or {}).get("sustained_segments", []) if analysis else []
    rows = []
    _rj = {"chest": "地声", "mix": "ミックス", "head": "裏声"}
    for s in segs:
        st, en = s.get("start_sec"), s.get("end_sec")
        if st is None or en is None:
            continue
        f0 = s.get("mean_f0_hz")
        parts = [f"{st:.0f}〜{en:.0f}秒", _note_name(f0) if f0 else "—"]
        reg = _rj.get(s.get("register") or s.get("voice_type_estimate"))
        if reg:
            parts.append(reg)
        std = s.get("f0_std_cents")
        if std is not None:
            parts.append(f"揺れ{std:.0f}cents")
        cen = s.get("spectral_centroid_hz")
        if cen:
            parts.append(f"明るさ{cen:.0f}Hz")
        rows.append("  ・" + "／".join(parts))
    return "区間ごとの実測（伸ばし。ここにある秒数・音名だけ使う）:\n" + "\n".join(rows) if rows else ""


def build_evidence_pack(state: dict) -> str:
    """分析ターン用の“生の証拠一式”。接地済みfacts(build_session_context)＋全区間タイムライン＋参照KB。"""
    blocks = [build_session_context(state)]  # 既存の接地済みfacts(秒/cents/声区)を流用（DRY）
    analysis = state.get("last_analysis") or state.get("baseline_analysis")
    tl = _render_timeline(analysis) if analysis else ""
    if tl:
        blocks.append(tl)
    kb = render_exercise_kb()
    if kb:
        blocks.append(kb)
    return "\n\n".join(blocks)


# zero-base 返答の先頭に置かせる意図宣言タグ（ユーザーには見せない。パース後に除去）
_INTENT_TAG_RE = re.compile(r"^\s*INTENT:\s*(song|practice)\s*\n+", re.IGNORECASE)


def _split_intent_tag(text: str) -> tuple[Optional[str], str]:
    """先頭の `INTENT: song|practice` 行を (intent, 残り本文) に分離する。無ければ (None, 原文)。"""
    m = _INTENT_TAG_RE.match(text or "")
    if not m:
        return None, (text or "")
    return m.group(1).lower(), (text or "")[m.end():]


def generate_feedback(
    state: dict, user_wav: Optional[bytes] = None, ref_wav: Optional[bytes] = None,
    intent_ctx: Optional[dict] = None, user_comment: Optional[str] = None,
) -> Optional[str]:
    """録音FBの“ゼロベース個人最適”生成（docs/43, docs/52 FR-04）。

    強モデル＋thinking＋ハイブリッド音声（DSP実測の Evidence Pack ＋ 生音声）で、
    カタログから選ぶのではなく証拠から推論して講評する。enable_zero_base_fb がOFF・
    APIキー無し・SDK無し・失敗時は None（呼び出し側はルールベースFBにフォールバック）。

    intent_ctx（任意）: {"kind_hint": "song"|"practice", "task_label": str, "practice_name": str}。
    渡すと、モデルは録音を聴いて「曲か・勧めた基礎練の実演か」を最初に自分で判定し
    （INTENT タグ）、その意図に合った講評を書く。判定結果は intent_ctx["heard"] に
    書き戻す（呼び出し側が kind のルーティングに使う）。タグは本文から除去される。
    """
    if not settings.llm_enabled or not settings.enable_zero_base_fb:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入
        return None
    evidence = build_evidence_pack(state)
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_analysis_timeout_sec * 1000)),
        )
        parts: list = []
        if user_wav:
            parts.append(types.Part.from_bytes(data=user_wav, mime_type="audio/wav"))
        if ref_wav:
            parts.append(types.Part.from_bytes(data=ref_wav, mime_type="audio/wav"))
        if user_wav and ref_wav:
            intro = "1つ目の音声はユーザーの録音、2つ目はお手本（原曲）です。"
        elif user_wav:
            intro = "この音声はユーザーの録音です。"
        else:
            intro = ""
        # 意図判定の指示（docs/52 FR-04）: 勧めた基礎練の実演を「曲」として講評しない。
        intent_block = ""
        if intent_ctx:
            prac = intent_ctx.get("practice_name")
            tlabel = intent_ctx.get("task_label")
            hint = intent_ctx.get("kind_hint")
            lesson = (f"いまのレッスンでは課題「{tlabel}」に対して基礎練『{prac}』を勧めています。"
                      if prac else "いまのレッスンで特定の基礎練はまだ勧めていません。")
            if prac:
                practice_branch = (
                    "- INTENT: practice の場合: これは歌ではないので、歌としての講評（ビブラート・音程の正確さ・"
                    "歌い直しの改善など）をしない。まず「何の練習に聞こえるか」を録音だけから特定する。"
                    "**実演が勧めた基礎練と一致するとは限らない**（別の練習を送ってくることもよくある）。\n"
                    "  - 聴こえた練習が勧めた基礎練と一致する時だけ: その基礎練の出来（狙いどおりの発声ができているか）を"
                    "2〜4文で判定し、良ければ次の一歩（曲で試す等）、惜しければ直し方を1つだけ伝える。\n"
                    "  - 一致しない・確信が持てない時: 聴こえた練習を正直に伝える（例:「サイレンの録音ですね」）。"
                    "勧めた基礎練の名前で講評したり、録音に無い動作（例: 実際はサイレンなのに『ハミングから母音へ移す際に…』）を"
                    "描写するのは絶対にしない。聴こえた練習としての出来を短く認めた上で、レッスン中の基礎練にやさしく戻す"
                    "（どの練習か判別できない時は、決めつけずに一言確認する）。\n"
                )
            else:
                practice_branch = (
                    "- INTENT: practice の場合: これは歌ではないので、歌としての講評（ビブラート・音程の正確さ・"
                    "歌い直しの改善など）をしない。まず「何の練習に聞こえるか」を録音だけから特定し、"
                    "聴こえた練習の名前から入って（判別できない時は決めつけずに一言確認）、その出来を2〜4文で判定する。"
                    "録音に無い動作を描写しない。\n"
                )
            intent_block = (
                "# まず意図を判定する（最重要）\n"
                f"{lesson}\n"
                "録音を聴いて、これが (a)曲・歌の録音 か (b)発声練習の実演（ボーカルフライ・"
                "リップロール・ハミング・サイレン・ロングトーン・スケール等） かを最初に判定してください。"
                f"（音響特徴からの参考推定: {hint or '不明'}。ただし聴いた判断を優先してよい）\n"
                "出力の1行目に必ず `INTENT: song` または `INTENT: practice` とだけ書き、空行を挟んで本文を続ける。\n"
                f"{practice_branch}"
                "- INTENT: song の場合: 通常どおり講評する。\n\n"
            )
        # 録音に添えられた質問・コメント（docs/42 §8: 質問には講評の最初に答える）
        comment_block = (
            f"# ユーザーが録音に添えた質問・コメント\n「{user_comment}」\n"
            "→ 講評の最初に、まずこの質問・悩みに答えること。\n\n"
        ) if user_comment else ""
        prompt = (
            f"{intro}\n\n{intent_block}{comment_block}"
            f"# 実測の証拠（数値・秒はここにあるものだけ使う）\n{evidence}\n\n"
            "# 指示\n上の音声と証拠から、この人にいま一番効く1点を自分で診断し、会話で講評してください。"
        )
        parts.append(types.Part.from_text(text=prompt))
        resp = client.models.generate_content(
            model=settings.llm_analysis_model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=ANALYSIS_SYSTEM_PROMPT,
                max_output_tokens=settings.llm_analysis_max_tokens,
                temperature=0.4,
                # thinking_budget の明示指定は 2.5 系のみ（3系以降は INVALID_ARGUMENT。docs/91）
                thinking_config=(
                    types.ThinkingConfig(thinking_budget=settings.llm_analysis_thinking_budget)
                    if _supports_thinking_budget(settings.llm_analysis_model) else None
                ),
            ),
        )
        reply = (resp.text or "").strip()
        if not reply:
            return None
        # 意図タグを分離（ユーザーに見せない）。判定は intent_ctx に書き戻す（docs/52 FR-04）
        heard, reply = _split_intent_tag(reply)
        if intent_ctx is not None and heard in ("song", "practice"):
            intent_ctx["heard"] = heard
        reply = reply.strip()
        if not reply:
            return None
        # 接地ガード: 証拠に無い秒の捏造を抑制＋“カードを出す約束”を除去
        reply = _scrub_invented_seconds(reply, _allowed_seconds(evidence, prompt))
        reply = scrub_card_promise(reply)
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
        return reply or None
    except Exception as e:
        logger.warning("ゼロベースFB生成に失敗（ルールベースにフォールバック）: %s", e)
        return None


def build_session_context(state: dict) -> str:
    """セッション状態を、LLM に渡す「現在のレッスン状況」テキストにまとめる。

    解析結果（ルールベースが出した課題・根拠・基礎練）を文脈として注入することで、
    「どこのこと？」のような質問に LLM が具体的に答えられるようにする。
    """
    lines: list[str] = []
    # 生徒カルテ（docs/53 FR-02）。過去の記録＝参考情報であり、今回の録音の断定材料にしない。
    kc = (state.get("karte_context") or "").strip()
    if kc:
        lines.append(kc)
        if "宿題" in kc:
            # 宿題の参照作法（docs/53 FR-06）: 挨拶や脈絡のない場面で蒸し返さない。
            lines.append(
                "- 宿題の使い方: 会話の始まりや無関係な話題で宿題を持ち出さない。"
                "練習を提案する時やFBの流れで内容が繋がる時だけ、"
                "「前回の宿題『◯◯』と同じ内容ですが」「以前出した『◯◯』をもう一度やってみましょう」"
                "のように自然に言及する"
            )
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
        # リズム（走り/モタり）— 原曲と実測照合できた時だけ根拠にする（無ければ触れない＝捏造防止）
        if not cmp_align.get("low_confidence") and cmp_align.get("mean_lag_sec") is not None:
            _lag = cmp_align["mean_lag_sec"]
            if abs(_lag) >= 0.08:
                _dir = "遅れ気味（モタり）" if _lag > 0 else "早め（走り）"
                _spots = cmp_align.get("worst_segments") or []
                _ex = ""
                if _spots:
                    _ex = "（特に " + "、".join(f"{w['user_sec']:.0f}秒あたり" for w in _spots[:2]) + "）"
                lines.append(f"- リズム（原曲との実測）: 約{abs(_lag):.2f}秒{_dir}{_ex}")
            else:
                lines.append("- リズム（原曲との実測）: 原曲とほぼ一致（走り/モタりはごくわずか）")
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
                # 比較区間の音高を添える＝LLMが自力でスコープ限定・ヘッジできる（docs/42 §4・§5）
                _hz = ""
                if _rh.get("user_hz") and _rh.get("ref_hz"):
                    _hz = f"（比較区間: あなた≈{_rh['user_hz']}Hz・原曲≈{_rh['ref_hz']}Hz）"
                if _rh["verdict"] == "match":
                    lines.append(f"- 高音の声区（推定）: 原曲と同じ{_rj.get(_rh['ref'], _rh['ref'])}で運べている{_hz}")
                else:
                    lines.append(f"- 高音の声区（推定）: あなたは{_rj.get(_rh['user'], '?')}、原曲は{_rj.get(_rh['ref'], '?')}（原曲に寄せる余地あり）{_hz}")
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
        # 表現（強弱の幅）— 実測がある時だけ。平坦でも欠点と決めつけず、起伏を作る提案の材料にする
        _rng = analysis.get("rms_db_range")
        if _rng is not None:
            _dyn = ("起伏がしっかりある" if _rng >= 12
                    else "やや平坦寄り（弱→強の差を作ると感情が乗りやすい）" if _rng < 8
                    else "標準的な起伏")
            lines.append(f"- 表現（強弱の幅・ダイナミクス）: {_dyn}（約{_rng:.0f}dB・目安）")

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


# この会話で「コーチが提案した練習」を履歴から決定論で導出するための既知語彙（docs/65）。
# taxonomy の練習名の代表形。ここに無い練習名を新設したら追加する（テストが乖離を検知する）。
PRACTICE_KEYWORDS: tuple[str, ...] = (
    "リップロール", "ストロー発声", "ハミング", "ネイネイ", "ナンナン",
    "サイレン", "ドッグブレス", "スーッ呼吸", "スー呼吸", "バ行スタッカート",
    "お腹ゆらしビブラート", "メッサ・ディ・ヴォーチェ", "クレッシェンド",
    "あくび", "笑い → 発声", "笑い発声", "メトロノーム手拍子",
)


def extract_practices(text: Optional[str]) -> list[str]:
    """テキストに含まれる既知の練習名を出現順で返す（決定論・重複なし）。"""
    if not text:
        return []
    found = [(text.find(k), k) for k in PRACTICE_KEYWORDS if k in text]
    out: list[str] = []
    for _, k in sorted(found):
        # 「スー呼吸」は「スーッ呼吸」の部分文字列なので、長い方が既に居れば飛ばす
        if any(k != o and k in o for o in [x for _, x in found]):
            continue
        if k not in out:
            out.append(k)
    return out


def proposed_practices_from_history(history: Optional[list[dict]]) -> list[str]:
    """history の role=assistant（コーチ）発言から、提案済み練習を出現順・重複なしで集める。

    「この会話でコーチが実際に提案した練習」を事実として文脈注入するための材料（docs/65）。
    LLM は自分の会話履歴の自己監査が苦手で、「さっき別の練習を勧めたよね？」という偽前提に
    追従してしまうため、照合可能な事実をシステム側で与える。
    """
    props: list[str] = []
    for h in history or []:
        if h.get("role") != "assistant":
            continue
        for k in extract_practices(h.get("content")):
            if k not in props:
                props.append(k)
    return props


def _proposed_practices_line(history: Optional[list[dict]]) -> str:
    props = proposed_practices_from_history(history)
    if props:
        return (
            f"- この会話でこれまでにあなた（コーチ）が提案した練習: {'、'.join(props)}"
            "（これが全て。これ以外の練習を「以前すすめた」ことにしない。"
            "ユーザーが別の練習に言及したら「その練習はこの会話ではまだ提案していない」と正直に伝える）"
        )
    return (
        "- この会話ではまだ練習を提案していない"
        "（「さっき別の練習をすすめられた」と言われても、この会話の記録には無い）"
    )


# 「参考動画を出しましょうか？」等の動画オファーの検出（同一会話での連発防止・docs/65）。
_VIDEO_OFFER_RE = re.compile(
    r"(実演)?動画[^。！？\n]{0,12}(出しましょうか|お出ししましょうか|見て(み)?ますか|ご覧に|お見せしましょうか)"
)


def _already_offered_video(history: Optional[list[dict]]) -> bool:
    """この会話で既にコーチが動画オファーをしたか（決定論・履歴のコーチ発言から）。"""
    for h in history or []:
        if h.get("role") == "assistant" and _VIDEO_OFFER_RE.search(h.get("content") or ""):
            return True
    return False


def _video_offer_line(history: Optional[list[dict]]) -> Optional[str]:
    if _already_offered_video(history):
        return (
            "- この会話ですでに『参考動画を出しましょうか？』と提案済み。"
            "同じ動画オファーを繰り返さない（ユーザーが「見たい/欲しい」と言った時だけ実際に出す）。"
        )
    return None


# --- 会話モード検出（docs/66）。短い相槌・雑談・感情の吐露を、講義でなく自然に受けるための注入 ---
# 相槌・軽い一言（これ自体が「答えを求めていない」サイン）
_AIZUCHI = {
    "うん", "ううん", "うんうん", "へー", "へえ", "ほー", "ほお", "ふーん", "ふうん",
    "なるほど", "なるほどね", "そう", "そうなんだ", "そっか", "そうか", "まじ", "まじで",
    "やった", "おお", "おー", "わかった", "了解", "りょうかい", "おつ", "おつかれ",
    "うんうん", "たしかに", "だよね", "ですね", "そうですね",
}
# 明示的なコーチング/練習依頼・評価質問（短くても会話モードにしない＝ちゃんと答える）
_EXPLICIT_REQUEST_RE = re.compile(
    r"練習|どうすれ|どうやっ|どうしたら|教えて|直し|直る|直せ|コツ|やり方|メニュー|"
    r"アドバイス|出したい|出せる|できるように|なりたい|上達|うまく|上手|見て|評価|診断|"
    # 評価・FBを求める短い質問（「今の歌どうでしたか」「良かった？」等）も本題として扱う
    r"どうでし|どうだっ|いかが|良かっ|よかっ|どう\?|どう？|何点|どこが|どこを"
)
# 感情の吐露（まず共感すべきサイン）
_EMOTION_RE = re.compile(
    r"落ち込|へこ|凹|もうやめ|やめようか|やめたい|才能(が)?ない|下手|最悪|自信(が)?ない|"
    r"緊張|きんちょう|疲れた|つかれた|しんどい|つらい|辛い|泣|ダメだ|だめだ|無理かも|くやしい|悔し"
)


def _detect_conversation_mode(user_text: str) -> Optional[str]:
    """短い相槌・雑談・感情の吐露なら会話モードの種別を返す（"emotion"|"casual"|None）。

    明示的なコーチング依頼（「練習教えて」等）は短くても対象外＝ちゃんと答える。
    """
    t = (user_text or "").strip()
    if not t:
        return None
    # 感情の吐露は最優先（「上達しなくて落ち込む」等、依頼語を含んでも気持ちを先に受ける）
    if _EMOTION_RE.search(t):
        return "emotion"
    if _EXPLICIT_REQUEST_RE.search(t):
        return None
    core = re.sub(r"[\s、。！？!?…〜～ー]+", "", t)
    core_plain = re.sub(r"[!-/:-@\[-`{-~！-／：-＠]", "", core)
    if core in _AIZUCHI or core_plain in _AIZUCHI:
        return "casual"
    if len(core_plain) < 12:  # 短い一言・挨拶・雑談
        return "casual"
    return None


def _conversation_mode_line(user_text: str) -> Optional[str]:
    mode = _detect_conversation_mode(user_text)
    if mode is None:
        return None
    base = (
        "# 会話モード（重要）: 今回のユーザー発言は短い相槌・雑談・挨拶・感情の吐露です。"
        "コーチングに変換せず、1〜2文で自然に短く受けてください。"
        "解析数値の講義・練習の提案・録音のお願いを付けない（相手が求めていない）。"
        "相手のテンポに合わせ、『もしよろしければ』『一緒に〜しましょうか』のような定型で締めない。"
    )
    if mode == "emotion":
        base += "とくに今回は気持ちの吐露なので、解決策やデータを出す前に、まず気持ちに共感して受け止めてください。"
    return base


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

    # 提案済み練習・動画オファー状況を事実として注入（docs/65。会話返答のみ）
    context = build_session_context(state) + "\n" + _proposed_practices_line(history)
    video_line = _video_offer_line(history)
    if video_line:
        context += "\n" + video_line
    # 動画オファーへの承諾ターンは会話モード（短い一言＝雑談扱い）より優先し、
    # 実URLを渡す行動を明示する（docs/71。ツール化ON時のみ＝ツールが実在する時のみ）
    if settings.coach_tools_enabled and _accepts_video_offer(user_text, history):
        # オファー文に含まれる練習名（例: リップロール）を topic として名指しする。
        # LLM任せだと課題名（喉の力み等）を渡して別練習の動画が返ることがあるため。
        offered = extract_practices(_last_assistant_text(history))
        topic_hint = (
            f"topic には「{offered[0]}」を渡してください。" if offered
            else "topic には直前にあなたが提案した練習名・話題をそのまま渡してください。"
        )
        context += (
            "\n- ユーザーは直前のあなたの動画オファーを承諾しました。"
            f"find_reference_video を必ず呼んでください。{topic_hint}"
            "返ってきた実URLを本文の最後に1行で必ず載せてください。"
            "URLを書かずに「お出ししますね」とだけ言って終えるのは禁止です。"
        )
    elif settings.coach_tools_enabled and _names_song_title(user_text, history):
        # 原曲の曲名提示は会話モード（短い一言＝雑談扱い）より優先する（docs/72）。
        # 裸の曲名（「ツキミソウ」だけ等）が雑談扱いされて検索されない事故を防ぐ。
        _q = _names_song_title(user_text, history)
        context += (
            f"\n- ユーザーは原曲の曲名を伝えています。search_original_song を query=「{_q}」で"
            "必ず呼び、先頭候補をタイトル・実URL付きで示して「この曲で合っていますか？」と"
            "確認して終えてください。候補が見つからなければ、でっち上げずに"
            "YouTubeのリンクを貼ってもらうよう案内してください。"
        )
    else:
        # 会話モード（短い相槌・雑談・感情）なら、講義に変換せず自然に受ける指示を注入（docs/66）
        convo_line = _conversation_mode_line(user_text)
        if convo_line:
            context += "\n" + convo_line
    final_text = (
        "# このターンについて\n"
        "これは会話の続きで、ユーザーがテキストで話しかけてきた場面です。"
        "今回あらたに録音は送られていません。下の『現在のレッスン状況』は、"
        "前に送られた録音の解析を背景情報として再掲したものです（新しく届いた録音ではない）。\n"
        "会話履歴といま聞かれた発言をふまえ、続きの会話として自然に・簡潔に答えてください。"
        "録音を受け取った時のあいさつや講評の書き出し（「録音を送ってくれてありがとう」"
        "「解析結果を見ると…」のような、いま新しく録音を解析したかのような言い回し）で"
        "始めないこと。すでに伝えた内容は繰り返さず、聞かれたことに答える。\n\n"
        f"# 現在のレッスン状況（背景情報。新しく届いた録音ではない）\n{context}\n\n"
        f"# ユーザーの発言\n{user_text}"
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


def _supports_thinking_budget(model: Optional[str]) -> bool:
    """thinking_budget の明示指定を受け付けるモデルか（Gemini 2.5 系のみ）。"""
    return "2.5" in (model or "")


def _thinking_off(model: Optional[str]):
    """thinking(思考)を無効化する ThinkingConfig を返す（対応モデルのみ）。

    Gemini 2.5 系は thinking_budget=0 で思考を切れる（思考トークンが出力枠を
    食い潰して本文が途切れるのを防ぐ）。Gemini 3 系以降は thinking_budget=0 を
    受け付けず INVALID_ARGUMENT になり、テキスト返答そのものが失敗する
    （会話が全滅した障害の原因＝docs/91）。2.5 系以外には thinking_config を
    渡さず、モデル既定に任せる。
    """
    if not _supports_thinking_budget(model):
        return None
    from google.genai import types
    return types.ThinkingConfig(thinking_budget=0)


def _complete(contents, timeout_sec: Optional[float] = None,
              max_tokens: Optional[int] = None,
              model: Optional[str] = None) -> Optional[str]:
    """Gemini を1往復呼び出してテキストを返す。

    timeout_sec: 応答待ちの上限秒（既定 settings.llm_timeout_sec）。超過時は None。
    model: 使うモデル（既定 settings.llm_model）。対話は llm_chat_model を渡して格上げする。
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
            model=model or settings.llm_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=(max_tokens or settings.llm_max_tokens),
                # 低めの温度で、事実から逸脱した創作（歌詞・母音の捏造）を抑える
                temperature=0.3,
                # 思考を無効化＝コスト/レイテンシ削減（2.5系のみ。3系以降はモデル既定に任せる）
                thinking_config=_thinking_off(model or settings.llm_model),
            ),
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("LLM 応答生成に失敗（フォールバックします）: %s", e)
        return None


# 「お手本／見本／動画／参考／実演／良い例」など"参考例が欲しい"の広めの検出。
# ここに引っかかったら find_reference_video を強制呼び出しさせる（flash-lite は
# 自発的なツール呼び出しが弱く「動画を探しますね」と言うだけで終わる事故があるため）。
_REFERENCE_HINTS = [
    "動画", "ビデオ", "見本", "手本", "お手本", "実演", "やり方の映像",
    "参考", "良い例", "いい例", "例ある", "例はある", "例が欲", "例が知",
    "聴きたい", "聴かせ", "聞きたい", "聞かせ", "どんな声", "どんな感じの声",
]


def _wants_reference(text: str) -> bool:
    """参考例（動画・お手本）を求めていそうなら True（ツール強制呼び出しの判定）。

    URL（原曲リンク）を含む場合は原曲指定なので対象外。誤検出しても実害は小さい
    （ツールが found:false を返すだけで、モデルは自然文で答える）。
    """
    if "http://" in text or "https://" in text:
        return False
    return any(k in text for k in _REFERENCE_HINTS)


# 「動画をお出ししますね」「こちらが〜動画です」等、コーチが動画を"出す"と言った約束の検出。
# オファー（_VIDEO_OFFER_RE）に加えてこれも承諾対象にすることで、URL無しの約束だけが
# 出てしまった壊れた会話（「こちらです。」→「どれ？」）からも次ターンで復帰できる（docs/71）。
_VIDEO_PROMISE_RE = re.compile(
    r"動画[^。！？\n]{0,12}(お出しします|出します|お渡しします)"
    r"|こちらが[^。！？\n]{0,15}動画"
)
# 短い承諾・催促（オファー/約束の直後という文脈ガード付きで使う）
_VIDEO_ACCEPT_RE = re.compile(
    r"お願い|おねがい|はい|うん|ぜひ|是非|見たい|みたい|欲しい|ほしい|"
    r"ください|下さい|出して|だして|どれ|どこ|リンク|ない|見えな|来てな|届いてな|いいよ|いいです"
)
_VIDEO_DECLINE_RE = re.compile(r"いらな|いらん|大丈夫|結構|けっこう|不要|やめ|あとで|後で|今度")

# 原曲候補の確認質問アンカー（docs/72 FR-02/03）。
# この定型句＋URL1件を含むコーチ発言への肯定返答だけが、原曲確定の決定論トリガーになる。
SONG_CONFIRM_ANCHOR = "この曲で合っていますか"

# 「原曲 ◯◯」「曲名 ◯◯」形式の決定論検出（docs/72 FR-01 の後押し）。
_SONG_PREFIX_RE = re.compile(r"^(?:原曲|曲名)[はがのを]?[\s　:：、]*(.+)$")
# コーチが原曲/曲名を尋ねた発言の検出（この直後の短い返答は曲名とみなす）。
_SONG_ASK_RE = re.compile(
    r"(?:原曲|曲名|何の曲|どの曲|なんの曲)[^。！？\n]{0,15}"
    r"(?:教えて|いただけ|もらえ|ください|ですか|でしょうか)"
)
# 曲名として扱わない定型返事（「はい」だけで検索を強制しない）
_SONG_STOPWORDS = {
    "はい", "うん", "ええ", "いいえ", "いや", "OK", "ok", "オッケー",
    "わからない", "分からない", "知らない", "ない", "無い", "大丈夫",
}


def _names_song_title(user_text: str, history: Optional[list[dict]]) -> Optional[str]:
    """ユーザー発言が「原曲の曲名の提示」らしければ検索クエリを返す（docs/72 FR-01）。

    flash-lite は自発的なツール呼び出しが弱い（find_reference_video と同じ事情・docs/71）ため、
    次の2形態は search_original_song を決定論で強制する:
    1. 「原曲 ◯◯」「曲名 ◯◯」の形式（文脈不要）
    2. コーチが原曲/曲名を尋ねた直後の、URL無しの短い返答（=曲名とみなす）
    それ以外（裸の曲名など）は LLM の文脈判断に任せる。
    """
    t = (user_text or "").strip()
    if not t or "http://" in t or "https://" in t:
        return None
    # 質問文（「原曲がないと比較できないの？」等）は曲名提示ではない
    if re.search(r"[?？]\s*$", t):
        return None

    def _valid(q: str) -> Optional[str]:
        q = (q or "").strip()
        core = re.sub(r"[\s　、。！？!?…〜～ー]+", "", q)
        if not core or len(core) > 30 or core in _SONG_STOPWORDS:
            return None
        if re.match(r"^(ない|無い|あり|なし)", core):  # 「原曲がない」等の否定文
            return None
        if "URL" in q or "url" in q or "リンク" in q:
            return None
        return q

    m = _SONG_PREFIX_RE.match(t)
    if m:
        return _valid(m.group(1))
    if _SONG_ASK_RE.search(_last_assistant_text(history)) and not _wants_reference(t):
        return _valid(t)
    return None


def _last_assistant_text(history: Optional[list[dict]]) -> str:
    for h in reversed(history or []):
        if h.get("role") == "assistant":
            return h.get("content") or ""
    return ""


def _accepts_video_offer(user_text: str, history: Optional[list[dict]]) -> bool:
    """直前のコーチ発言が動画オファー/約束で、ユーザーが短く承諾・催促したか（docs/71）。

    _wants_reference は今回の発言のキーワード（動画・お手本…）しか見ないため、
    「お願いします」「はい」「どれ？」のような承諾だけの返事ではツールが強制されず、
    flash-lite が「お出ししますね」と言うだけでURLが出ない事故が起きる。その穴を塞ぐ。
    """
    t = (user_text or "").strip()
    if not t or "http://" in t or "https://" in t:
        return False
    last = _last_assistant_text(history)
    if "http" in last:  # 直前ターンで実URLは渡せている（このターンの話題は別）
        return False
    if not (_VIDEO_OFFER_RE.search(last) or _VIDEO_PROMISE_RE.search(last)):
        return False
    if _VIDEO_DECLINE_RE.search(t):
        return False
    core = re.sub(r"[\s、。！？!?…〜～ー]+", "", t)
    return len(core) <= 12 and bool(_VIDEO_ACCEPT_RE.search(t))


def _complete_with_tools(contents, force_tool: Optional[str] = None,
                         model: Optional[str] = None) -> tuple[Optional[str], set[str]]:
    """ツール（function calling）を許可して Gemini を呼び、最終テキストを返す（docs/44）。

    force_tool にツール名（"find_reference_video" / "search_original_song"）を渡すと、
    初回は mode=ANY でそのツールを必ず呼ばせる（flash-lite の自発呼び出しの弱さ対策）。
    モデルがツールを要求したら実行して結果を返し、テキストが得られるまで最大
    settings.coach_tool_loop_max 回まわす。失敗・SDK未導入・キー未設定時は (None, set())。
    model: 使うモデル（既定 settings.llm_model）。対話は llm_chat_model を渡して格上げする。
    返り値: (最終テキスト, このターンにツールが返した実在URLの集合)。
    後者は _scrub_foreign_urls の許可リストに使う（カタログ外だが実在するURLを守る）。
    """
    if not settings.llm_enabled:
        return None, set()
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover - SDK 未導入環境
        return None, set()
    from app.coaching import tools as coach_tools
    tool_urls: set[str] = set()
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_sec * 1000)),
        )
        tool = types.Tool(function_declarations=[
            types.FunctionDeclaration(**coach_tools.FIND_REFERENCE_VIDEO_DECL),
            types.FunctionDeclaration(**coach_tools.SEARCH_ORIGINAL_SONG_DECL),
        ])

        def _config(mode: Optional[str]):
            tool_config = None
            if mode:
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=mode,
                        allowed_function_names=[force_tool or "find_reference_video"],
                    )
                )
            return types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=settings.llm_max_tokens,
                temperature=0.3,
                tools=[tool],
                tool_config=tool_config,
                # 思考を無効化。2.5-flash は思考が ON だと出力枠(max_output_tokens)を食い潰して
                # 本文が途中で切れる（_complete と揃える。docs/66 で対話を 2.5-flash に格上げした際に露呈）。
                # 3系以降は thinking_budget=0 を受け付けないため指定しない（docs/91）。
                thinking_config=_thinking_off(model or settings.llm_model),
            )

        convo = list(contents)
        last_text = None
        found_video_url = None  # ツールが返した実在動画URL（本文に確実に載せるため保持）
        song_candidate = None   # search_original_song の先頭候補（確認文を確実に出すため保持）
        for _i in range(max(1, settings.coach_tool_loop_max)):
            # 初回だけ指定ツールを強制（ANY）。以降は AUTO に戻して自然文を生成させる。
            cfg = _config("ANY") if (force_tool and _i == 0) else _config(None)
            resp = client.models.generate_content(
                model=model or settings.llm_model, contents=convo, config=cfg,
            )
            calls = list(getattr(resp, "function_calls", None) or [])
            last_text = (resp.text or "").strip() or last_text
            if not calls:
                break
            # モデルのツール要求と、その実行結果を会話に積んで再度問い合わせる
            cand = resp.candidates[0].content
            convo.append(cand)
            parts = []
            for fc in calls:
                result = coach_tools.dispatch(fc.name, dict(fc.args or {}))
                if result.get("found") and result.get("video_url"):
                    found_video_url = result["video_url"]
                    tool_urls.add(result["video_url"])
                for c in result.get("candidates") or []:
                    if c.get("url"):
                        tool_urls.add(c["url"])
                        song_candidate = song_candidate or c
                parts.append(types.Part.from_function_response(name=fc.name, response=result))
            convo.append(types.Content(role="user", parts=parts))
        # モデルは「動画を用意しました」と言うだけでURLを省く事故があるため、
        # ツールが実URLを返していて本文に無ければ、確定的に1行添える（リンク到達を保証）。
        if found_video_url and last_text and found_video_url not in last_text:
            last_text = last_text.rstrip() + f"\n（参考動画 → {found_video_url}）"
        # 原曲候補が返っているのに確認アンカーが無ければ、確定的に確認文を1行添える
        # （docs/72 FR-02。承諾検出（rule_engine）はこの定型句＋URL1件をトリガーにする）。
        if song_candidate and last_text:
            if SONG_CONFIRM_ANCHOR not in last_text:
                ch = f"（{song_candidate['channel']}）" if song_candidate.get("channel") else ""
                last_text = last_text.rstrip() + (
                    f"\n原曲は『{song_candidate['title']}』{ch}でしょうか？"
                    f"この曲で合っていますか？ → {song_candidate['url']}"
                )
            elif song_candidate["url"] not in last_text:
                # アンカーはあるのにURLを省いた（モデルの省略事故）→ 確定的に補う
                last_text = last_text.rstrip() + f"\n→ {song_candidate['url']}"
        return last_text or None, tool_urls
    except Exception as e:  # API エラー・ネットワーク・レート制限など
        logger.warning("ツール付きLLM応答に失敗（ツール無しにフォールバック）: %s", e)
        return None, tool_urls


_URL_RE = re.compile(r"https?://[^\s　）\)】\]」』]+")


def _scrub_foreign_urls(text: Optional[str], extra_allowed: Optional[set[str]] = None) -> Optional[str]:
    """カタログ（taxonomy）に無い URL を除去する（捏造リンク防止の最終ガード）。

    ツール経由で得た実在URLだけが残る。存在しない YouTube リンクをでっち上げても、
    ここでユーザーに届く前に消える。
    extra_allowed: このターンにツールが実際に返したURL（原曲候補など）。カタログ外でも
    実在が保証されているので残す（docs/72）。
    """
    if not text:
        return text
    from app.coaching.tools import CATALOG_VIDEO_URLS

    allowed = CATALOG_VIDEO_URLS | (extra_allowed or set())

    def repl(m: "re.Match") -> str:
        raw = m.group(0)
        cleaned = raw.rstrip("。、,.！!？?")
        return raw if cleaned in allowed else ""

    out = _URL_RE.sub(repl, text)
    # URL 除去で生じた「→ 」「（参考に … ）」の抜け殻や連続空白を軽く整える
    out = re.sub(r"[（(][^（()]*→\s*[)）]", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip() or None


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


# Markdown装飾の除去（docs/42 §2）。フロントの吹き出しは素テキスト描画
# （Bubbles.tsx の whitespace-pre-wrap）なので、`**リップロール**` と書かれると記号がそのまま出る。
# プロンプトで禁じても漏れる（実測: 6回中2回）ため、返す直前に機械的に落とす。
# 行頭の記号だけでなくインラインの強調も対象。改行をまたぐ誤マッチを避けるため1行内に限定する。
_MD_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.M)     # 「## 見出し」
_MD_BULLET_RE = re.compile(r"^[ \t]{0,3}[-*+][ \t]+", re.M)       # 「- 項目」「* 項目」
_MD_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")                   # **太字**
_MD_BOLD_US_RE = re.compile(r"__([^_\n]+?)__")                    # __太字__
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")        # *斜体*（**は上で処理済み）


def scrub_markdown(text: Optional[str]) -> Optional[str]:
    """Markdown記法を落として素の会話文にする（中の言葉は残す）。"""
    if not text:
        return text
    out = _MD_BOLD_RE.sub(r"\1", text)
    out = _MD_BOLD_US_RE.sub(r"\1", out)
    out = _MD_ITALIC_RE.sub(r"\1", out)
    out = _MD_HEADING_RE.sub("", out)
    out = _MD_BULLET_RE.sub("", out)
    return out.strip() or text


def generate_reply(
    state: dict, user_text: str, history: Optional[list[dict]] = None
) -> Optional[str]:
    """ユーザーのテキストに対するソラ先生の自然言語返答を生成する。"""
    context = build_session_context(state)
    contents = _build_contents(state, user_text, history)
    chat_model = settings.llm_chat_model  # 対話は一段上のモデルに格上げ（docs/66）
    tool_urls: set[str] = set()
    # ツール化ON時は function calling 経由（動画等の"事実"は実データをツールで供給）。
    if settings.llm_enabled and settings.coach_tools_enabled:
        # キーワード（動画・お手本…）だけでなく、直前オファーへの承諾（お願いします/はい/
        # どれ？）でもツールを強制する（承諾なのにURLが出ない事故の修正。docs/71）。
        # 原曲の曲名提示（「原曲 ◯◯」や、原曲を尋ねた直後の短い返答）は検索を強制する（docs/72）。
        force: Optional[str] = None
        if _wants_reference(user_text) or _accepts_video_offer(user_text, history):
            force = "find_reference_video"
        elif _names_song_title(user_text, history):
            force = "search_original_song"
        reply, tool_urls = _complete_with_tools(contents, force_tool=force, model=chat_model)
    else:
        reply = _complete(contents, model=chat_model)
    if not reply and settings.llm_enabled:
        # 一過性の失敗（タイムアウト/過負荷）で定型に落ちないよう、1回だけ再試行する（ツール無し）。
        reply = _complete(contents, model=chat_model)
    if reply:
        # facts / 状況 / ユーザー発言 に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(context, user_text))
        # チャット返信はカードを伴わないので、カードを出す約束文を消す
        reply = scrub_card_promise(reply)
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
        # カタログに無い URL（でっち上げリンク）を除去する。ツールが実際に返した
        # 原曲候補URL（実在保証つき）は許可する（docs/72）
        reply = _scrub_foreign_urls(reply, extra_allowed=tool_urls)
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


# --- モデル世代差の吸収（音声入力パス）------------------------------------------------
# チャット経路は _thinking_off() で「2.5 系以外には thinking_config を渡さない」対処をしている。
# 音声パスはそれだけでは足りない: 思考をモデル既定に任せると思考トークンが出力枠を食い、
# 本文が途中で切れる（実測 gemini-flash-latest・thinking_config なし・max=600 で MAX_TOKENS）。
# そこで音声パスは「最小予算を明示 ＋ 出力枠の下限を確保」の2段構えにする。
# モデルが突然死んだときに env の LLM_AUDIO_MODEL 差し替え＋再起動だけで復旧できるよう、
# 危険な組み合わせはここで安全側へ寄せる（再デプロイを待たずに載せ替えるための保険）。
# 思考を切れない世代での最小予算。0 は不可、128 は実測で受理される。
_MIN_THINKING_BUDGET = 128
# 思考が有効な世代で本文が途中で切れないための出力枠の下限。実測（gemini-3.6-flash・
# thinking_budget=128・N=8）で max=400 は 5/8 が finish=MAX_TOKENS、max=1024 は 8/8 STOP。
_MIN_MAX_TOKENS_WITH_THINKING = 1024


def _thinking_off_ok(model: str) -> bool:
    """このモデルで thinking_budget=0 が使えるか（判定は _supports_thinking_budget に一本化）。"""
    return _supports_thinking_budget(model)


def _safe_thinking_budget(model: str, budget: int) -> int:
    """thinking を切れない世代なら 0 指定を最小予算へ引き上げる。"""
    if budget > 0 or _thinking_off_ok(model):
        return budget
    return _MIN_THINKING_BUDGET


def _safe_max_tokens(model: str, budget: int, want: int) -> int:
    """思考トークンが出力枠を食う世代では、本文が切れないよう下限を確保する。"""
    if budget <= 0 and _thinking_off_ok(model):
        return want
    return max(want, _MIN_MAX_TOKENS_WITH_THINKING)


def build_range_hint(analysis: Optional[dict]) -> Optional[dict]:
    """解析結果から「音域移動があるか」の実測事実を作る（docs/42 §4・§5）。

    換声点のつながりは音域を動いた時にしか現れないため、この判定は必須。
    ところが実測で、モデルは音域移動の有無を耳では取り違える（単一音域の録音に
    「移動あり」、2.5オクターブ動く録音に「高い音だけ」と誤答。docs/92 §5.7）。
    f0 は DSP で正確に測れているので、聴かせるのではなく事実として渡す。

    戻り: {"moves": bool, "low_hz", "high_hz", "octaves", "text": 人間向け1行} / None
    """
    if not analysis:
        return None
    cands = []
    med = analysis.get("f0_median_hz")
    if med:
        cands.append(float(med))
    for seg in ((analysis.get("timeline") or {}).get("sustained_segments") or []):
        f = seg.get("mean_f0_hz")
        if f:
            cands.append(float(f))
    cands = [c for c in cands if c and c > 0]
    if len(cands) < 2:
        return None
    lo, hi = min(cands), max(cands)
    octaves = math.log2(hi / lo) if lo > 0 else 0.0
    # 長6度(0.75oct)以上動いていれば換声点をまたぐ可能性がある＝「移動あり」とみなす
    moves = octaves >= 0.75
    if moves:
        text = (f"この録音は約{octaves:.1f}オクターブの音域移動を含む"
                f"（最低 {_note_name(lo)} 付近 〜 最高 {_note_name(hi)} 付近）")
    else:
        text = (f"この録音はほぼ単一の音域（{_note_name(lo)}〜{_note_name(hi)} 付近）で、"
                "換声点をまたぐ音域移動を含まない")
    return {"moves": moves, "low_hz": lo, "high_hz": hi,
            "octaves": round(octaves, 2), "text": text}


def classify_register_audio(
    user_wav: bytes, dsp_hint: Optional[str] = None,
    prev_verdict: Optional[dict] = None,
    range_hint: Optional[dict] = None,
) -> Optional[str]:
    """録音そのものを Gemini に聴かせ、声区（地声/ミックス/裏声）を音色から聞き分ける。

    prev_verdict（任意）: {"text": 前回の判定文, "same_recording": bool}。
    渡すと、判定が前回と変わる場合に「変化」として自然に触れる（黙って逆を言わない）。
    前回に合わせて判定を曲げる方向には使わない（プロンプトで明示）。

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
        # ⚠️ 単一ラベル（地声/ミックス/裏声）の断定をさせない（運用者決定 2026-08-08・docs/42 §4）。
        #    ミックスボイスは「地声と裏声の音色の混合」ではなく、TA優位→CT優位への支配が
        #    音域移動に伴って滑らかに移行し、換声点で段差が出ない筋活動の協調状態を指す。
        #    したがって1つの音を切り取って「これはミックスか」は機構的に答えの出ない問い。
        #    協調は「音域を動いた時に段差が出るか」にしか現れないため、換声点のつながりを聴かせる。
        #    （実測でミックスの的中が全モデル 0/6 だったのは、モデルの限界というより
        #      問いの設計が機構と噛み合っていなかったため。docs/92 §5.6/§5.7）
        # ⚠️ 「迷ったらミックス」という逃げ道も引き続き書かない（docs/92 §5.5）。
        prompt = (
            "あなたは発声の専門家です。この歌声を聴いて、声区（レジスター）について答えてください。\n\n"
            "# 前提（重要）\n"
            "ミックスボイスとは「地声と裏声の音色を混ぜたもの」ではありません。"
            "音域を上がるにつれて、地声を作る筋肉（TA）優位の厚い振動から、裏声を作る筋肉（CT）優位の"
            "薄い伸展へと支配が滑らかに移り、換声点で段差が出ない『つながった状態』のことです。"
            "そのため、1つの音だけを切り取って『これはミックスか』を断定することはできません。"
            "つながりは、音域を動いた時に段差が出るかどうかにしか現れないからです。\n\n"
            "# 答え方\n"
            + (
                # 音域移動の有無は DSP の実測を事実として渡す（耳では取り違えるため。docs/92 §5.7）
                ("この録音には音域移動が含まれます（下の実測を参照）。"
                 "換声点で音色が急に切り替わる『段差』があるかを聴き取って答えてください。"
                 "段差があれば『〜秒あたりで音色が急に切り替わる段差がありました』のように位置と様子を、"
                 "無ければ『段差なく滑らかにつながっています。これがミックスで目指している状態です』と伝えます。\n")
                if (range_hint or {}).get("moves") else
                ("この録音はほぼ単一の音域で、換声点をまたぐ移動を含みません（下の実測を参照）。"
                 "したがって、つながり（＝ミックスができているか）はこの録音からは判定できません。"
                 "その音の状態（芯の強さ・厚み・息の混じり・軽さ）を描写するにとどめ、"
                 "声区がミックスかどうかを断定しないでください。"
                 "『段差なく滑らかにつながっています』のような、つながりを評価する言い方もしないこと。"
                 "そのうえで『ミックスができているかは、低いところから上がってきた時に段差が出ないかで"
                 "分かります。低い音から高い音へサイレンのようにつなげた録音を聴かせてください』と"
                 "次の一歩を伝えます。\n")
                if range_hint else
                # 実測が無い時は、つながりの断定を避けて音の状態だけ述べさせる（安全側）
                ("この録音に音域移動が含まれるかは分かっていません。つながり（ミックスかどうか）は"
                 "断定せず、聴こえた音の状態（芯の強さ・厚み・息の混じり・軽さ）を描写してください。"
                 "そのうえで、低い音から高い音へサイレンのようにつなげた録音があれば"
                 "つながりまで見られる、と次の一歩を伝えます。\n")
            )
            + "迷った時の無難な答えとして『ミックス』という言葉に逃げないこと。\n\n"
            "# 段差があった時の見立て（処方につなげる）\n"
            "・段差の手前まで芯が強く、そこで急に破綻する → 地声で引っぱりすぎ(pulled chest)。"
            "サイレンやリップトリルで換声点をなめらかに通す練習が効きます。\n"
            "・段差の後で急に息っぽく細くなる → 薄い裏声へ逃げている。"
            "ネイ(nay)やギ(gee)で前に当てる練習が効きます。\n"
            "見立てが立つ場合は、練習を1つだけ添えてください。\n\n"
            "根拠になった音色の特徴を一言添え、やわらかい敬体で3〜4文。"
            + (f"\n\n# 音域の実測（この事実に従う。聴いた印象より優先）\n{range_hint['text']}"
               if range_hint else "")
            + (f"\n（参考: 数値解析の声区推定は『{dsp_hint}』ですが、音色の最終判断は実際に聴いた音を優先してください）" if dsp_hint else "")
            + " 重要: 歌詞・曲名・英語や日本語の歌詞フレーズを絶対に引用しない（「」で歌詞を囲まない）。"
            + "場所は『高い音の箇所』『サビあたり』『〜秒あたり』のように音楽的にだけ言う。母音も推測しない。Markdown記号は使わない。"
        )
        # 前回判定の文脈（docs/92: テイク間・再質問で黙って逆を言わない。判定は曲げない）
        if prev_verdict and prev_verdict.get("text"):
            if prev_verdict.get("same_recording"):
                prompt += (
                    "\n\n# 前回のあなたの判定（同じ録音への再質問です）\n"
                    f"「{prev_verdict['text']}」\n"
                    "→ もう一度聴き直して、聴こえたとおりに答えてください。前回に合わせる必要は"
                    "ありません。結論が変わる場合は、どこを聴いてそう判断が変わったかを一言添えてください。"
                )
            else:
                prompt += (
                    "\n\n# 前回の録音（別テイク）へのあなたの判定\n"
                    f"「{prev_verdict['text']}」\n"
                    "→ 今回の録音で判断が変わる場合は、『前回は〜でしたが、今回は〜』のように"
                    "変化として自然に触れてください。歌い方が変われば判定が変わるのは普通のことです。"
                    "前回に引きずられて今回の判定を曲げないこと。"
                )
        parts = [types.Part.from_bytes(data=user_wav, mime_type="audio/wav"),
                 types.Part.from_text(text=prompt)]
        _model = settings.llm_audio_model
        # thinking は原則無効。これが有効だと思考トークンが出力枠を食い尽くし、本文が
        # 数文字で途切れる（声区回答が壊れていた原因）。ただし Gemini 3 系は 0 を拒否するので、
        # その場合だけ最小予算＋広い出力枠に自動で寄せる（_safe_* 参照）。
        _budget = _safe_thinking_budget(_model, settings.llm_audio_thinking_budget)
        cfg = types.GenerateContentConfig(
            max_output_tokens=_safe_max_tokens(_model, _budget, settings.llm_audio_max_tokens),
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=_budget),
        )
        last_err = None
        for attempt in range(2):  # 503(過負荷)など一過性失敗を1回リトライ
            try:
                resp = client.models.generate_content(
                    model=_model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=cfg,
                )
                text = (resp.text or "").strip()
                if text:
                    return scrub_markdown(_scrub_lyrics(text))
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
        # thinking と出力枠はモデル世代に合わせて安全側へ（classify_register_audio と同じ理由）
        _model = settings.llm_audio_model
        _budget = _safe_thinking_budget(_model, settings.llm_audio_thinking_budget)
        resp = client.models.generate_content(
            model=_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=_safe_max_tokens(_model, _budget, settings.llm_audio_max_tokens),
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=_budget),
            ),
        )
        return scrub_markdown((resp.text or "").strip()) or None
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
    # 会話コメントも対話モデルに格上げ（docs/66）
    reply = _complete(contents, timeout_sec=timeout_sec, max_tokens=max_tokens,
                      model=settings.llm_chat_model)
    if reply:
        # facts に無い秒数は伏せる（捏造防止の最終ガード）
        reply = _scrub_invented_seconds(reply, _allowed_seconds(facts))
        # 素テキスト描画なので Markdown 記法を落とす（docs/42 §2）
        reply = scrub_markdown(reply)
    return reply
