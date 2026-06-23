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

.PHONY: install playground run-server test generate-traces grade

install:
	uv sync

playground:
	uv run agents-cli playground

run-server:
	uv run uvicorn loan_agent.server:fastapi_app --host 127.0.0.1 --port 8080

test:
	uv run pytest -v

generate-traces:
	uv run python tests/eval/generate_traces.py

grade:
	uv run python tests/eval/grade_traces.py
