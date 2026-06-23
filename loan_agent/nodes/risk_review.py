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

from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from loan_agent.config import MODEL_NAME

class RiskAssessmentOutput(BaseModel):
    risk_score: int = Field(description="A quantitative risk score between 0 and 100")
    risk_level: str = Field(description="LOW (0-30), MEDIUM (31-70), or HIGH (71-100) based on the risk score")
    risk_summary: str = Field(description="Detailed summary explaining the risk assessment findings")
    recommendation: str = Field(description="Recommendation for the loan: approve, review, or reject")

# Create LlmAgent for risk review
llm_risk_assessment = LlmAgent(
    name="llm_risk_assessment",
    model=MODEL_NAME,
    instruction=(
        "You are a professional banking risk review agent. Analyze the provided loan application details.\n"
        "Assess the following:\n"
        "1. Income adequacy compared to loan amount.\n"
        "2. Loan purpose legitimacy.\n"
        "3. Repayment risk and creditworthiness.\n"
        "4. Employment stability.\n"
        "5. Any unusual or suspicious patterns.\n\n"
        "Provide a quantitative risk score (0 to 100) and assign the risk level:\n"
        "- 0 to 30: LOW\n"
        "- 31 to 70: MEDIUM\n"
        "- 71 to 100: HIGH\n"
        "Give a detailed summary of your assessment and recommend: 'approve', 'review', or 'reject'."
    ),
    output_schema=RiskAssessmentOutput,
    output_key="risk_assessment"
)
