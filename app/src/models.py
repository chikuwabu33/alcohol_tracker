from sqlalchemy import Column, Integer, Date, JSON, Float, String
from .database import Base

class DailyIntake(Base):
    """日々の飲酒記録を保存するテーブル"""
    __tablename__ = "daily_intakes"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False) # 記録日
    items = Column(JSON, nullable=False) # 飲んだ物の詳細リスト (JSON形式)
    total_pure_alcohol = Column(Integer, nullable=False) # その日の合計純アルコール量(g)

class AlcoholMaster(Base):
    """お酒の種類を登録しておくマスタテーブル"""
    __tablename__ = "alcohol_master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # お酒の名前
    percent = Column(Integer, nullable=False) # 度数 (%)
    default_ml = Column(Integer, nullable=False) # デフォルトの量 (ml)