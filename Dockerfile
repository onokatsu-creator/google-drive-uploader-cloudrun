# 1. ベースとなるPython環境を指定
FROM python:3.11-slim

# 2. 作業ディレクトリを作成し、移動
WORKDIR /app

# 3. 必要なライブラリの一覧をコピー
COPY requirements.txt requirements.txt

# 4. ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションの全ファイルをコピー
COPY . .

# 6. 環境変数でポート番号を指定
ENV PORT 8080

# 7. このポートを外部に公開
EXPOSE 8080

# 8. アプリケーションを実行するコマンド
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]