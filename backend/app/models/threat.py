from sqlalchemy import Column, String, DateTime, Boolean, JSON
from app.db.base import Base
import datetime

class HeritageRisk(Base):
    __tablename__ = "heritage_risks"
    
    site_id = Column(String, primary_key=True)
    risk_score = Column(String)  # Low, Moderate, High
    factors = Column(String)     # Detailed description of hazards
    
    is_alert_active = Column(Boolean, default=False)  # Trigger for admin alerts
    raw_data = Column(JSON)                           # Store the API response for audit
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<HeritageRisk(site_id={self.site_id}, risk={self.risk_score})>"