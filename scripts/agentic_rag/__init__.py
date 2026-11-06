"""Enterprise Agentic RAG agent for the NetCore knowledge base.

    from agentic_rag import ask, show_result
    show_result(ask("What does NCS-SLA-2001 mean?", user_id="bob"))

Demo users: alice (guest), bob (employee), carol (admin).
"""

import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from .agent import AgentResult, ask, build_agent  # noqa: E402
from .cache import clear_cache  # noqa: E402
from .config import DEMO_USERS, get_settings, override_settings  # noqa: E402
from .display import (  # noqa: E402
    show_guardrail_check,
    show_plan,
    show_plan_report,
    show_result,
    show_settings,
    show_trace_table,
    show_users,
)
from .guardrails import check_input, check_output  # noqa: E402

__all__ = ["AgentResult", "DEMO_USERS", "ask", "build_agent", "check_input", "check_output", "clear_cache",
           "get_settings", "override_settings", "show_guardrail_check", "show_plan", "show_plan_report",
           "show_result", "show_settings", "show_trace_table", "show_users"]
