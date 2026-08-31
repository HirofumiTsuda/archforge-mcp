"""App config: exam metadata for the question bank.

Domain weights are the published exam blueprint. Used to compare against
the user's own accuracy in `domain_stats`, and to guide whoever (or
whatever - a Claude Code session) is generating questions on how many to
write per domain.

No model/pricing config here, unlike archforge's config.py: this project
doesn't call the Anthropic API itself. Generation happens in the calling
agent's own session (see DESIGN.md); this MCP server only stores and
serves questions.
"""

EXAM_NAME = "Claude Certified Architect – Foundations (CCA-F)"

DOMAINS = [
    {"name": "Agentic Architecture & Orchestration", "weight": 0.27},
    {"name": "Tool Design & MCP Integration", "weight": 0.18},
    {"name": "Claude Code Configuration & Workflows", "weight": 0.20},
    {"name": "Prompt Engineering & Structured Output", "weight": 0.20},
    {"name": "Context Management & Reliability", "weight": 0.15},
]

BANK_PATH = "data/bank.json"
