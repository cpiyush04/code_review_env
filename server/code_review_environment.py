# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import os
import sys
from uuid import uuid4
import random
from typing import Dict, TYPE_CHECKING

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

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

# --- Define the 3 Hackathon Tasks ---
TASKS = {
    "easy": {
        "title": "Fix simple typo in helper function",
        "description": "Please review this PR. I added a new math helper.",
        "files": {
            "math_helpers.py": "1: def add_numbers(a, b):\n2:     retun a + b  # Typo here\n3: "
        },
        "bug_file": "math_helpers.py",
        "bug_line": 2,
        "should_approve": False
    },
    "medium": {
        "title": "Add Database Config",
        "description": "Adding the db connection strings for production.",
        "files": {
            "config.py": "1: import os\n2: \n3: DB_HOST = 'prod.db.local'\n4: DB_PASSWORD = 'super_secret_password_123'  # Hardcoded secret!\n5: DB_USER = 'admin'"
        },
        "bug_file": "config.py",
        "bug_line": 4,
        "should_approve": False
    },
    "hard": {
        "title": "User login feature",
        "description": "Added the login endpoint. PTAL.",
        "files": {
            "auth.py": "1: from db import execute\n2: \n3: def login(username, password):\n4:     query = f\"SELECT * FROM users WHERE user='{username}' AND pass='{password}'\"\n5:     return execute(query)  # SQL Injection vulnerability!"
        },
        "bug_file": "auth.py",
        "bug_line": 4,
        "should_approve": False
    }
}

class CodeReviewEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.current_task = None
        self.comments = []
        self.found_bug = False
        self.total_reward = 0.0

    def reset(self, task_level: str = None) -> CodeReviewObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        
        # Select task (random if not specified, allows iterating through all 3)
        level = task_level if task_level in TASKS else random.choice(list(TASKS.keys()))
        self.current_task = TASKS[level]
        self.comments = []
        self.found_bug = False
        self.total_reward = 0.0
        self.task_level = level
        
        return self._build_obs(f"Loaded {level} task. Type 'list_files' to begin.")

    def step(self, action: CodeReviewAction) -> CodeReviewObservation:
        self._state.step_count += 1
        reward = 0.0
        done = False
        status = ""
        current_view = "No file currently viewed."

        if action.command == "list_files":
            status = f"Files in PR: {', '.join(self.current_task['files'].keys())}"
            
        elif action.command == "view_file":
            if action.file_path in self.current_task['files']:
                current_view = self.current_task['files'][action.file_path]
                status = f"Viewing {action.file_path}"
                reward += 0.05 # Tiny reward for exploring
            else:
                status = "File not found."
                reward -= 0.05
                
        elif action.command == "add_comment":
            if action.file_path in self.current_task['files']:
                self.comments.append(ReviewComment(
                    file_path=action.file_path, 
                    line_number=action.line_number, 
                    comment=action.text
                ))
                status = f"Comment added to {action.file_path} on line {action.line_number}."
                
                # Meaningful partial reward: Did they find the exact bug?
                if (not self.found_bug and 
                    action.file_path == self.current_task['bug_file'] and 
                    action.line_number == self.current_task['bug_line']):
                    self.found_bug = True
                    reward += 0.3  # Partial credit for finding the issue
                    status += " [Grader: Bug identified!]"
            else:
                status = "Invalid file for comment."
                reward -= 0.05
                
        elif action.command == "submit_review":
            done = True
            decision = action.text.lower().strip()
            
            if decision == "request_changes" and not self.current_task['should_approve']:
                if self.found_bug:
                    reward += 0.7  # Perfect completion
                    status = "PR properly rejected with correct bugs found. Task Complete!"
                else:
                    reward += 0.2  # Rejected, but missed the actual specific bug
                    status = "PR rejected, but exact bug line was not commented on."
            elif decision == "approve" and self.current_task['should_approve']:
                reward += 1.0
                status = "PR correctly approved. Task Complete!"
            else:
                reward -= 0.5  # Heavy penalty for approving bad code
                status = "Critical Failure: Approved vulnerable/broken code or rejected good code."
        else:
            status = "Unknown command."
            reward -= 0.05

        self.total_reward += reward
        # Clamp reward between 0 and 1 for the final OpenEnv grader spec
        normalized_reward = max(0.0, min(1.0, self.total_reward))

        obs = self._build_obs(status, current_view)
        
        # OpenEnv tuple return structure inside observation wrapper
        obs.done = done
        obs.reward = normalized_reward
        obs.metadata = {"step": self._state.step_count, "task": self.task_level, "found_bug": self.found_bug}
        
        return obs

    def _build_obs(self, status_message: str, current_view: str = "No file currently viewed.") -> CodeReviewObservation:
        return CodeReviewObservation(
            pr_title=self.current_task["title"],
            pr_description=self.current_task["description"],
            changed_files=list(self.current_task["files"].keys()),
            current_file_view=current_view,
            active_comments=self.comments,
            status_message=status_message,
            task_difficulty=self.task_level,
            done=False,
            reward=0.0
        )

    @property
    def state(self) -> State:
        return self._state