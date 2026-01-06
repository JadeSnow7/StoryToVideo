"""Shared in-memory state for the gateway.

This module provides centralized state management to prevent circular imports
and ensure consistent state access across all gateway modules.
"""

from collections import defaultdict
from typing import Dict, List, Any
import asyncio

# Task storage: task_id -> TaskState
# Note: Using Any for TaskState to avoid circular import
# The actual type is gateway.schemas.task.TaskState
tasks: Dict[str, Any] = {}

# Project storage: project_id -> project dict
projects: Dict[str, Dict] = {}

# Project shots: project_id -> shot_id -> shot dict
project_shots: Dict[str, Dict[str, Dict]] = defaultdict(dict)

# Progress subscriptions: task_id -> list of asyncio.Queue for SSE/WebSocket
progress_subs: Dict[str, List[asyncio.Queue]] = defaultdict(list)

