from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from app.database.engine import Base


class ScrapedDrug(Base):
    __tablename__ = "dorilar"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    nomi = Column(String(255), nullable=False, index=True)
    kategoriya = Column(String(100), nullable=True, index=True)
    shakli = Column(String(100), nullable=True)
    rasm_url = Column(String(500), nullable=True)
    tarkibi = Column(Text, nullable=True)
    qollanilishi = Column(Text, nullable=True)
    dozalash = Column(Text, nullable=True)
    bolalar_dozasi = Column(Text, nullable=True)
    retsept = Column(String(100), nullable=True)
    ishlab_chiqaruvchi = Column(String(255), nullable=True)
    mamlakat = Column(String(100), nullable=True)
    atx_kodi = Column(String(20), nullable=True)
    manba_url = Column(String(500), nullable=True)
    qoshilgan_vaqt = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ScrapedDrug(id={self.id}, nomi={self.nomi}, kategoriya={self.kategoriya})>"
