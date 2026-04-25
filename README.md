# Alcohol Tracker (アルコールトラッカー)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Infrastructure-Docker-2496ED)](https://www.docker.com/)

日々のアルコール摂取量を記録し、純アルコール量を視覚的に管理するためのアプリケーションです。
厚生労働省のガイドライン等に基づいた健康管理をサポートします。

## 🚀 主な機能

- **カレンダーUI**: 月ごとのカレンダー形式で、日々の飲酒状況を一目で把握。
- **純アルコール量自動計算**: お酒の量(ml) × 度数(%) × 0.8(比重) を自動計算。
- **お酒のマスタ管理**: よく飲むお酒（名前、度数、量）をマスタ登録し、個数を選択するだけで簡単入力。
- **目標設定機能**: 1日の純アルコール摂取限度を設定可能。限度を超えた日はカレンダー上で色が変わります（緑 → オレンジ → 赤）。
- **AI医師によるマンスリー分析**: Google Gemini API を活用し、月間の飲酒傾向に基づいた健康上のアドバイスを生成します。
- **設定の永続化**: データベース(PostgreSQL)および設定ファイルにより、データは永続的に保持されます。

## 🛠 技術スタック

- **Frontend**: [Streamlit](https://streamlit.io/) (Python)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **AI API**: [Google Gemini API](https://ai.google.dev/)
- **Infrastructure**: Docker / Docker Compose

## 💻 システム構成

| コンポーネント | URL / ポート | 備考 |
| :--- | :--- | :--- |
| **Frontend (UI)** | `http://localhost:8501` | Streamlit (Port 8501) |
| **Backend (API)** | `http://localhost:8000` | FastAPI (Port 8000) |
| **API Documentation** | `http://localhost:8000/docs` | Swagger UI (自動生成) |
| **Database** | `localhost:5433` | PostgreSQL |
## 📦 セットアップ方法

### 前提条件

- Docker および Docker Compose がインストールされていること。

### 環境変数の設定

プロジェクトのルートディレクトリに `.env` ファイルを作成し、以下の内容を設定してください。このファイルはコンテナ起動時に読み込まれます。

```.env
# Google AI Studioで取得したAPIキー
GOOGLE_API_KEY=your_google_api_key_here
# バックエンドの外部ポート番号
BACKEND_PORT=8001
#フロントエンドの外部ポート番号
FRONTEND_PORT=8502
#DBの外部ポート番号
DB_PORT=5433
```
※ `GOOGLE_API_KEY` は Google AI Studio で取得可能です。

### 起動手順

1. リポジトリをクローンします。
2. プロジェクトのルートディレクトリに移動します。
3. 以下のコマンドを実行してコンテナをビルド・起動します。

   ```bash
   docker-compose up --build
   ```

4. ブラウザで `http://localhost:8502` にアクセスしてください。

## ライセンス / 利用規約

- **商用利用不可**: 本ソフトウェアを営利目的で利用、配布、または改変して販売することを禁じます。
- 個人利用および学習目的での利用に限定されます。
- ソフトウェアの使用によって生じたいかなる損害についても、作者は一切の責任を負いません。