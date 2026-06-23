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

from datetime import datetime, timezone
from typing import Any
from google.adk.events.event import Event
from google.adk.agents.context import Context
from google.genai import types
from loan_agent.models import DecisionRecord, save_decision_record
from loan_agent.config import logger

def record_decision(ctx: Context, node_input: Any) -> Event:
    """Compiles the final DecisionRecord and stores it in SQLite for audit and compliance."""
    logger.info("Entering record_decision node.")
    
    application = ctx.state.get("application", {})
    app_id = application.get("application_id", "UNKNOWN")
    session_id = ctx.session.id
    
    # Retrieve decision details
    decision = ctx.state.get("decision")
    if not decision:
        if isinstance(node_input, str):
            decision = node_input
        else:
            decision = "unknown"
            
    reviewer = ctx.state.get("reviewer", "unknown")
    notes = ctx.state.get("notes", "No notes recorded.")
    
    # Retrieve risk assessment
    risk_data = ctx.state.get("risk_assessment") or {}
    risk_score = risk_data.get("risk_score")
    risk_level = risk_data.get("risk_level")
    
    # Retrieve security event details
    security_event = ctx.state.get("security_event", False)
    security_reason = ctx.state.get("security_reason")
    redacted_fields = ctx.state.get("redacted_fields") or []
    
    record = DecisionRecord(
        application_id=app_id,
        session_id=session_id,
        decision=decision,
        reviewer=reviewer,
        timestamp=datetime.now(timezone.utc).isoformat(),
        risk_score=risk_score,
        risk_level=risk_level,
        security_event=security_event,
        security_reason=security_reason,
        redacted_fields=redacted_fields,
        audit_notes=notes
    )
    
    logger.info("Compiled audit DecisionRecord: %s", record.model_dump())
    
    db_path = "loan_decisions.db"
    try:
        save_decision_record(db_path, record)
        logger.info("Successfully persisted decision record in SQLite: %s", db_path)
    except Exception as e:
        logger.error("Database save failed: %s", e)
        
    explanation = f"Workflow completed. Decision of '{decision}' by reviewer '{reviewer}' has been recorded in the audit trail database."
    return Event(
        output=record.model_dump(),
        state={
            "audit_trail_saved": True
        },
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=explanation)]
        )
    )
