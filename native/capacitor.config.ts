import type { CapacitorConfig } from '@capacitor/cli';

// 本番URL。ステージング検証や独自ドメイン移行時は CAP_SERVER_URL で差し替える（docs/79）。
const APP_URL = process.env.CAP_SERVER_URL || 'https://sora-vocal-ai.duckdns.org';
const APP_HOST = new URL(APP_URL).hostname;

const config: CapacitorConfig = {
  appId: 'com.vocalcoach.sora',
  appName: 'ソラ先生',
  webDir: 'www',
  backgroundColor: '#0b1020',
  server: {
    // 本番ホストのみ WebView 内で開く。それ以外の外部リンクはシステムブラウザへ。
    allowNavigation: [APP_HOST],
  },
  android: {
    // frontend 側の isNativeApp() 判定に使う（docs/79 5.2）
    appendUserAgent: 'VocalCoachApp',
  },
  ios: {
    appendUserAgent: 'VocalCoachApp',
  },
};

export default config;
