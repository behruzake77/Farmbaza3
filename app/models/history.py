from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database.engine import Base


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(BigInteger, nullable=False, index=True)
    query = Column(String(255), nullable=False)
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(BigInteger, nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
