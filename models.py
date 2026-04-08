# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import List, Optional, Literal, Dict
from pydantic import Field, BaseModel
from openenv.core.env_server.types import Action, Observation

class ReviewComment(BaseModel):
    file_path: str
    line_number: int
    comment: str

class CodeReviewAction(Action):
    """Actions the agent can take during a code review."""
    command: Literal["list_files", "view_file", "add_comment", "submit_review"] = Field(..., description="Action to perform")
    file_path: str = Field(default="", description="Required for view_file and add_comment")
    line_number: int = Field(default=0, description="Required for add_comment")
    text: str = Field(default="", description="Comment text, OR 'approve'/'request_changes' for submit_review")

class CodeReviewObservation(Observation):
    """What the agent sees at each step."""
    pr_title: str = Field(default="")
    pr_description: str = Field(default="")
    changed_files: List[str] = Field(default_factory=list)
    current_file_view: str = Field(default="No file currently viewed.")
    active_comments: List[ReviewComment] = Field(default_factory=list)
    status_message: str = Field(default="Environment initialized.")
    task_difficulty: str = Field(default="")