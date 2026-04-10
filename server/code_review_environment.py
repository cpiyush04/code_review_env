# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import os
import sys
from uuid import uuid4
import random
from typing import Dict, TYPE_CHECKING

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Import the refactored external files
from .tasks import TASKS
from .graders import grade_easy, grade_medium, grade_hard, grade_expert

if TYPE_CHECKING:
    from models import CodeReviewAction, CodeReviewObservation, ReviewComment  # type: ignore
else:
    try:
        from ..models import CodeReviewAction, CodeReviewObservation, ReviewComment
    except ImportError:
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from models import CodeReviewAction, CodeReviewObservation, ReviewComment

class CodeReviewEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.current_task = None
        self.comments = []
        self.found_bug = False
        self.total_reward = 0.0
    
    @property
    def tasks(self) -> list[str]:
        return list(TASKS.keys())

    def reset(
        self, 
        seed: int | None = None, 
        episode_id: str | None = None, 
        **kwargs
    ) -> CodeReviewObservation:
        
        new_episode_id = episode_id if episode_id is not None else str(uuid4())
        self._state = State(episode_id=new_episode_id, step_count=0)
        
        if seed is not None:
            random.seed(seed)
            
        task_name = kwargs.get("task_name")
        
        # Select task (random if not specified)
        level = task_name if task_name in TASKS else random.choice(list(TASKS.keys()))
        self.current_task = TASKS[level]
        self.comments = []
        self.found_bug = False
        self.total_reward = 0.0
        self.task_level = level
        
        return self._build_obs(f"Loaded {level} task. Type 'list_files' to begin.")

    def step(
        self, 
        action: CodeReviewAction, 
        timeout_s: float | None = None, 
        **kwargs
    ) -> CodeReviewObservation:
        
        self._state.step_count += 1
        
        # Determine the current file view
        current_view = "No file currently viewed."
        if action.command == "view_file" and action.file_path in self.current_task['files']:
            current_view = self.current_task['files'][action.file_path]
        
        # Track physical state updates that remain in the environment side
        if action.command == "add_comment" and action.file_path in self.current_task['files']:
            self.comments.append(ReviewComment(
                file_path=action.file_path, 
                line_number=action.line_number, 
                comment=action.text
            ))

        if self.task_level == "easy":
            reward, done, status, self.found_bug = grade_easy(action, self.current_task, self.found_bug)
        elif self.task_level == "medium":
            reward, done, status, self.found_bug = grade_medium(action, self.current_task, self.found_bug)
        elif self.task_level == "hard":
            reward, done, status, self.found_bug = grade_hard(action, self.current_task, self.found_bug)
        elif self.task_level == "expert":
            reward, done, status, self.found_bug = grade_expert(action, self.current_task, self.found_bug)
        else:
            reward, done, status = 0.0, False, "Unknown Task Error."

        # Accumulate reward and constrain boundaries
        self.total_reward += reward
        normalized_reward = max(0.01, min(0.99, self.total_reward))

        obs = self._build_obs(status, current_view)
        
        # OpenEnv tuple return structure inside observation wrapper
        obs.done = done
        obs.reward = normalized_reward
        obs.metadata = {"step": self._state.step_count, "task": self.task_level, "found_bug": self.found_bug}
        
        return obs

    def _build_obs(self, status_message: str, current_view: str = "No file currently viewed.") -> CodeReviewObservation:
        safe_reward = max(0.01, min(0.99, self.total_reward))
        
        return CodeReviewObservation(
            pr_title=self.current_task["title"],
            pr_description=self.current_task["description"],
            changed_files=list(self.current_task["files"].keys()),
            current_file_view=current_view,
            active_comments=self.comments,
            status_message=status_message,
            task_difficulty=self.task_level,
            done=False,
            reward=safe_reward
        )

    @property
    def state(self) -> State:
        return self._state