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
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure log directory exists
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "artifacts", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "workflow.log")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("loanflow_ai")
logger.info("Initializing configuration and logging to: %s", LOG_FILE)

# Business Rule Configurations
AUTO_APPROVE_MAX_AMOUNT = 10000
AUTO_APPROVE_MIN_CREDIT_SCORE = 750
AUTO_REJECT_CREDIT_SCORE = 600

# Model Configurations
MODEL_NAME = "gemini-3.1-flash-lite"
ENABLE_SECURITY_CHECKPOINT = True
OTEL_TO_CLOUD = False
