import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "プライバシーポリシー",
  robots: { index: true, follow: true },
};

// 連絡先は特商法ページ（legal/tokushoho）と揃える
const CONTACT_EMAIL = "benfan164@gmail.com";

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <section className="space-y-2">
    <h2 className="font-semibold text-gray-800">{title}</h2>
    <div className="space-y-2 text-gray-700">{children}</div>
  </section>
);

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-6 p-6 text-sm">
      <h1 className="text-xl font-bold">プライバシーポリシー</h1>
      <p className="text-gray-700">
        ソラ先生 運営事務局（以下「当方」）は、AIボーカルトレーナー「ソラ先生」（Webサイトおよびアプリ。以下「本サービス」）に
        おける利用者の情報を、以下のとおり取り扱います。
      </p>

      <Section title="1. 取得する情報">
        <ul className="list-disc space-y-1 pl-5">
          <li>アカウント情報: メールアドレス、パスワード（暗号化して保存します）</li>
          <li>音声データ: 利用者がアップロード・録音した歌声、および比較用の原曲音源</li>
          <li>利用データ: 解析結果・フィードバック履歴・練習記録、機能の利用状況</li>
          <li>技術情報: アクセスログ（IPアドレス・ブラウザ情報等）、Cookie（ログイン状態の維持に使用）</li>
        </ul>
      </Section>

      <Section title="2. 利用目的">
        <ul className="list-disc space-y-1 pl-5">
          <li>歌声の解析とフィードバックの作成・履歴提供（本サービスの提供）</li>
          <li>本人確認・ログイン状態の維持・不正利用の防止</li>
          <li>有料プランの決済・請求（決済は Stripe 社のシステムを利用し、カード番号は当方で保持しません）</li>
          <li>サービスの改善・品質向上・お問い合わせ対応</li>
        </ul>
      </Section>

      <Section title="3. 外部サービスへの提供">
        <p>
          歌声の解析・フィードバック作成のため、音声データおよび関連情報を外部のAIサービス（クラウドAPI）へ送信します。
          送信は本サービスの提供に必要な範囲に限ります。決済情報は Stripe 社が取り扱います。
          これらを除き、法令に基づく場合を除いて、利用者の情報を第三者に提供しません。広告目的での第三者提供は行いません。
        </p>
      </Section>

      <Section title="4. 保管と安全管理">
        <p>
          通信はすべて暗号化（HTTPS）します。取得した情報はアクセスを制限したサーバーで保管し、
          漏えい・滅失の防止に努めます。
        </p>
      </Section>

      <Section title="5. 開示・訂正・削除">
        <p>
          利用者は、自己の情報の開示・訂正・削除（アカウントの削除を含む）を、下記の窓口からいつでも請求できます。
          本人確認のうえ、遅滞なく対応します。
        </p>
      </Section>

      <Section title="6. お問い合わせ窓口">
        <p>{CONTACT_EMAIL}（メールにて随時受付・原則3営業日以内に返信）</p>
      </Section>

      <Section title="7. 改定">
        <p>本ポリシーを改定する場合は、本ページで告知します。重要な変更はサービス内でもお知らせします。</p>
      </Section>

      <p className="pt-2 text-xs text-gray-400">制定日: 2026-07-21</p>
    </main>
  );
}
