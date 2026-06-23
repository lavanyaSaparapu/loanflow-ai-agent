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

import json
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.adk.runners import InMemoryRunner, RunConfig
from google.genai import types
from loan_agent.agent import app
from loan_agent.config import logger

fastapi_app = FastAPI(title="LoanFlow AI Agent Server", version="2.0.0")
runner = InMemoryRunner(app=app)

class PubSubMessage(BaseModel):
    data: str

class PubSubPayload(BaseModel):
    message: PubSubMessage
    subscription: str

class LocalPayload(BaseModel):
    applicant_name: str
    annual_income: float
    credit_score: int
    loan_amount: float
    purpose: str
    employment_status: str
    application_date: Optional[str] = None
    application_id: Optional[str] = None

class ResumePayload(BaseModel):
    human_decision: str

def normalize_subscription(subscription: str) -> str:
    """Extracts the subscription ID from a full GCP subscription path."""
    if "/" in subscription:
        return subscription.split("/")[-1]
    return subscription

async def run_workflow_session(payload: dict, metadata: dict) -> dict:
    """Creates a session and runs the workflow e2e, handling pauses."""
    try:
        # Create session
        session = await runner.session_service.create_session(
            app_name=app.name,
            user_id="system",
            state={"subscription": metadata.get("subscription")}
        )
        
        logger.info("Created workflow session %s", session.id)
        
        # Prepare content
        msg = types.Content(
            role="user",
            parts=[types.Part.from_text(text=json.dumps(payload))]
        )
        
        # Run workflow
        interrupted = False
        interrupt_info = {}
        final_decision = None
        
        async for event in runner.run_async(
            user_id="system",
            session_id=session.id,
            new_message=msg,
            run_config=RunConfig(custom_metadata=metadata)
        ):
            if event.output is not None:
                final_decision = event.output
            
            # Detect human review interrupt
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name == "adk_request_input":
                        interrupted = True
                        fc = part.function_call
                        args = fc.args or {}
                        interrupt_info = {
                            "interrupt_id": fc.id,
                            "message": args.get("message")
                        }
                        logger.info("Workflow paused for HITL. Interrupt ID: %s", fc.id)
                        break
            if interrupted:
                break
                
        if interrupted:
            return {
                "status": "referred_for_review",
                "session_id": session.id,
                **interrupt_info
            }
        else:
            return {
                "status": "completed",
                "session_id": session.id,
                "decision": final_decision
            }
            
    except Exception as e:
        logger.exception("Error running workflow session")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/trigger/pubsub")
async def trigger_pubsub(payload: PubSubPayload):
    """Triggers the loan workflow from a Pub/Sub event."""
    logger.info("Received Pub/Sub trigger request for subscription %s", payload.subscription)
    
    normalized_sub = normalize_subscription(payload.subscription)
    metadata = {
        "subscription": normalized_sub,
        "trigger_type": "pubsub"
    }
    
    # We pass the raw Pub/Sub payload wrapper to the parse_event node
    raw_payload = payload.model_dump()
    return await run_workflow_session(raw_payload, metadata)

@fastapi_app.post("/trigger/local")
async def trigger_local(payload: LocalPayload):
    """Triggers the loan workflow locally for debugging and integration testing."""
    logger.info("Received Local trigger request for applicant %s", payload.applicant_name)
    
    metadata = {
        "subscription": None,
        "trigger_type": "local"
    }
    
    raw_payload = payload.model_dump()
    return await run_workflow_session(raw_payload, metadata)

@fastapi_app.post("/resume/{session_id}")
async def resume_session(session_id: str, payload: ResumePayload):
    """Resumes a paused workflow session with a human decision."""
    logger.info("Received resume request for session %s with decision %s", session_id, payload.human_decision)
    
    try:
        # Check if session exists
        session = await runner.session_service.get_session(app_name=app.name, user_id="system", session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
            
        # Build function response part to resume
        part = types.Part(
            function_response=types.FunctionResponse(
                name="adk_request_input",
                response={"human_decision": payload.human_decision},
                id="human_decision"
            )
        )
        msg = types.Content(role="user", parts=[part])
        
        final_decision = None
        async for event in runner.run_async(
            user_id="system",
            session_id=session_id,
            new_message=msg
        ):
            if event.output is not None:
                final_decision = event.output
                
        return {
            "status": "completed",
            "session_id": session_id,
            "decision": final_decision
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error resuming session %s", session_id)
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/health")
def health():
    """Returns the service health status."""
    return {"status": "healthy"}
