# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Code Review Environment Client."""

import os
import sys
from typing import Dict, TYPE_CHECKING

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

if TYPE_CHECKING:
    from models import CodeReviewAction, CodeReviewObservation  # type: ignore
else:
    try:
        from .models import CodeReviewAction, CodeReviewObservation
    except ImportError:
        _pkg_dir = os.path.dirname(os.path.abspath(__file__))
        if _pkg_dir not in sys.path:
            sys.path.insert(0, _pkg_dir)
        from models import CodeReviewAction, CodeReviewObservation


class CodeReviewEnv(
    EnvClient[CodeReviewAction, CodeReviewObservation, State]
):
    """
    Client for the Code Review Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with CodeReviewEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.echoed_message)
        ...
        ...     result = client.step(CodeReviewAction(message="Hello!"))
        ...     print(result.observation.echoed_message)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = CodeReviewEnv.from_docker_image("code_review-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(CodeReviewAction(message="Test"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: CodeReviewAction) -> Dict:
        return {
            "command": action.command,
            "file_path": action.file_path,
            "line_number": action.line_number,
            "text": action.text,
        }

    def _parse_result(self, payload: Dict) -> StepResult[CodeReviewObservation]:
        obs_data = payload.get("observation", {})
        observation = CodeReviewObservation(
            pr_title=obs_data.get("pr_title", ""),
            pr_description=obs_data.get("pr_description", ""),
            changed_files=obs_data.get("changed_files", []),
            current_file_view=obs_data.get("current_file_view", ""),
            status_message=obs_data.get("status_message", ""),
            task_difficulty=obs_data.get("task_difficulty", ""),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
