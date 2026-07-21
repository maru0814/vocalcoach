# native/ — ソラ先生 ネイティブアプリシェル（Capacitor）

既存 Web 版（`https://sora-vocal-ai.duckdns.org`）をそのまま表示する Capacitor シェル。
設計は `docs/79_設計書_ネイティブアプリ化.md`、リリース手順は `docs/81_リリース手順_ネイティブアプリ.md` を参照。

## 仕組み
- `www/index.html`（起動シェル）が本番への到達を確認して `/coach?source=app` へ遷移する。
  オフライン時は日本語の再試行画面を出す。
- `capacitor.config.ts` の `appendUserAgent: "VocalCoachApp"` により、frontend 側の
  `isNativeApp()`（`frontend/src/lib/appMode.ts`）がアプリ内表示を判定し、課金導線を隠す。
- プロダクト機能の変更で本ディレクトリを触る必要はない（Web 側の変更が即アプリに反映される）。

## よく使うコマンド
```bash
npm ci                 # 依存導入
npm run gen            # www/index.html を生成（CAP_SERVER_URL で接続先を上書き可）
npx cap sync android   # www と設定を android/ へ反映
npx cap sync ios       # 同 iOS（pod install は macOS のみ）
```

## ビルド
- ローカルに Android SDK があれば `cd android && ./gradlew assembleDebug`。
- 通常は GitHub Actions（`.github/workflows/native-android.yml`）が
  debug APK（常時）と署名済み release AAB/APK（Secrets 設定時）を Artifacts に出力する。

## バージョン更新（ストア提出のたびに）
`android/app/build.gradle` の `versionCode`（+1 必須）と `versionName` を上げる。

## 触ってよいファイル / 生成物
- 手書き: `capacitor.config.ts` / `templates/index.html.tmpl` / `scripts/*` / 権限まわり
  （`android/app/src/main/AndroidManifest.xml`, `ios/App/App/Info.plist`）
- 生成物（直接編集しない）: `www/` は `npm run gen`、アイコン類は `scripts/gen-android-assets.py`
- コミット禁止: `*.keystore` / `keystore.properties`（.gitignore 済み）
