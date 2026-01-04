# Multibagger Hunter (日米対応版)

学術論文 *"The Alchemy of Multibagger Stocks (2025)"* の知見に基づき、将来的に株価が10倍以上（マルチバガー）となる可能性を秘めた「米国株」および「日本株」を自動抽出するWebアプリケーション。

## 特徴
- **維持コストゼロ**: GitHub ActionsとGitHub Pagesを利用。
- **完全自動化**: 毎日自動でデータを更新。
- **日米対応**: 米国株と日本株（グロース/スタンダード）を横断検索。

## 抽出ロジック
1.  **Size (小型株)**: 時価総額 20億ドル未満
2.  **Value (割安)**: 低PER、低PBRなど
3.  **Quality (高収益)**: 高ROE (10%以上)
4.  **Cash Flow (現金創出力)**: 高FCF利回り (3〜5%以上)

## ローカルでの実行方法

1. 依存ライブラリのインストール
   ```bash
   pip install -r requirements.txt
   ```

2. データ収集スクリプトの実行
   ```bash
   python scripts/fetch_data.py
   ```
   `public/stock_data.json` が生成されます。

3. アプリの確認
   `index.html` をブラウザで開くか、簡易サーバーを立ち上げて確認します。
   ```bash
   python -m http.server
   ```

## デプロイ方法 (GitHub Pages)

1. このリポジトリをGitHubにプッシュします。
2. リポジトリの `Settings` > `Actions` > `General` > `Workflow permissions` を **Read and write permissions** に変更します。
3. `Settings` > `Pages` > `Source` を `main` ブランチの `/ (root)` に設定します。
4. Actionsが実行されると、データが更新され、ページが公開されます。
