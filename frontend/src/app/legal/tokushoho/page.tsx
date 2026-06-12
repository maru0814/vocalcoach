import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "特定商取引法に基づく表記",
  robots: { index: true, follow: true },
};

/**
 * ⚠️ 公開前に必ず実値へ差し替えてください（法的に必要な記載）。
 * 個人事業主の場合、氏名・住所・電話番号は「消費者からの請求があれば遅滞なく開示」とする
 * 運用が特商法上認められています（discloseOnRequest=true）。屋号やバーチャルオフィスを
 * 使う場合は実値を記載してください。
 */
const SELLER = {
  // 事業者名（個人の場合は氏名、または「氏名＋屋号」）
  name: "丸山ゆう",
  // 運営統括責任者
  manager: "丸山ゆう",
  // 連絡先メール（必須・公開）
  email: "benfan164@gmail.com",
  // 住所・電話は請求時開示にする場合 true（個人事業主向け）。実記載するなら false にして下記を埋める。
  discloseOnRequest: true,
  address: "（所在地）",
  phone: "（電話番号）",
  // 問い合わせ受付時間の目安
  supportHours: "メールにて随時受付（原則3営業日以内に返信）",
};

const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div className="grid grid-cols-1 gap-1 border-b py-3 sm:grid-cols-3 sm:gap-4">
    <dt className="font-medium text-gray-700">{label}</dt>
    <dd className="text-gray-800 sm:col-span-2">{children}</dd>
  </div>
);

export default function TokushohoPage() {
  const onRequest = SELLER.discloseOnRequest;
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-6">
      <h1 className="text-xl font-bold">特定商取引法に基づく表記</h1>
      <dl className="text-sm">
        <Row label="販売事業者">{SELLER.name}</Row>
        <Row label="運営統括責任者">{SELLER.manager}</Row>
        <Row label="所在地">
          {onRequest ? "請求があった場合、遅滞なく開示します。" : SELLER.address}
        </Row>
        <Row label="電話番号">
          {onRequest ? "請求があった場合、遅滞なく開示します。" : SELLER.phone}
        </Row>
        <Row label="お問い合わせ">
          {SELLER.email}
          <br />
          <span className="text-gray-500">{SELLER.supportHours}</span>
        </Row>

        <Row label="販売価格">
          プレミアムプラン: 月額 500円（消費税込）
          <br />
          無料プランは0円でご利用いただけます。
        </Row>
        <Row label="商品代金以外の必要料金">
          インターネット接続にかかる通信料はお客様のご負担となります。
        </Row>
        <Row label="支払方法">クレジットカード決済（Stripe）</Row>
        <Row label="支払時期">
          初回はお申し込み時に決済されます。以後は毎月、同日に自動更新・課金されます。
        </Row>
        <Row label="サービス提供時期">
          決済完了後、ただちにプレミアム機能をご利用いただけます。
        </Row>
        <Row label="解約について">
          設定画面の「プラン管理」からいつでも解約できます。解約後も、当該請求期間の末日までは
          プレミアム機能をご利用いただけます。期間途中の解約による日割り返金は行いません。
        </Row>
        <Row label="返品・返金について">
          サービスの性質上、決済後の返金は原則として承っておりません。
          システム障害等で機能をご利用いただけなかった場合は、お問い合わせ窓口までご連絡ください。
          個別に対応いたします。
        </Row>
        <Row label="動作環境">
          最新版の主要ブラウザ（Chrome / Safari / Edge / Firefox）。音声の録音・再生が可能な環境。
        </Row>
      </dl>

      <p className="pt-2 text-xs text-gray-400">最終更新日: 2026-06-12</p>
    </main>
  );
}
