import os
import sys
import json
import textwrap
from typing import List, Optional, TYPE_CHECKING
import asyncio

from openai import OpenAI

# Import the Code Review specific client and models
if TYPE_CHECKING:
    from client import CodeReviewEnv  # type: ignore
    from models import CodeReviewAction  # type: ignore
else:
    try:
        from .client import CodeReviewEnv
        from .models import CodeReviewAction
    except ImportError:
        _pkg_dir = os.path.dirname(os.path.abspath(__file__))
        if _pkg_dir not in sys.path:
            sys.path.insert(0, _pkg_dir)
        from client import CodeReviewEnv
        from models import CodeReviewAction

# --- Environment Variables ---
IMAGE_NAME = os.getenv("IMAGE_NAME") # If you are using docker image 
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASK_NAME = os.getenv("MY_ENV_V4_TASK", "code_review_task")
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "code_review")

MAX_STEPS = 10
TEMPERATURE = 0.2
SUCCESS_SCORE_THRESHOLD = 0.8

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an automated Code Review Agent.
    Your goal is to maximize your reward by finding bugs in the PR and making the correct final decision.
    
    You MUST output valid JSON only, matching one of these action schemas:
    1. {"command": "list_files"}
    2. {"command": "view_file", "file_path": "filename.ext"}
    3. {"command": "add_comment", "file_path": "filename.ext", "line_number": 1, "text": "Bug description"}
    4. {"command": "submit_review", "text": "request_changes"} OR {"command": "submit_review", "text": "approve"}
    
    Reply with exactly one JSON block.
    """
).strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    action_clean = action.replace("\n", "").replace("\r", "")
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def build_user_prompt(step: int, obs_dict: dict, last_reward: float, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    return textwrap.dedent(
        f"""
        Step: {step}
        Current Observation: {json.dumps(obs_dict, indent=2)}
        Last reward: {last_reward:.2f}
        Previous steps:
        {history_block}
        
        Send your next JSON action.
        """
    ).strip()

def get_model_message(client: OpenAI, step: int, obs_dict: dict, last_reward: float, history: List[str]) -> str:
    user_prompt = build_user_prompt(step, obs_dict, last_reward, history)
    try:
        # OpenAI chat completions format
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=TEMPERATURE,
            response_format={"type": "json_object"} # Forces JSON output
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return '{"command": "list_files"}'

async def main() -> None:
    # Initialize OpenAI Client with custom base URL for HF/vLLM routing
    client = OpenAI(
        api_key=API_KEY, 
        base_url=API_BASE_URL
    )

    if IMAGE_NAME:
        env = await CodeReviewEnv.from_docker_image(IMAGE_NAME)
    else:
        env = CodeReviewEnv(base_url="http://localhost:8000")

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset() 
        obs = result.observation
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            obs_dict = {
                "pr_title": obs.pr_title,
                "pr_description": obs.pr_description,
                "changed_files": obs.changed_files,
                "current_file_view": obs.current_file_view,
                "status_message": obs.status_message,
                "task_difficulty": obs.task_difficulty
            }

            raw_action = get_model_message(client, step, obs_dict, last_reward, history)
            
            error = None
            action_obj = None
            
            try:
                action_dict = json.loads(raw_action)
                action_obj = CodeReviewAction(**action_dict)
            except Exception as e:
                error = f"Invalid JSON or Action Format: {str(e)}"
                action_obj = CodeReviewAction(command="list_files")

            try:
                result = await env.step(action_obj)
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done
            except Exception as e:
                error = f"Env step failed: {str(e)}"
                reward = 0.0
                done = True

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=raw_action, reward=reward, done=done, error=error)
            history.append(f"Step {step}: {raw_action} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards)
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
            
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())