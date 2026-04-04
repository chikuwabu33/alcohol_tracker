# Alcohol Tracker (アルコールトラッカー)

日々のアルコール摂取量を記録し、純アルコール量を視覚的に管理するためのアプリケーションです。
厚生労働省のガイドライン等に基づいた健康管理をサポートします。

## 主な機能

- **カレンダーUI**: 月ごとのカレンダー形式で、日々の飲酒状況を一目で把握。
- **純アルコール量自動計算**: お酒の量(ml) × 度数(%) × 0.8(比重) を自動計算。
- **お酒のマスタ管理**: よく飲むお酒（名前、度数、量）をマスタ登録し、個数を選択するだけで簡単入力。
- **目標設定機能**: 1日の純アルコール摂取限度を設定可能。限度を超えた日はカレンダー上で色が変わります（緑 → オレンジ → 赤）。
- **設定の永続化**: 目標設定値などの個人設定はローカルに保存されます。

## 技術スタック

- **Frontend**: [Streamlit](https://streamlit.io/) (Python)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **Infrastructure**: Docker / Docker Compose

## システム構成

- **Frontend**: `http://localhost:8502`
- **Backend (API)**: `http://localhost:8001`
- **Database**: PostgreSQL (Port: 5433)

## セットアップ方法

### 前提条件

- Docker および Docker Compose がインストールされていること。

### 起動手順

1. リポジトリをクローンします。
2. プロジェクトのルートディレクトリに移動します。
3. 以下のコマンドを実行してコンテナを起動します。

```bash
docker-compose up --build
```

4. ブラウザで `http://localhost:8502` にアクセスしてください。

## ディレクトリ構造

```text
.
├── app/
│   └── src/
│       ├── backend.py      # FastAPI エンドポイント
│       ├── frontend.py     # Streamlit アプリケーション
│       ├── models.py       # SQLAlchemy モデル
│       ├── database.py     # DB接続設定
│       └── settings.json   # アプリ設定（自動生成）
├── docker-compose.yml
├── backend.Dockerfile
├── frontend.Dockerfile
└── requirements.txt
```

## ライセンス / 利用規約

- **商用利用不可**: 本ソフトウェアを営利目的で利用、配布、または改変して販売することを禁じます。
- 個人利用および学習目的での利用に限定されます。
- ソフトウェアの使用によって生じたいかなる損害についても、作者は一切の責任を負いません。