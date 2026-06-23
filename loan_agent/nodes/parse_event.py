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

import base64
import json
import uuid
from datetime import date
from typing import Any
from google.adk.events.event import Event
from google.adk.agents.context import Context
from loan_agent.models import LoanApplication
from loan_agent.config import logger

def parse_event(ctx: Context, node_input: Any) -> Event:
    """Parses incoming loan application payload from local testing or Pub/Sub event."""
    logger.info("Entering parse_event node. Node input type: %s", type(node_input))
    
    raw_data = None
    
    if isinstance(node_input, dict):
        raw_data = node_input
    elif isinstance(node_input, str):
        try:
            raw_data = json.loads(node_input)
        except json.JSONDecodeError:
            raw_data = {"purpose": node_input}
    elif hasattr(node_input, "parts") and node_input.parts:
        text_parts = [p.text for p in node_input.parts if p.text]
        if text_parts:
            text = "".join(text_parts)
            try:
                raw_data = json.loads(text)
            except json.JSONDecodeError:
                raw_data = {"purpose": text}
                
    if not isinstance(raw_data, dict):
        raw_data = {}

    # Handle Pub/Sub format wrapper
    app_data = {}
    if "message" in raw_data and isinstance(raw_data["message"], dict) and "data" in raw_data["message"]:
        pubsub_msg = raw_data["message"]
        encoded_data = pubsub_msg["data"]
        try:
            decoded_bytes = base64.b64decode(encoded_data)
            decoded_str = decoded_bytes.decode("utf-8")
            app_data = json.loads(decoded_str)
            logger.info("Parsed Pub/Sub message successfully.")
        except Exception as e:
            logger.error("Failed to decode Pub/Sub base64: %s", e)
            app_data = {}
    else:
        app_data = raw_data

    # Auto-generate IDs and dates if missing
    if "application_id" not in app_data or not app_data["application_id"]:
        app_data["application_id"] = f"APP-{uuid.uuid4().hex[:8].upper()}"
    if "application_date" not in app_data or not app_data["application_date"]:
        app_data["application_date"] = date.today().isoformat()

    try:
        # Schema validation & field normalization
        normalized = LoanApplication(
            applicant_name=str(app_data.get("applicant_name", "Unknown")),
            annual_income=float(app_data.get("annual_income", 0)),
            credit_score=int(app_data.get("credit_score", 0)),
            loan_amount=float(app_data.get("loan_amount", 0)),
            purpose=str(app_data.get("purpose", "")),
            employment_status=str(app_data.get("employment_status", "Unknown")),
            application_date=str(app_data.get("application_date")),
            application_id=str(app_data.get("application_id"))
        )
        logger.info("Parsed application successfully: %s", normalized.application_id)
        return Event(
            output=normalized.model_dump(),
            state={
                "application": normalized.model_dump(),
                "redacted_fields": [],
                "security_event": False,
                "security_reason": None
            }
        )
    except Exception as e:
        logger.error("Validation failed: %s", e)
        fallback_id = app_data.get("application_id", f"APP-ERR-{uuid.uuid4().hex[:8].upper()}")
        fallback = {
            "applicant_name": str(app_data.get("applicant_name", "Unknown")),
            "annual_income": 0.0,
            "credit_score": 0,
            "loan_amount": 0.0,
            "purpose": str(app_data.get("purpose", "Invalid Data")),
            "employment_status": "Unknown",
            "application_date": app_data.get("application_date", ""),
            "application_id": fallback_id
        }
        return Event(
            output=fallback,
            state={
                "application": fallback,
                "redacted_fields": [],
                "security_event": True,
                "security_reason": f"Payload validation error: {str(e)}"
            }
        )
