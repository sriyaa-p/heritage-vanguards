from sqlalchemy import Column, String, Integer, DateTime
from app.db.base import Base

class HeritageRisk(Base):
    __tablename__ = "heritage_risks"
    site_id = Column(String, primary_key=True)
    risk_score = Column(String)  # Low, Moderate, High
    factors = Column(String)     # e.g., "High flood risk, heatwave"
    last_updated = Column(DateTime)