# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Pydantic models for request/response serialization
class LoanApplication(BaseModel):
    applicant_name: str
    annual_income: float
    credit_score: int
    loan_amount: float
    purpose: str
    employment_status: str
    application_date: Optional[str] = None
    application_id: Optional[str] = None

class DecisionRecord(BaseModel):
    application_id: str
    session_id: Optional[str] = None
    decision: str
    reviewer: str
    timestamp: str
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    security_event: bool = False
    security_reason: Optional[str] = None
    redacted_fields: List[str] = Field(default_factory=list)
    audit_notes: Optional[str] = None

# SQLAlchemy Setup
Base = declarative_base()

class DecisionRecordDB(Base):
    __tablename__ = 'decision_records'
    
    application_id = Column(String, primary_key=True)
    session_id = Column(String, nullable=True)
    decision = Column(String, nullable=False)
    reviewer = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String, nullable=True)
    security_event = Column(Boolean, default=False)
    security_reason = Column(String, nullable=True)
    redacted_fields = Column(String, nullable=True) # Stored as comma-separated string
    audit_notes = Column(String, nullable=True)

# Database persistence helper
def save_decision_record(db_path: str, record: DecisionRecord):
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    db_record = DecisionRecordDB(
        application_id=record.application_id,
        session_id=record.session_id,
        decision=record.decision,
        reviewer=record.reviewer,
        timestamp=record.timestamp,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        security_event=record.security_event,
        security_reason=record.security_reason,
        redacted_fields=",".join(record.redacted_fields),
        audit_notes=record.audit_notes
    )
    
    with Session() as session:
        session.merge(db_record)
        session.commit()
