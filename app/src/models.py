from sqlalchemy import Column, Integer, Date, JSON, Float, String
from .database import Base

class DailyIntake(Base):
    __tablename__ = "daily_intakes"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    items = Column(JSON, nullable=False) # List of {percent, ml}
    total_pure_alcohol = Column(Integer, nullable=False)

class AlcoholMaster(Base):
    __tablename__ = "alcohol_master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    percent = Column(Integer, nullable=False)
    default_ml = Column(Integer, nullable=False)