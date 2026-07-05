from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database.engine import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_uz = Column(String(255), nullable=True)
    name_ru = Column(String(255), nullable=True)
    barcode = Column(String(50), nullable=True, index=True)
    manufacturer = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)

    dosage_form = Column(String(100), nullable=True)
    strength = Column(String(100), nullable=True)

    composition = Column(Text, nullable=True)
    age_group = Column(String(150), nullable=True)
    age_ai_generated = Column(Boolean, default=False)
    description_ai_generated = Column(Boolean, default=False)
    frequency = Column(String(100), nullable=True)
    prescription = Column(Boolean, nullable=True)

    source_url = Column(String(500), nullable=True)

    price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    t136_filial = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Medicine(id={self.id}, name={self.name})>"
