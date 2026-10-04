from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Bond(Base):
    """Модель облигации в базе данных."""

    __tablename__ = "bonds"

    secid = Column(String, primary_key=True, nullable=False)
    secname = Column(String, nullable=False)
    listlevel = Column(Integer, nullable=True)
    prevprice = Column(Float, nullable=True)
    effectiveyield = Column(Float, nullable=True)
    matdate = Column(String, nullable=True)
    status = Column(String, nullable=True)
    couponpercent = Column(Float, nullable=True)
    creditrating = Column(String, nullable=True)
    facevalue = Column(Float, nullable=True)
    sectype = Column(String, nullable=True)
    issuesize = Column(Float, nullable=True)
    couponfrequency = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)
    faceunit = Column(String, nullable=True)
    volume = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_bonds_status", "status"),
        Index("idx_bonds_listlevel", "listlevel"),
        Index("idx_bonds_updated_at", "updated_at"),
    )
