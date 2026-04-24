from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import calendar
from typing import List
from datetime import date
from pydantic import BaseModel
from .database import engine, get_db, Base
from .models import DailyIntake, AlcoholMaster

# スキーマ変更を反映させるため、一時的にテーブルを削除して再作成する
#Base.metadata.drop_all(bind=engine) 
Base.metadata.create_all(bind=engine)

# FastAPIアプリケーションのインスタンス化
app = FastAPI()

class AlcoholItem(BaseModel):
    """1回に飲んだお酒の情報を保持するスキーマ"""
    percent: int  # アルコール度数 (%)
    ml: int       # 飲んだ量 (ml)

class AlcoholMasterBase(BaseModel):
    """お酒のマスタデータの基本構造"""
    name: str        # お酒の名前（例: ビール、ハイボール）
    percent: int     # デフォルトの度数 (%)
    default_ml: int  # デフォルトの量 (ml)

class AlcoholMasterResponse(AlcoholMasterBase):
    """APIレスポンス用のお酒マスタスキーマ"""
    id: int  # データベース上のID
    class Config:
        from_attributes = True

class IntakeCreate(BaseModel):
    """飲酒記録作成時のリクエストスキーマ"""
    date: date               # 記録対象の日付
    items: List[AlcoholItem] # 飲んだお酒のリスト

@app.get("/health")
def health_check():
    """サーバーの稼働確認用エンドポイント"""
    return {"status": "ok"}

@app.get("/alcohols", response_model=List[AlcoholMasterResponse])
def get_alcohol_masters(db: Session = Depends(get_db)):
    """登録済みのお酒マスタ一覧を取得する"""
    return db.query(AlcoholMaster).all()

@app.post("/alcohols", response_model=AlcoholMasterResponse)
def save_alcohol_master(data: AlcoholMasterBase, db: Session = Depends(get_db)):
    """お酒のマスタを新規登録または更新する"""
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.name == data.name).first()
    if db_item:
        # 既存の場合は情報を更新
        db_item.percent = data.percent
        db_item.default_ml = data.default_ml
    else:
        # 新規登録
        db_item = AlcoholMaster(**data.model_dump())
        db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/alcohols/{alc_id}")
def delete_alcohol_master(alc_id: int, db: Session = Depends(get_db)):
    """指定されたIDのお酒マスタを削除する"""
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.id == alc_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return {"status": "deleted"}

@app.get("/intakes")
def get_intakes(year: int, month: int, db: Session = Depends(get_db)):
    """指定された年月（1ヶ月分）の飲酒記録を取得する"""
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    results = db.query(DailyIntake).filter(
        DailyIntake.date >= start_date,
        DailyIntake.date <= end_date
    ).all()
    return results

@app.post("/intakes")
def save_intake(data: IntakeCreate, db: Session = Depends(get_db)):
    """特定の日付の飲酒記録を保存する"""
    if len(data.items) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 items allowed")
    
    # 純アルコール量計算: ml * (percent/100) * 0.8
    total_pure = sum([ 
        item.ml * (item.percent / 100) * 0.8
        for item in data.items
    ])

    db_item = db.query(DailyIntake).filter(DailyIntake.date == data.date).first()
    items_json = [item.model_dump() for item in data.items]

    if db_item:
        # 既存の記録がある場合は更新
        db_item.items = items_json
        db_item.total_pure_alcohol = int(total_pure + 0.5)
    else:
        # 新規の記録を作成
        db_item = DailyIntake(
            date=data.date,
            items=items_json,
            total_pure_alcohol=int(total_pure + 0.5)
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/intake/{target_date}")
def get_day_intake(target_date: date, db: Session = Depends(get_db)):
    """特定の日付の飲酒詳細データを取得する"""
    return db.query(DailyIntake).filter(DailyIntake.date == target_date).first()