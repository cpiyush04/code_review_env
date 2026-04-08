---
title: Code Review Environment Server
emoji: 🔍
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# 🔍 Code Review Environment

An **OpenEnv-compliant AI agent environment** where an LLM agent acts as a code reviewer. The agent must inspect code changes in a simulated Pull Request (PR), identify bugs or security vulnerabilities, add targeted comments, and submit a correct final review decision — all to maximize its reward score.

Built for the **Meta AI Hackathon** using the [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework.

---

## 🧠 What the Agent Does

The agent interacts with a simulated PR review workflow through a structured action space:

| Command | Description |
|---|---|
| `list_files` | List all files changed in the PR |
| `view_file` | Read the contents of a specific file |
| `add_comment` | Leave a review comment on a specific file and line |
| `submit_review` | Submit a final decision: `"approve"` or `"request_changes"` |

The goal is to **find the bug**, comment on the correct line, and **request changes** — earning maximum reward.

---

## 🎯 Tasks & Reward System

The environment ships with **3 built-in tasks** of increasing difficulty, randomly selected at `reset()`:

### Easy — Syntax Bug
- **PR Title**: "Fix simple typo in helper function"
- **Bug**: `retun a + b` typo in `math_helpers.py` (line 2)
- **Goal**: Spot and flag the typo, request changes

### Medium — Security: Hardcoded Secret
- **PR Title**: "Add Database Config"
- **Bug**: Hardcoded `DB_PASSWORD = 'super_secret_password_123'` in `config.py` (line 4)
- **Goal**: Flag the credential leak, request changes

### Hard — Security: SQL Injection
- **PR Title**: "User login feature"
- **Bug**: Unsanitized f-string SQL query in `auth.py` (line 4)
- **Goal**: Identify the SQL injection vector, request changes

### Reward Breakdown

| Action | Reward |
|---|---|
| Viewing the correct file | `+0.05` |
| Viewing a non-existent file | `-0.05` |
| Adding comment on exact bug line | `+0.30` (partial credit) |
| Submitting correct decision + bug found | `+0.70` (final bonus) |
| Submitting correct decision without finding bug | `+0.20` |
| Approving bad code / rejecting good code | `-0.50` |

> Total reward is clamped to `[0.0, 1.0]`. Success threshold: **0.8**.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# From the code_review/ directory
uv sync
```

### 2. Run the Server Locally

```bash
# Development mode (auto-reload)
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

# Or via the project entry point
uv run --project . server
```

### 3. Connect with the Client

```python
import asyncio
from code_review import CodeReviewAction, CodeReviewEnv

async def main():
    async with CodeReviewEnv(base_url="http://localhost:8000") as env:
        # Reset to start a new episode (random task selected)
        result = await env.reset()
        obs = result.observation
        print(f"Task: {obs.pr_title}")
        print(f"Difficulty: {obs.task_difficulty}")

        # List files in the PR
        result = await env.step(CodeReviewAction(command="list_files"))
        print(result.observation.status_message)

        # View a file
        result = await env.step(CodeReviewAction(command="view_file", file_path="math_helpers.py"))
        print(result.observation.current_file_view)

        # Comment on the bug
        result = await env.step(CodeReviewAction(
            command="add_comment",
            file_path="math_helpers.py",
            line_number=2,
            text="Typo: 'retun' should be 'return'"
        ))

        # Submit final review
        result = await env.step(CodeReviewAction(command="submit_review", text="request_changes"))
        print(f"Final reward: {result.reward}")
        print(f"Status: {result.observation.status_message}")

asyncio.run(main())
```

---

## 🤖 Running the AI Agent (Inference)

The `inference.py` script drives an LLM agent through the environment end-to-end.

### Configure Environment Variables

Create a `.env` file (or export the variables):

```env
# Required: API key for the LLM provider
HF_TOKEN=hf_your_token_here
# OR
API_KEY=sk-your-openai-key

# Optional overrides (defaults shown)
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

# Optional: run against a Docker image instead of a local server
IMAGE_NAME=code_review-env:latest
```

### Run the Agent

```bash
# Make sure the server is running first (or use IMAGE_NAME for Docker)
python inference.py
```

The agent will:
1. Reset the environment to get an initial observation
2. Call the LLM at each step to decide the next action (JSON output enforced)
3. Execute up to `MAX_STEPS=10` actions
4. Log each step with reward and action taken
5. Print a final summary: success, total score, and per-step rewards

**Log format:**
```
[START] task=code_review_task env=code_review model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"command": "list_files"} reward=0.00 done=false error=null
[STEP] step=2 action={"command": "view_file", "file_path": "math_helpers.py"} reward=0.05 done=false error=null
...
[END] success=true steps=4 score=1.000 rewards=0.00,0.05,0.35,1.00
```

---

## 🐳 Docker

### Build the Image

```bash
# From the code_review/ directory (project root)
docker build -t code_review-env:latest .
```

### Run the Container

```bash
docker run -p 8000:8000 code_review-env:latest
```

### Available Endpoints

Once running (locally or via Docker), the server exposes:

| Endpoint | Description |
|---|---|
| `POST /reset` | Reset the environment, start a new episode |
| `POST /step` | Execute an action |
| `GET /state` | Get current episode state |
| `GET /schema` | Get action/observation JSON schemas |
| `WS /ws` | WebSocket for persistent low-latency sessions |
| `GET /health` | Health check |
| `/web` | Interactive web UI |
| `/docs` | OpenAPI / Swagger documentation |

---

## ☁️ Deploy to Hugging Face Spaces

```bash
# From the code_review/ directory
openenv push

