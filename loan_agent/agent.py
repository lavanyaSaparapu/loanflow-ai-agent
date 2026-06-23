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

from google.adk.workflow import Workflow, START, Edge
from google.adk.apps import App, ResumabilityConfig
from loan_agent.nodes.parse_event import parse_event
from loan_agent.nodes.security_checkpoint import security_checkpoint
from loan_agent.nodes.policy_router import policy_router, auto_approve, auto_reject
from loan_agent.nodes.risk_review import llm_risk_assessment
from loan_agent.nodes.human_review import human_review
from loan_agent.nodes.record_decision import record_decision

# Wire up the workflow graph edges using dict routing syntax
edges = [
    (START, parse_event),
    (parse_event, security_checkpoint),
    (security_checkpoint, {'normal': policy_router, 'security_bypass': human_review}),
    (policy_router, {'auto_approve': auto_approve, 'auto_reject': auto_reject, 'llm_risk_assessment': llm_risk_assessment}),
    (auto_approve, record_decision),
    (auto_reject, record_decision),
    (llm_risk_assessment, human_review),
    (human_review, record_decision)
]

# Construct Workflow
root_agent = Workflow(
    name="loanflow_workflow",
    edges=edges,
    description="Loan approval workflow graph including rule evaluation, risk assessment, and human-in-the-loop review."
)

# App Container: App name MUST match the directory containing the agent (loan_agent)
app = App(
    root_agent=root_agent,
    name="loan_agent",
    resumability_config=ResumabilityConfig(enabled=True)
)
