import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 環境変数からDB接続情報を取得。デフォルトはDocker内PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # 開発環境（Docker等）用のデフォルト。本番の認証情報は必ず環境変数で管理してください。
    DATABASE_URL = "postgresql://user:password@db:5432/alcohol_db"

# RenderやSupabaseなどの環境で "postgres://" となっている場合に "postgresql://" に変換する
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SSL接続の設定（Supabaseなどの外部DBに接続する際のセキュリティ向上）
connect_args = {}
if "localhost" not in DATABASE_URL and "@db:" not in DATABASE_URL:
    # SupabaseなどのクラウドDBではSSL接続を必須に設定
    connect_args = {"sslmode": "require"}

# SQLAlchemyエンジンの作成
# pool_pre_ping=True を追加して、接続が切れている場合に自動で再接続を試みるようにする
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args
)
# セッション作成用のクラス
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base() # モデル定義のベースクラス

def get_db():
    """APIリクエストごとにDBセッションを生成・クローズする依存用関数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()