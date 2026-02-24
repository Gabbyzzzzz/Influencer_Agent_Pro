from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

if not os.path.exists('data'):
    os.makedirs('data')

DB_PATH = "data/memory.db"
engine = create_engine(
    f"sqlite:///{DB_PATH}?check_same_thread=False",
    pool_pre_ping=True,
)
Base = declarative_base()


class SearchBatch(Base):
    """搜索批次 — 每次点击"启动搜索"创建一条"""
    __tablename__ = 'search_batches'

    id = Column(Integer, primary_key=True)
    brand_requirement = Column(Text)
    brand_name = Column(String)
    platforms = Column(String)  # "YouTube,Instagram"
    candidate_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    influencers = relationship("Influencer", back_populates="batch")


class Influencer(Base):
    __tablename__ = 'influencers'

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('search_batches.id'))
    name = Column(String)
    platform = Column(String)
    platform_handle = Column(String)
    url = Column(String, unique=True)
    follower_count = Column(Integer, default=0)
    followers_verified = Column(Boolean, default=False)  # 粉丝数是否经过 API 验证
    engagement_rate = Column(Float)
    tags = Column(String)
    niche = Column(String)
    language = Column(String)

    fit_score = Column(Integer)
    fit_reason = Column(Text)
    price_min = Column(Float)
    price_max = Column(Float)

    email_draft = Column(Text)
    is_confirmed = Column(Boolean, default=False)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    batch = relationship("SearchBatch", back_populates="influencers")

    __table_args__ = (
        Index('ix_platform', 'platform'),
        Index('ix_fit_score', 'fit_score'),
        Index('ix_is_confirmed', 'is_confirmed'),
        Index('ix_batch_id', 'batch_id'),
    )


Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
