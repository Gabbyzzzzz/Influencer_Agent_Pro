from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 确保 data 目录存在
if not os.path.exists('data'):
    os.makedirs('data')

DB_PATH = "data/memory.db"
engine = create_engine(f"sqlite:///{DB_PATH}?check_same_thread=False")
Base = declarative_base()


class Influencer(Base):
    __tablename__ = 'influencers'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    platform = Column(String)
    url = Column(String, unique=True)
    follower_count = Column(Integer, default=0)
    tags = Column(String)  # 存储原始简介

    fit_score = Column(Integer)
    fit_reason = Column(Text)
    price_min = Column(Float)
    price_max = Column(Float)

    email_draft = Column(Text)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    return SessionLocal()