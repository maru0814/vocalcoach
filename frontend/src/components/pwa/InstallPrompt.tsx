"use client";

import { useEffect, useState } from "react";
import { isStandalone } from "@/lib/push";

/** Chrome系の beforeinstallprompt イベント型（型定義が標準に無いため最小定義）。 */
type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "pwa_install_dismissed_at";
const DISMISS_DAYS = 7;

function recentlyDismissed(): boolean {
  if (typeof window === "undefined") return true;
  const raw = window.localStorage.getItem(DISMISS_KEY);
  if (!raw) return false;
  const ts = Number(raw);
  if (!ts) return false;
  return Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000;
}

function isIos(): boolean {
  if (typeof window === "undefined") return false;
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

function isAndroid(): boolean {
  if (typeof window === "undefined") return false;
  return /android/i.test(window.navigator.userAgent);
}

/** Web Share API（iOSの共有シート起動）に対応しているか。 */
function canShare(): boolean {
  return typeof navigator !== "undefined" && typeof navigator.share === "function";
}

/**
 * SNSアプリ内ブラウザ（WebView）か。X/LINE/Instagram/Facebook などのアプリ内で
 * 開いた場合、共有メニューに「ホーム画面に追加」が出ず PWA を追加できない。
 * → 一度 Safari/Chrome で開き直してもらう必要がある。
 */
function isInAppBrowser(): boolean {
  if (typeof window === "undefined") return false;
  const ua = window.navigator.userAgent;
  // 主要SNS/メッセージアプリのアプリ内ブラウザ
  if (/(FBAN|FBAV|FB_IAB|Instagram|Line|Twitter|TikTok|MicroMessenger|KAKAOTALK)/i.test(ua)) {
    return true;
  }
  // iOSでSafari/Chrome/Firefoxのいずれでもない WKWebView（アプリ内）はトークンが乏しい。
  // 通常のSafari UAは "Safari" を含み、iOS版Chrome(CriOS)/Firefox(FxiOS) も "Safari" を含む。
  const iOS = /iphone|ipad|ipod/i.test(ua);
  if (iOS && !/safari/i.test(ua)) return true;
  return false;
}

/**
 * インストール導線バナー＋手順シート（docs/74 SCR-01 / SCR-02）。
 * - Android/Chrome系: beforeinstallprompt を捕捉して「追加する」で prompt()。
 *   非発火の端末向けに、メニュー操作の手順シートもフォールバックで出す。
 * - iOS/Safari: 非対応なので、実際の共有ボタン（navigator.share）で共有シートを開き、
 *   そこから「ホーム画面に追加」を選んでもらう手順シートを出す。
 * - SNSアプリ内ブラウザ（X/LINE等）: 追加不可なので、まずSafari/Chromeで開き直す案内を出す。
 * - standalone起動時・7日以内に閉じた場合は出さない。自動ポップアップはしない。
 */
export default function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [iosSheet, setIosSheet] = useState(false);
  const [androidSheet, setAndroidSheet] = useState(false);
  const [inAppSheet, setInAppSheet] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isStandalone() || recentlyDismissed()) return;

    // Android/Chrome系
    const onBip = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", onBip);

    // iOS Safari は beforeinstallprompt 非対応、Android も非発火の場合がある
    // → 手順案内でバナーだけ出す
    if (isIos() || isAndroid()) setVisible(true);

    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  const dismiss = () => {
    setVisible(false);
    setIosSheet(false);
    setAndroidSheet(false);
    setInAppSheet(false);
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      /* localStorage不可でも動作継続 */
    }
  };

  const closeSheets = () => {
    setIosSheet(false);
    setAndroidSheet(false);
    setInAppSheet(false);
  };

  const add = async () => {
    if (isInAppBrowser()) {
      // アプリ内ブラウザ（X/LINE等）はホーム画面に追加できない → まずSafari/Chromeで開く案内
      setInAppSheet(true);
    } else if (deferred) {
      // Android/Chrome系はネイティブのインストールプロンプトを優先
      await deferred.prompt();
      await deferred.userChoice;
      setDeferred(null);
      setVisible(false);
    } else if (isIos()) {
      setIosSheet(true);
    } else {
      // Android（beforeinstallprompt非発火）・その他は手順シート
      setAndroidSheet(true);
    }
  };

  /** 現在のURLをクリップボードにコピー（Safari/Chromeに貼り付けて開いてもらう用）。 */
  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(window.location.origin);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* クリップボード不可でも案内文で誘導できる */
    }
  };

  /** iOSの実際の共有シートを開く（そこから「ホーム画面に追加」を選ぶ）。 */
  const openShare = async () => {
    if (!canShare()) return;
    try {
      await navigator.share({
        title: "AIボーカルトレーナー ソラ先生",
        url: window.location.origin,
      });
    } catch {
      /* ユーザーがキャンセルした場合など。何もしない */
    }
  };

  if (!visible) return null;

  return (
    <>
      <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-3 border-t bg-white px-4 py-3 shadow-lg [padding-bottom:env(safe-area-inset-bottom)]">
        <img src="/icons/icon-192.png" alt="" aria-hidden className="h-9 w-9 rounded" />
        <p className="flex-1 text-sm text-slate-800">ホーム画面に置いて、毎日サッと練習</p>
        <button
          onClick={add}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white"
        >
          追加する
        </button>
        <button onClick={dismiss} aria-label="あとで" className="px-1 text-slate-400">
          ×
        </button>
      </div>

      {iosSheet && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-label="ホーム画面への追加方法（iPhone）"
          onClick={closeSheets}
        >
          <div
            className="w-full rounded-t-2xl bg-white p-5 [padding-bottom:calc(1.25rem+env(safe-area-inset-bottom))]"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-3 text-lg font-bold text-slate-800">
              ホーム画面への追加方法（iPhone）
            </h2>
            {canShare() ? (
              <>
                <button
                  onClick={openShare}
                  className="mb-3 w-full rounded bg-blue-600 py-2.5 text-sm font-medium text-white"
                >
                  共有メニューを開く
                </button>
                <ol className="space-y-2 text-sm text-slate-700">
                  <li>1. 上のボタンで共有メニューを開く</li>
                  <li>2. 下にスクロールして「ホーム画面に追加」をタップ</li>
                  <li>3. 右上の「追加」をタップ</li>
                </ol>
              </>
            ) : (
              <ol className="space-y-2 text-sm text-slate-700">
                <li>1. 画面下の共有アイコン（□に↑）をタップ</li>
                <li>2. メニューを下にスクロールして「ホーム画面に追加」をタップ</li>
                <li>3. 右上の「追加」をタップ</li>
              </ol>
            )}
            <p className="mt-3 text-xs text-slate-500">
              追加すると通知も受け取れるようになります。
            </p>
            <button
              onClick={dismiss}
              className="mt-4 w-full rounded bg-slate-100 py-2 text-sm font-medium text-slate-700"
            >
              閉じる
            </button>
          </div>
        </div>
      )}

      {androidSheet && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-label="ホーム画面への追加方法（Android）"
          onClick={closeSheets}
        >
          <div
            className="w-full rounded-t-2xl bg-white p-5 [padding-bottom:calc(1.25rem+env(safe-area-inset-bottom))]"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-3 text-lg font-bold text-slate-800">
              ホーム画面への追加方法（Android）
            </h2>
            <ol className="space-y-2 text-sm text-slate-700">
              <li>1. 画面右上のメニュー（︙）をタップ</li>
              <li>2. 「アプリをインストール」または「ホーム画面に追加」をタップ</li>
              <li>3. 「インストール」または「追加」をタップ</li>
            </ol>
            <p className="mt-3 text-xs text-slate-500">
              追加すると通知も受け取れるようになります。
            </p>
            <button
              onClick={dismiss}
              className="mt-4 w-full rounded bg-slate-100 py-2 text-sm font-medium text-slate-700"
            >
              閉じる
            </button>
          </div>
        </div>
      )}

      {inAppSheet && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-label="ブラウザで開き直す方法"
          onClick={closeSheets}
        >
          <div
            className="w-full rounded-t-2xl bg-white p-5 [padding-bottom:calc(1.25rem+env(safe-area-inset-bottom))]"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="mb-2 text-lg font-bold text-slate-800">
              まずブラウザで開き直してください
            </h2>
            <p className="mb-3 text-sm text-slate-700">
              アプリ内ブラウザ（X・LINE・Instagramなど）からはホーム画面に追加できません。
              {isIos()
                ? "Safariで開き直すと追加できます。"
                : "Chromeで開き直すと追加できます。"}
            </p>
            <ol className="space-y-2 text-sm text-slate-700">
              <li>1. 画面のメニュー（•••）または共有アイコンをタップ</li>
              <li>
                2.{" "}
                {isIos()
                  ? "「Safariで開く」を選ぶ"
                  : "「ブラウザで開く」「Chromeで開く」を選ぶ"}
              </li>
              <li>3. 開いた先で、もう一度この「追加する」を押す</li>
            </ol>
            <p className="mt-3 text-xs text-slate-500">
              メニューが見つからない場合は、下のURLをコピーして
              {isIos() ? "Safari" : "Chrome"}に貼り付けて開いてください。
            </p>
            <button
              onClick={copyUrl}
              className="mt-2 w-full rounded bg-blue-600 py-2.5 text-sm font-medium text-white"
            >
              {copied ? "コピーしました" : "URLをコピー"}
            </button>
            <button
              onClick={dismiss}
              className="mt-3 w-full rounded bg-slate-100 py-2 text-sm font-medium text-slate-700"
            >
              閉じる
            </button>
          </div>
        </div>
      )}
    </>
  );
}
