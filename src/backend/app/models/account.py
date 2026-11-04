from app.db.session import Base
from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.sql import func


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String(50), unique=True, index=True, nullable=False)
    account_holder_name = Column(String(200), nullable=False)
    role = Column(String(20), default="viewer", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
