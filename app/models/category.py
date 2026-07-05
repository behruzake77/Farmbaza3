from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.engine import Base


class Category(Base):
    __tablename__ = "kategoriyalar"

    id          = Column(Integer, primary_key=True, index=True)
    nomi        = Column(String(100), unique=True, nullable=False)
    gopharm_slug = Column(String(150), nullable=True)   # gopharm.uz kategoriya slug
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Category(id={self.id}, nomi={self.nomi})>"
