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

app = FastAPI()

class AlcoholItem(BaseModel):
    percent: int
    ml: int

class AlcoholMasterBase(BaseModel):
    name: str
    percent: int
    default_ml: int

class AlcoholMasterResponse(AlcoholMasterBase):
    id: int
    class Config:
        from_attributes = True

class IntakeCreate(BaseModel):
    date: date
    items: List[AlcoholItem]

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/alcohols", response_model=List[AlcoholMasterResponse])
def get_alcohol_masters(db: Session = Depends(get_db)):
    return db.query(AlcoholMaster).all()

@app.post("/alcohols", response_model=AlcoholMasterResponse)
def save_alcohol_master(data: AlcoholMasterBase, db: Session = Depends(get_db)):
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.name == data.name).first()
    if db_item:
        db_item.percent = data.percent
        db_item.default_ml = data.default_ml
    else:
        db_item = AlcoholMaster(**data.model_dump())
        db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/alcohols/{alc_id}")
def delete_alcohol_master(alc_id: int, db: Session = Depends(get_db)):
    db_item = db.query(AlcoholMaster).filter(AlcoholMaster.id == alc_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return {"status": "deleted"}

@app.get("/intakes")
def get_intakes(year: int, month: int, db: Session = Depends(get_db)):
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
        db_item.items = items_json
        db_item.total_pure_alcohol = int(total_pure + 0.5)
    else:
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
    return db.query(DailyIntake).filter(DailyIntake.date == target_date).first()