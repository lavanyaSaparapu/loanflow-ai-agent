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

from typing import Any
from google.adk.events.event import Event
from google.adk.agents.context import Context
from google.genai import types
from loan_agent.config import (
    logger,
    AUTO_APPROVE_MIN_CREDIT_SCORE,
    AUTO_APPROVE_MAX_AMOUNT,
    AUTO_REJECT_CREDIT_SCORE,
)

def policy_router(ctx: Context, node_input: Any) -> Event:
    """Applies deterministic banking rules to route the loan application."""
    logger.info("Entering policy_router node.")
    application = ctx.state.get("application") or node_input
    
    credit_score = application.get("credit_score", 0)
    loan_amount = application.get("loan_amount", 0)
    
    logger.info(
        "Application %s details - Credit Score: %s, Loan Amount: %s",
        application.get("application_id"),
        credit_score,
        loan_amount
    )
    
    if credit_score >= AUTO_APPROVE_MIN_CREDIT_SCORE and loan_amount < AUTO_APPROVE_MAX_AMOUNT:
        logger.info("Policy Router decision: Auto Approve route matched.")
        return Event(output=application, route="auto_approve")
    elif credit_score < AUTO_REJECT_CREDIT_SCORE:
        logger.info("Policy Router decision: Auto Reject route matched.")
        return Event(output=application, route="auto_reject")
    else:
        logger.info("Policy Router decision: LLM Risk Assessment route matched.")
        return Event(output=application, route="llm_risk_assessment")

def auto_approve(ctx: Context, node_input: Any) -> Event:
    """Auto-approves the loan and sets final decision state."""
    logger.info("Entering auto_approve node.")
    explanation = "Loan application has been automatically approved based on credit score and loan amount policy rules."
    return Event(
        output="approve",
        state={
            "decision": "approve",
            "reviewer": "system_policy",
            "notes": explanation
        },
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=explanation)]
        )
    )

def auto_reject(ctx: Context, node_input: Any) -> Event:
    """Auto-rejects the loan and sets final decision state."""
    logger.info("Entering auto_reject node.")
    explanation = "Loan application has been automatically rejected due to credit score falling below the required system policy threshold."
    return Event(
        output="reject",
        state={
            "decision": "reject",
            "reviewer": "system_policy",
            "notes": explanation
        },
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=explanation)]
        )
    )
