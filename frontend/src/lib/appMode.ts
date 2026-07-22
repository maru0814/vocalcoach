/**
 * ネイティブアプリ（Capacitor シェル）内での表示かどうかの判定（docs/79 5.2）。
 * 主判定: シェルが付与する User-Agent "VocalCoachApp"。
 * 従判定: 起動クエリ ?source=app（localStorage に保持し、以降の画面遷移でも維持）。
 * アプリ内では有料プラン購入導線を出さない（docs/78 FR-05, Play 規約対応）。
 */
export function isNativeApp(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (navigator.userAgent.includes("VocalCoachApp")) return true;
    const q = new URLSearchParams(window.location.search);
    if (q.get("source") === "app") {
      localStorage.setItem("vc_app_mode", "1");
      return true;
    }
    return localStorage.getItem("vc_app_mode") === "1";
  } catch {
    return false;
  }
}
