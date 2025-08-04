# google-drive-uploader 開発メモ

## よく使うコマンド集

### 1. ローカルでのプレビュー起動
```bash
cd google-drive-uploader
python3 main.py



gcloud run deploy google-drive-uploader \
--source . \
--platform managed \
--region asia-northeast1 \
--allow-unauthenticated \
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




git add .
git commit -m "ここに修正内容のメモを書く"
git push