from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.engine import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default="uz")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    search_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"
