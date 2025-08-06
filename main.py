# main.py のCloud Run対応・最終版コード（これを丸ごと貼り付けてください）

from flask import Flask, render_template, request, jsonify
import os
import requests
import uuid
from datetime import datetime, timezone, timedelta
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# ★★★ Secret Managerを扱うためのライブラリをインポート ★★★
from google.cloud import secretmanager

app = Flask(__name__)

# --- GCPプロジェクトIDの設定 ---
# Cloud Shellの環境変数から自動で取得します
GCP_PROJECT_ID = "sys-53183373100584097874846988"

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ★★★ 新規追加：Secret Managerから値を取得するための補助関数 ★★★
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
def access_secret_version(secret_id, version_id="latest"):
    """
    Secret Managerから最新のシークレットの値を取得する関数。
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        # JSON形式のシークレットの場合は、ここでJSONオブジェクトに変換
        if secret_id == 'GOOGLE_CREDENTIALS_JSON':
            return json.loads(payload)
        return payload
    except Exception as e:
        # エラーが発生した場合、ログに出力してアプリケーションを停止させる
        # これにより、設定ミスにすぐに気づくことができる
        error_message = f"Failed to access secret: {secret_id}. Error: {e}"
        print(error_message)
        raise SystemExit(error_message)

# --- アプリケーション起動時に、すべての秘密情報を一度に読み込む ---
# これにより、リクエストごとの読み込み遅延を防ぎ、コストも削減できる
try:
    print("Loading secrets from Secret Manager...")
    NPK_FOLDER_ID                 = access_secret_version("NPK_FOLDER_ID")
    HABITAT_IMAGE_FOLDER_ID       = access_secret_version("HABITAT_IMAGE_FOLDER_ID")
    KINTONE_DOMAIN                = access_secret_version("KINTONE_DOMAIN")
    KINTONE_APP_ID                = access_secret_version("KINTONE_APP_ID")
    KINTONE_API_TOKEN             = access_secret_version("KINTONE_API_TOKEN")
    KINTONE_USER_MASTER_APP_ID    = access_secret_version("KINTONE_USER_MASTER_APP_ID")
    KINTONE_USER_MASTER_API_TOKEN = access_secret_version("KINTONE_USER_MASTER_API_TOKEN")
    KINTONE_ATTENDANCE_APP_ID     = access_secret_version("KINTONE_ATTENDANCE_APP_ID")
    KINTONE_ATTENDANCE_API_TOKEN  = access_secret_version("KINTONE_ATTENDANCE_API_TOKEN")
    GOOGLE_CREDENTIALS_JSON       = access_secret_version("GOOGLE_CREDENTIALS_JSON")
    print("All secrets loaded successfully.")
except SystemExit as e:
    # 起動時のシークレット読み込みに失敗した場合は、ここでプログラムが停止する
    print(f"FATAL: Could not start application. {e}")
    # この後のコードは実行されない
    
# --- Kintone連携用の設定値（ハードコードされていたものを変数に） ---
KINTONE_UUID_FIELD_CODE = 'uuid'
KINTONE_STATUS_FIELD_CODE = 'ocr_status'
KINTONE_NPK_TYPE_FIELD_CODE = 'npk_test_type'

# (find_or_create_folder, upload_file_to_google_drive は変更なし)
def find_or_create_folder(drive_service, parent_folder_id, folder_name):
    query = f"'{parent_folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    folders = response.get('files', [])
    if folders:
        return folders[0].get('id')
    else:
        folder_metadata = { 'name': folder_name, 'parents': [parent_folder_id], 'mimeType': 'application/vnd.google-apps.folder' }
        new_folder = drive_service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
        return new_folder.get('id')

def upload_file_to_google_drive(file_storage, filename, folder_id):
    try:
        # ★★★ Secret Managerから読み込んだ認証情報を使用 ★★★
        credentials = service_account.Credentials.from_service_account_info(
            GOOGLE_CREDENTIALS_JSON, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=credentials)
        file_metadata = {'name': filename, 'parents': [folder_id]}
        file_stream = io.BytesIO(file_storage.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file_storage.mimetype, resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        return True, "Google Driveへのアップロードに成功しました。"
    except Exception as e:
        print(f"Google Drive Upload Error: {e}")
        return False, f"Google Driveへのアップロード中にエラーが発生しました: {e}"


# --- 表示・認証関連のルート (Secret Managerから読み込んだ変数を使用する以外は変更なし) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clock-in')
def clock_in():
    return render_template('clock_in.html')

@app.route('/record-attendance', methods=['POST'])
def record_attendance():
    data = request.get_json()
    worker_id = data.get('worker_id')
    if not worker_id: return jsonify({'success': False, 'message': '作業者IDがありません。'}), 400
    try:
        lookup_url = f"https://{KINTONE_DOMAIN}/k/v1/records.json"
        lookup_headers = {'X-Cybozu-API-Token': KINTONE_USER_MASTER_API_TOKEN}
        lookup_params = {'app': KINTONE_USER_MASTER_APP_ID, 'query': f'userid_master = "{worker_id}"', 'fields': ['username_master']}
        lookup_response = requests.get(lookup_url, headers=lookup_headers, params=lookup_params)
        lookup_response.raise_for_status()
        records = lookup_response.json().get('records', [])
        if not records: return jsonify({'success': False, 'message': f'ID「{worker_id}」の作業者が見つかりません。'}), 404
        worker_name = records[0].get('username_master', {}).get('value')
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': 'ユーザーマスタの検索に失敗しました。'}), 500
    try:
        jst = timezone(timedelta(hours=+9), 'JST'); now_jst = datetime.now(jst).isoformat(); latitude = data.get('latitude'); longitude = data.get('longitude'); accuracy = data.get('accuracy')
        record_payload_data = {'worker_id': {'value': worker_id},'worker_name': {'value': worker_name},'clock_in_time': {'value': now_jst},'latitude': {'value': latitude},'longitude': {'value': longitude},'location_accuracy': {'value': accuracy},'map_link': {'value': f"https://www.google.com/maps?q={latitude},{longitude}" if latitude and longitude else ""}}
        record_to_send = {k: v for k, v in record_payload_data.items() if v.get('value') is not None}
        record_payload = {'app': KINTONE_ATTENDANCE_APP_ID, 'record': record_to_send}
        record_url = f"https://{KINTONE_DOMAIN}/k/v1/record.json"
        record_headers = {'X-Cybozu-API-Token': KINTONE_ATTENDANCE_API_TOKEN, 'Content-Type': 'application/json'}
        record_response = requests.post(record_url, json=record_payload, headers=record_headers)
        record_response.raise_for_status()
        return jsonify({'success': True, 'message': '出勤を記録しました。', 'worker_name': worker_name})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': '出勤記録に失敗しました。'}), 500


# --- NPK画像（OCR対象）のアップロード処理 ---
@app.route('/submit', methods=['POST'])
def submit():
    image_file = request.files.get('photo_npk_test_type')
    if not image_file or not image_file.filename: return jsonify({'success': False, 'message': '画像が選択されていません。'}), 400
    record_uuid = str(uuid.uuid4())
    tray_id = request.form.get('treiID')
    if not tray_id: return jsonify({'success': False, 'message': 'トレイIDが入力されていません。'}), 400
    jst = timezone(timedelta(hours=+9), 'JST'); timestamp = datetime.now(jst).strftime('%Y-%m-%dT%H-%M-%S')
    _, original_extension = os.path.splitext(image_file.filename)
    drive_filename = f"{tray_id}_{timestamp}_{record_uuid}{original_extension}"
    success, message = upload_file_to_google_drive(image_file, drive_filename, NPK_FOLDER_ID)
    if not success: return jsonify({'success': False, 'message': message}), 500
    form_data = request.form
    record_payload = {
        KINTONE_UUID_FIELD_CODE: {'value': record_uuid}, KINTONE_STATUS_FIELD_CODE: {'value': 'OCR処理中'}, KINTONE_NPK_TYPE_FIELD_CODE: {'value': '土壌検査'},
        'placeID': {'value': form_data.get('placeID')}, 'houseID': {'value': form_data.get('houseID')}, 'treiID': {'value': form_data.get('treiID')},
        'username': {'value': form_data.get('username')}, 'worker_id': {'value': form_data.get('worker_id')}, 'memo': {'value': form_data.get('memo')}
    }
    record_to_send = {k: v for k, v in record_payload.items() if v.get('value')}
    # ★★★ Secret Managerから読み込んだアプリIDを使用 ★★★
    kintone_payload = {'app': KINTONE_APP_ID, 'record': record_to_send}
    record_url = f"https://{KINTONE_DOMAIN}/k/v1/record.json"
    record_headers = {'X-Cybozu-API-Token': KINTONE_API_TOKEN, 'Content-Type': 'application/json'}
    try:
        response = requests.post(record_url, json=kintone_payload, headers=record_headers)
        response.raise_for_status()
        return jsonify({'success': True, 'message': 'アップロードとKintoneへの登録を開始しました。'})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': 'Kintoneへの先行登録に失敗しました。'}), 500

# --- 生息画像のアップロード処理 ---
# ↓↓↓↓↓↓ この関数全体を、以下の新しいコードに置き換えてください ↓↓↓↓↓↓

# --- 生息画像のアップロード処理 ---
@app.route('/upload_habitat_image', methods=['POST'])
def upload_habitat_image():
    """生息画像を処理する。「生息画像用フォルダ」の中に「トレイID」フォルダを自動作成して保存する。
       メモが入力されている場合は、同名の.txtファイルも作成する。"""

    image_file = request.files.get('habitat_image')
    tray_id = request.form.get('treiID')
    # ★★★ フォームからメモの内容を取得 ★★★
    memo_text = request.form.get('memo')

    if not image_file or not image_file.filename:
        return jsonify({'success': False, 'message': '画像が選択されていません。'}), 400
    if not tray_id:
        return jsonify({'success': False, 'message': 'トレイIDが入力されていません。'}), 400

    try:
        credentials = service_account.Credentials.from_service_account_info(
            GOOGLE_CREDENTIALS_JSON, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=credentials)
        target_folder_id = find_or_create_folder(drive_service, HABITAT_IMAGE_FOLDER_ID, tray_id)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Google Driveのフォルダ操作中にエラー: {e}'}), 500

    # 1. 共通のファイル名を生成 (拡張子なし)
    jst = timezone(timedelta(hours=+9), 'JST')
    timestamp = datetime.now(jst).strftime('%Y-%m-%dT%H-%M-%S')
    base_filename = f"{tray_id}_{timestamp}"
    
    # 2. 画像ファイルをアップロード
    _, original_extension = os.path.splitext(image_file.filename)
    image_filename = f"{base_filename}{original_extension}"
    
    # ★★★ upload_file_to_google_driveを直接呼び出すのではなく、drive_serviceを再利用する形に変更 ★★★
    try:
        image_stream = io.BytesIO(image_file.read())
        image_media = MediaIoBaseUpload(image_stream, mimetype=image_file.mimetype, resumable=True)
        image_metadata = {'name': image_filename, 'parents': [target_folder_id]}
        drive_service.files().create(body=image_metadata, media_body=image_media, fields='id', supportsAllDrives=True).execute()
        print(f"Successfully uploaded image {image_filename}")
    except Exception as e:
        return jsonify({'success': False, 'message': f'画像のアップロード中にエラーが発生しました: {e}'}), 500

    # 3. ★★★ メモが入力されている場合のみ、テキストファイルをアップロード ★★★
    if memo_text and memo_text.strip(): # メモが存在し、かつ空白文字だけでないことを確認
        try:
            memo_filename = f"{base_filename}_memo.txt"
            # メモの内容をバイト列に変換
            memo_bytes = memo_text.encode('utf-8')
            memo_stream = io.BytesIO(memo_bytes)
            memo_media = MediaIoBaseUpload(memo_stream, mimetype='text/plain', resumable=True)
            memo_metadata = {'name': memo_filename, 'parents': [target_folder_id]}
            drive_service.files().create(body=memo_metadata, media_body=memo_media, fields='id', supportsAllDrives=True).execute()
            print(f"Successfully uploaded memo file {memo_filename}")
        except Exception as e:
            # メモのアップロードでエラーが発生しても、画像は成功しているので、成功メッセージを返す
            # ただし、ログにはエラーを残す
            print(f"Warning: Image upload succeeded, but memo upload failed: {e}")

    return jsonify({'success': True, 'message': 'アップロードが完了しました。'})

# ↑↑↑↑↑↑ この関数全体を、上記の新しいコードに置き換えてください ↑↑↑↑↑↑

# --- Cloud Runで実行するためのエントリーポイント ---
if __name__ == '__main__':
    # PORT環境変数はCloud Runによって自動的に設定される
    port = int(os.environ.get('PORT', 8080))
    # gunicornがこのFlaskアプリを直接実行するため、app.run()は不要になるが、
    # 互換性のために残しておく
    app.run(host='0.0.0.0', port=port, debug=False)