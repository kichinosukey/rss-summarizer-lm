# Python のスリムイメージをベースにする
FROM python:3.11-slim

WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# コンテナ内で 60 分ごとにスクリプトを実行
CMD ["bash", "-c", "while true; do python -u main.py; sleep 3600; done"]