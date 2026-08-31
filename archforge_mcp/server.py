"""MCP server exposing the question bank.

Generation and review happen in the calling agent's own session (Claude
Code, Claude Desktop, ...) - not here. This server only stores and serves
questions, so the whole thing runs inside whatever plan (Pro/Max/API key)
the calling agent already has; no separate Anthropic API billing from
this code.
"""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from archforge_mcp.bank import Bank
from archforge_mcp.config import BANK_PATH
from archforge_mcp.schema import ReviewedQuestion

mcp = FastMCP("archforge question bank")
bank = Bank(bank_path=BANK_PATH)


@mcp.tool
def add_questions(questions: list[ReviewedQuestion]) -> dict[str, Any]:
    """Add generated, reviewed questions to the bank.

    Each question must match the ReviewedQuestion shape (scenario,
    question, choices, correct_indices, select_count_hint, difficulty,
    grounding_notes, domain) - fastmcp validates the arguments against
    this schema before the tool body ever runs, and reports a schema
    violation back to the caller as a tool error without touching the
    bank.
    """
    bank.add_questions([q.model_dump() for q in questions])
    return {"added": len(questions), "bank_size": len(bank.questions)}


@mcp.tool
def unattempted(domain: str | None = None) -> list[dict[str, Any]]:
    """List unattempted questions, optionally restricted to one exam domain.

    Each returned question includes `correct_indices` - the caller is the
    one grading the user's answer in conversation, so it needs the answer
    key. Don't reveal it to the user before they answer.
    """
    return bank.unattempted(domain=domain)


@mcp.tool
def record_attempt(qid: str, given_indices: list[int], correct: bool) -> dict[str, Any]:
    """Record an attempt against a question by id.

    Raises a tool error if `qid` doesn't match any question in the bank.
    """
    try:
        bank.record_attempt(qid, given_indices, correct)
    except KeyError as e:
        raise ToolError(str(e)) from e
    return {"recorded": True}


if __name__ == "__main__":
    mcp.run()
