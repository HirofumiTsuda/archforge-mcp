"""MCP server exposing the question bank.

Generation and review happen in the calling agent's own session (Claude
Code, Claude Desktop, ...) - not here. This server only stores and serves
questions, so the whole thing runs inside whatever plan (Pro/Max/API key)
the calling agent already has; no separate Anthropic API billing from
this code.
"""

from typing import Any

from fastmcp import FastMCP

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
    current = bank.load_bank()
    updated = bank.add_questions(current, [q.model_dump() for q in questions])
    bank.save_bank(updated)
    return {"added": len(questions), "bank_size": len(updated)}


if __name__ == "__main__":
    mcp.run()
