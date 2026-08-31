"""Local JSON question bank. Generation (expensive, multi-agent) and practice
(cheap, no API calls for grading) are decoupled through this file.

Stateful: a Bank instance holds its own `questions` list (populated by
`load()`), instead of every method taking/returning it - so callers don't
need to thread a `current` list through each call. Each caller (an MCP
tool, the practice CLI) still calls `load()` at the start of its own
operation and `save()` after mutating, so state always comes fresh from
disk rather than trusting whatever another process wrote in the meantime.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

Question = dict[str, Any]


class Bank:
    def __init__(self, bank_path: str) -> None:
        self.bank_path = bank_path
        self.questions: list[Question] = []

    def load(self) -> None:
        if not os.path.exists(self.bank_path):
            self.questions = []
            return
        with open(self.bank_path, encoding="utf-8") as f:
            self.questions = json.load(f)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.bank_path), exist_ok=True)
        with open(self.bank_path, "w", encoding="utf-8") as f:
            json.dump(self.questions, f, ensure_ascii=False, indent=2)

    def add_questions(self, questions: list[Question]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for q in questions:
            q["id"] = uuid.uuid4().hex[:12]
            q["created_at"] = now
            q["attempts"] = []
        self.questions.extend(questions)

    def unattempted(self, domain: str | None = None) -> list[Question]:
        return [
            q
            for q in self.questions
            if not q["attempts"] and (domain is None or q["domain"] == domain)
        ]

    def record_attempt(self, qid: str, given_indices: list[int], correct: bool) -> None:
        for q in self.questions:
            if q["id"] == qid:
                q["attempts"].append(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "given_indices": given_indices,
                        "correct": correct,
                    }
                )
                return
        raise KeyError(f"question id not found in bank: {qid}")

    def domain_stats(self) -> dict[str, dict[str, int]]:
        stats: dict[str, dict[str, int]] = {}
        for q in self.questions:
            d = stats.setdefault(q["domain"], {"total": 0, "attempted": 0, "correct": 0})
            d["total"] += 1
            if q["attempts"]:
                d["attempted"] += 1
                if q["attempts"][-1]["correct"]:
                    d["correct"] += 1
        return stats
