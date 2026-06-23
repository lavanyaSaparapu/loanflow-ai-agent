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

import re
from typing import Any, Dict
from google.adk.events.event import Event
from google.adk.agents.context import Context
from loan_agent.config import logger, ENABLE_SECURITY_CHECKPOINT

# PII Detection Regexes
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
ROUTING_REGEX = re.compile(r'\b\d{9}\b')
BANK_ACCOUNT_REGEX = re.compile(r'\b\d{10,12}\b')

# Prompt Injection Keywords
INJECTION_KEYWORDS = [
    "ignore previous rules",
    "ignore previous instructions",
    "ignore all instructions",
    "reveal hidden instructions",
    "reveal system prompt",
    "system prompt",
    "developer instructions",
    "developer mode",
    "admin mode",
    "act as administrator",
    "act as the bank manager",
    "roleplay as manager",
    "bypass security",
    "disable security",
    "approve regardless of score",
    "override workflow",
    "skip human review",
    "forget safety checks",
    "grant approval immediately",
    "approve immediately",
    "override policy",
    "bypass approval",
    "you are now the bank manager",
    "always approve",
    "forget security"
]

# Compliance/Suspicious Activity Keywords
COMPLIANCE_KEYWORDS = [
    "money laundering",
    "laundering",
    "illegal",
    "bribe",
    "trafficking",
    "terrorist financing",
    "tax evasion",
    "smuggling"
]

def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    """Screens the application data for PII, prompt injections, and compliance violations."""
    logger.info("Entering security_checkpoint node.")
    
    # Retrieve application from state if node_input is not populated
    application = ctx.state.get("application") or node_input
    if not isinstance(application, dict):
        logger.warning("No application dictionary found in state/input. Bypassing security checkpoint.")
        return Event(output=node_input, route="normal")
        
    if not ENABLE_SECURITY_CHECKPOINT:
        logger.info("Security checkpoint is disabled in config.")
        return Event(output=application, route="normal")

    # Create a copy to modify
    app_copy = dict(application)
    redacted_fields = []
    security_event = ctx.state.get("security_event", False)
    security_reason = ctx.state.get("security_reason")

    # 1. PII Redaction and Security Flagging
    for field, value in app_copy.items():
        if not isinstance(value, str):
            continue
            
        modified = value
        
        # Redact SSNs
        if SSN_REGEX.search(modified):
            modified = SSN_REGEX.sub("[REDACTED]", modified)
            security_event = True
            security_reason = f"PII leak (SSN) detected in field: {field}"
            
        # Redact Credit Cards
        if CREDIT_CARD_REGEX.search(modified):
            modified = CREDIT_CARD_REGEX.sub("[REDACTED]", modified)
            security_event = True
            security_reason = f"PII leak (Credit Card) detected in field: {field}"
            
        # Redact Routing numbers (9 digits)
        if ROUTING_REGEX.search(modified):
            modified = ROUTING_REGEX.sub("[REDACTED]", modified)
            security_event = True
            security_reason = f"PII leak (Routing Number) detected in field: {field}"
            
        # Redact Bank Accounts (10-12 digits)
        if BANK_ACCOUNT_REGEX.search(modified):
            modified = BANK_ACCOUNT_REGEX.sub("[REDACTED]", modified)
            security_event = True
            security_reason = f"PII leak (Bank Account Number) detected in field: {field}"
            
        if modified != value:
            app_copy[field] = modified
            redacted_fields.append(field)
            logger.info("PII redacted in field: %s. Reason: %s", field, security_reason)

    # 2. Prompt Injection Detection
    for field, value in app_copy.items():
        if not isinstance(value, str):
            continue
            
        val_lower = value.lower()
        for kw in INJECTION_KEYWORDS:
            if kw in val_lower:
                security_event = True
                security_reason = f"Prompt injection pattern '{kw}' detected in field: {field}"
                logger.warning("Security Event! %s", security_reason)
                break
        if security_event:
            break

    # 3. Compliance Violation (AML/Suspicious Activity) Detection
    if not security_event:
        for field, value in app_copy.items():
            if not isinstance(value, str):
                continue
                
            val_lower = value.lower()
            for kw in COMPLIANCE_KEYWORDS:
                if kw in val_lower:
                    security_event = True
                    security_reason = f"Compliance violation: Suspicious keyword '{kw}' detected in field: {field}"
                    logger.warning("Security Event! %s", security_reason)
                    break
            if security_event:
                break

    # 4. Routing Decisions
    if security_event:
        return Event(
            output=app_copy,
            route="security_bypass",
            state={
                "application": app_copy,
                "redacted_fields": redacted_fields,
                "security_event": True,
                "security_reason": security_reason
            }
        )
    else:
        return Event(
            output=app_copy,
            route="normal",
            state={
                "application": app_copy,
                "redacted_fields": redacted_fields
            }
        )
