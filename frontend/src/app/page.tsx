import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">録音した歌へのフィードバック</h1>
      <div className="flex gap-4">
        <Link className="rounded bg-blue-600 px-4 py-2 text-white" href="/login">
          ログイン
        </Link>
        <Link className="rounded border px-4 py-2" href="/recordings">
          評価履歴一覧
        </Link>
      </div>
    </div>
  );
}
