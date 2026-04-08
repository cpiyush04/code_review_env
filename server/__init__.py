# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Code Review environment server components."""

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from code_review_environment import CodeReviewEnvironment  # type: ignore
else:
    try:
        from .code_review_environment import CodeReviewEnvironment
    except ImportError:
        _server_dir = os.path.dirname(os.path.abspath(__file__))
        if _server_dir not in sys.path:
            sys.path.insert(0, _server_dir)
        from code_review_environment import CodeReviewEnvironment

__all__ = ["CodeReviewEnvironment"]
