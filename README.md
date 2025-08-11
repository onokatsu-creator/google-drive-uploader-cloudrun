# google-drive-uploader 開発メモ

## よく使うコマンド集

---

### 1. 開発・プレビュー時の基本サイクル

**1. コードの修正**
   - Cloud Shellエディタで、`main.py`や`templates/index.html`などのファイルを編集し、`Ctrl + S`で保存します。

**2. 開発サーバーの起動・再起動**
   - ターミナルで、まずプロジェクトフォルダに移動します。
     ```bash
     cd ~/google-drive-uploader
     ```
   - **【重要】 もしサーバーが既に起動している場合は、一度`Ctrl + C`で必ず停止してください。**
   - 以下のコマンドで、プレビュー用のサーバーを起動します。
     ```bash
     python3 main.py
     ```
   - ライブラリを追加・変更した場合は、起動前に`pip install -r requirements.txt`を実行します。

**3. 動作確認**
   - サーバー起動後、Cloud Shellエディタ右上の**「ウェブでプレビュー」**アイコンから動作を確認します。

---

### 2. 本番環境へのデプロイ

```bash
# 必ず、作業内容をGitHubに保存してから実行すること！
gcloud run deploy google-drive-uploader \
--source . \
--platform managed \
--region asia-northeast1 \
--allow-unauthenticated \
--timeout=300s \
--set-secrets="GOOGLE_CREDENTIALS_JSON=GOOGLE_CREDENTIALS_JSON:latest" \
--set-secrets="NPK_FOLDER_ID=NPK_FOLDER_ID:latest" \
--set-secrets="HABITAT_IMAGE_FOLDER_ID=HABITAT_IMAGE_FOLDER_ID:latest" \
--set-secrets="KINTONE_DOMAIN=KINTONE_DOMAIN:latest" \
--set-secrets="KINTONE_API_TOKEN=KINTONE_API_TOKEN:latest" \
--set-secrets="KINTONE_APP_ID=KINTONE_APP_ID:latest" \
--set-secrets="KINTONE_USER_MASTER_APP_ID=KINTONE_USER_MASTER_APP_ID:latest" \
--set-secrets="KINTONE_USER_MASTER_API_TOKEN=KINTONE_USER_MASTER_API_TOKEN:latest" \
--set-secrets="KINTONE_ATTENDANCE_APP_ID=KINTONE_ATTENDANCE_APP_ID:latest" \
--set-secrets="KINTONE_ATTENDANCE_API_TOKEN=KINTONE_ATTENDANCE_API_TOKEN:latest"


 GitHubへの保存
 # 1. 変更された全てのファイルを記録対象にする
git add .

# 2. 変更内容のメモを付けて記録する
git commit -m "ここに修正内容のメモを書く（例: 生息画像のメモ機能を実装）"

# 3. GitHubに送信する
git push



