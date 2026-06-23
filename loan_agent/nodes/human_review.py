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

from typing import Any, AsyncGenerator
from google.adk.events.request_input import RequestInput
from google.adk.events.event import Event
from google.adk.agents.context import Context
from google.adk.workflow import node
from google.genai import types
from loan_agent.config import logger

@node(rerun_on_resume=True)
async def human_review(ctx: Context, node_input: Any) -> AsyncGenerator[Any, None]:
    """Pauses the workflow using RequestInput until a human decision is provided."""
    logger.info("Entering human_review node.")
    
    # Check if human_decision was already supplied during resumption
    if not ctx.resume_inputs or "human_decision" not in ctx.resume_inputs:
        application = ctx.state.get("application", {})
        redacted_fields = ctx.state.get("redacted_fields", [])
        security_event = ctx.state.get("security_event", False)
        security_reason = ctx.state.get("security_reason")
        
        # Risk assessment details from state
        risk_data = ctx.state.get("risk_assessment") or {}
        risk_score = risk_data.get("risk_score", "N/A")
        risk_level = risk_data.get("risk_level", "N/A")
        risk_summary = risk_data.get("risk_summary", "N/A")
        recommendation = risk_data.get("recommendation", "N/A")
        
        # Format a professional review prompt
        message = (
            f"=== LOAN APPLICATION FOR HUMAN REVIEW ===\n"
            f"Application ID: {application.get('application_id')}\n"
            f"Applicant Name: {application.get('applicant_name')}\n"
            f"Annual Income: ${application.get('annual_income'):,.2f}\n"
            f"Credit Score: {application.get('credit_score')}\n"
            f"Loan Amount: ${application.get('loan_amount'):,.2f}\n"
            f"Purpose: {application.get('purpose')}\n"
            f"Employment Status: {application.get('employment_status')}\n"
            f"\n"
            f"--- SECURITY CHECKPOINT ---\n"
            f"Security Event: {security_event}\n"
            f"Security Reason: {security_reason or 'None'}\n"
            f"Redacted Fields: {', '.join(redacted_fields) if redacted_fields else 'None'}\n"
            f"\n"
            f"--- LLM RISK ASSESSMENT ---\n"
            f"Risk Score (0-100): {risk_score}\n"
            f"Risk Level: {risk_level}\n"
            f"Recommendation: {recommendation}\n"
            f"Summary: {risk_summary}\n"
            f"\n"
            f"Please reply with 'approve', 'reject', or 'needs_more_info'."
        )
        
        logger.info("Human decision not found in resume_inputs. Raising RequestInput interrupt.")
        yield RequestInput(interrupt_id="human_decision", message=message)
        return

    # Extract human decision from resume_inputs
    raw_decision = ctx.resume_inputs["human_decision"]
    if isinstance(raw_decision, dict):
        decision = raw_decision.get("decision") or raw_decision.get("result") or raw_decision.get("human_decision")
    else:
        decision = raw_decision
        
    decision = str(decision).strip().lower()
    logger.info("Received human decision: %s", decision)
    
    explanation = f"Human review complete. The decision is to {decision} the loan application."
    yield Event(
        output=decision,
        state={
            "decision": decision,
            "reviewer": "human",
            "notes": f"Human reviewer decision: {decision}"
        },
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=explanation)]
        )
    )