# With options
openenv push --repo-id my-org/code-review-env --private
```

The deployed Space will be available at:
`https://huggingface.co/spaces/<repo-id>`

---

## 📁 Project Structure

```
code_review/
├── __init__.py                        # Package exports (CodeReviewEnv, CodeReviewAction, etc.)
├── models.py                          # Pydantic models: CodeReviewAction, CodeReviewObservation, ReviewComment
├── client.py                          # Async WebSocket client (CodeReviewEnv)
├── inference.py                       # LLM agent driver script
├── Dockerfile                         # Multi-stage Docker image definition
├── openenv.yaml                       # OpenEnv manifest (name, runtime, port)
├── pyproject.toml                     # Project metadata and dependencies
├── uv.lock                            # Locked dependency tree
├── validate-submission.sh             # Submission validation script
├── .env                               # Environment variables (not committed)
├── .gitignore
└── server/
    ├── __init__.py                    # Server package exports
    ├── app.py                         # FastAPI app factory (HTTP + WebSocket)
    ├── code_review_environment.py     # Core environment logic, tasks, reward calculation
    └── requirements.txt               # Server-specific requirements
```

---

## 🔧 Development

### Test the Environment Directly (No Server)

```bash
python server/code_review_environment.py
```

### Validate the Submission

```bash
bash validate-submission.sh
```

This script checks that:
- Docker builds successfully
- The container starts and becomes healthy
- All API endpoints respond correctly
- The reward system functions as expected

### Run with Concurrent Sessions

Modify `server/app.py` to allow multiple simultaneous agent sessions:

```python
app = create_app(
    CodeReviewEnvironment,
    CodeReviewAction,
    CodeReviewObservation,
    env_name="code_review",
    max_concurrent_envs=4,  # Up from default of 1
)
```

---

## 📋 Requirements

- **Python** >= 3.10
- **uv** (recommended) or pip
- **Docker** (for containerized runs)
- An **API key** for your LLM provider (Hugging Face or OpenAI-compatible)

---

## 📄 License

Copyright (c) Meta Platforms, Inc. and affiliates.  
Licensed under the BSD-style license. See `LICENSE` for details.
