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

import os
import json
import asyncio
import re
from datetime import date
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types
from loan_agent.agent import app
from loan_agent.config import logger

SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
ROUTING_REGEX = re.compile(r'\b\d{9}\b')
BANK_ACCOUNT_REGEX = re.compile(r'\b\d{10,12}\b')

def redact_pii(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = SSN_REGEX.sub("[REDACTED]", text)
    text = CREDIT_CARD_REGEX.sub("[REDACTED]", text)
    text = ROUTING_REGEX.sub("[REDACTED]", text)
    text = BANK_ACCOUNT_REGEX.sub("[REDACTED]", text)
    return text

# Load environment variables
load_dotenv()

DATASET_PATH = "tests/eval/datasets/basic-dataset.json"
OUTPUT_DIR = "artifacts/traces"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "generated_traces.json")

async def generate_traces():
    logger.info("Initializing trace generation...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(DATASET_PATH):
        logger.error("Dataset not found at: %s", DATASET_PATH)
        return
        
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    runner = InMemoryRunner(app=app)
    trace_cases = []
    
    for case in dataset.get("eval_cases", []):
        case_id = case.get("eval_case_id")
        prompt_content = case.get("prompt")
        prompt_text = prompt_content["parts"][0]["text"]
        
        logger.info("Running workflow for case: %s", case_id)
        
        # Create session
        session = await runner.session_service.create_session(
            app_name=app.name,
            user_id="eval_user"
        )
        
        turns = []
        turn_0_events = []
        
        # Turn 0 User Prompt Event (with PII redacted for the trace file)
        redacted_prompt_text = redact_pii(prompt_text)
        turn_0_events.append({
            "author": "user",
            "content": {"parts": [{"text": redacted_prompt_text}]}
        })
        
        # Trigger workflow run
        msg1 = types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
        interrupted = False
        interrupt_id = None
        
        async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=msg1):
            author = event.author or "loanflow_workflow"
            parts = []
            if event.content and event.content.parts:
                for p in event.content.parts:
                    part_dict = {}
                    if p.text:
                        part_dict["text"] = p.text
                    elif p.function_call:
                        fc = p.function_call
                        args = fc.args or {}
                        part_dict["function_call"] = {
                            "name": fc.name,
                            "args": args,
                            "id": fc.id
                        }
                        if fc.name == "adk_request_input":
                            interrupted = True
                            interrupt_id = fc.id
                    elif p.function_response:
                        fr = p.function_response
                        part_dict["function_response"] = {
                            "name": fr.name,
                            "response": fr.response,
                            "id": fr.id
                        }
                    if part_dict:
                        parts.append(part_dict)
            if parts:
                turn_0_events.append({
                    "author": author,
                    "content": {"parts": parts}
                })
                
        turns.append({
            "turn_index": 0,
            "events": turn_0_events
        })
        
        # Handle pause and resume if interrupted
        if interrupted:
            logger.info("Case %s interrupted. Simulating human decision...", case_id)
            
            # Fetch the updated session state from the runner session service
            updated_session = await runner.session_service.get_session(
                app_name=app.name,
                user_id="eval_user",
                session_id=session.id
            )
            state = updated_session.state if updated_session else {}
            
            security_event = state.get("security_event", False)
            risk_data = state.get("risk_assessment") or {}
            risk_level = risk_data.get("risk_level", "LOW")
            recommendation = risk_data.get("recommendation", "approve")
            
            application = state.get("application") or {}
            annual_income = float(application.get("annual_income", 1.0))
            loan_amount = float(application.get("loan_amount", 0.0))
            
            # Simulated human decision logic:
            # - Reject security events
            # - Reject high risk or reject recommendations
            # - Reject if loan amount is more than 5x annual income
            # - Approve low/medium risk
            if security_event:
                simulated_decision = "reject"
            elif risk_level == "HIGH" or recommendation == "reject":
                simulated_decision = "reject"
            elif annual_income > 0 and (loan_amount / annual_income) > 5.0:
                simulated_decision = "reject"
            else:
                simulated_decision = "approve"
                
            logger.info("Simulated decision for case %s: %s", case_id, simulated_decision)
            
            turn_1_events = []
            # Turn 1 User Function Response Event
            turn_1_events.append({
                "author": "user",
                "content": {
                    "parts": [{
                        "function_response": {
                            "name": "adk_request_input",
                            "response": {"human_decision": simulated_decision},
                            "id": interrupt_id
                        }
                    }]
                }
            })
            
            # Resume session execution
            resume_part = types.Part(
                function_response=types.FunctionResponse(
                    name="adk_request_input",
                    response={"human_decision": simulated_decision},
                    id=interrupt_id
                )
            )
            msg2 = types.Content(role="user", parts=[resume_part])
            
            async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=msg2):
                author = event.author or "loanflow_workflow"
                parts = []
                if event.content and event.content.parts:
                    for p in event.content.parts:
                        part_dict = {}
                        if p.text:
                            part_dict["text"] = p.text
                        elif p.function_call:
                            part_dict["function_call"] = {
                                "name": p.function_call.name,
                                "args": p.function_call.args or {},
                                "id": p.function_call.id
                            }
                        elif p.function_response:
                            part_dict["function_response"] = {
                                "name": p.function_response.name,
                                "response": p.function_response.response,
                                "id": p.function_response.id
                            }
                        if part_dict:
                            parts.append(part_dict)
                if parts:
                    turn_1_events.append({
                        "author": author,
                        "content": {"parts": parts}
                    })
                    
            turns.append({
                "turn_index": 1,
                "events": turn_1_events
            })
            
        trace_cases.append({
            "eval_case_id": case_id,
            "agent_data": {
                "agents": {
                    "loanflow_workflow": {
                        "agent_id": "loanflow_workflow",
                        "instruction": "Wired workflow for processing loan approvals, verifying policy thresholds and risks."
                    }
                },
                "turns": turns
            }
        })
        
    output_data = {"eval_cases": trace_cases}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
        
    logger.info("Trace generation complete. Saved %s cases to: %s", len(trace_cases), OUTPUT_PATH)

if __name__ == "__main__":
    asyncio.run(generate_traces())
