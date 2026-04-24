import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 環境変数からDB接続情報を取得。デフォルトはDocker内PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/alcohol_db")

# SQLAlchemyエンジンの作成
engine = create_engine(DATABASE_URL)
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