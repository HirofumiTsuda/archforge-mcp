import pytest

from archforge_mcp.bank import Bank


def make_question(domain: str = "Agentic Architecture & Orchestration") -> dict:
    return {
        "scenario": "A team is designing a multi-agent pipeline.",
        "question": "What should they do?",
        "choices": ["A", "B", "C", "D"],
        "correct_indices": [0],
        "select_count_hint": "Select one answer.",
        "difficulty": "medium",
        "grounding_notes": "Because A is correct.",
        "domain": domain,
    }


def test_load_missing_file_results_in_empty_questions(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.load()
    assert bank.questions == []


def test_add_questions_persists_to_disk(tmp_path):
    path = str(tmp_path / "bank.json")
    bank = Bank(bank_path=path)
    bank.add_questions([make_question()])

    reloaded = Bank(bank_path=path)
    reloaded.load()
    assert reloaded.questions == bank.questions


def test_add_questions_assigns_id_created_at_and_empty_attempts(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(), make_question()])

    assert len(bank.questions) == 2
    for q in bank.questions:
        assert q["id"]
        assert q["created_at"]
        assert q["attempts"] == []
    # ids are unique
    assert bank.questions[0]["id"] != bank.questions[1]["id"]


def test_add_questions_extends_existing_bank(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question()])
    bank.add_questions([make_question()])

    assert len(bank.questions) == 2


def test_unattempted_returns_only_questions_without_attempts(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(), make_question()])
    bank.record_attempt(bank.questions[0]["id"], [0], True)

    remaining = bank.unattempted()

    assert len(remaining) == 1
    assert remaining[0]["id"] == bank.questions[1]["id"]


def test_unattempted_filters_by_domain(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions(
        [
            make_question(domain="Tool Design & MCP Integration"),
            make_question(domain="Context Management & Reliability"),
        ]
    )

    remaining = bank.unattempted(domain="Tool Design & MCP Integration")

    assert len(remaining) == 1
    assert remaining[0]["domain"] == "Tool Design & MCP Integration"


def test_record_attempt_appends_attempt_with_expected_fields(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question()])
    qid = bank.questions[0]["id"]

    bank.record_attempt(qid, [0, 2], False)

    attempts = bank.questions[0]["attempts"]
    assert len(attempts) == 1
    assert attempts[0]["given_indices"] == [0, 2]
    assert attempts[0]["correct"] is False
    assert attempts[0]["ts"]


def test_record_attempt_unknown_id_raises_key_error(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question()])

    with pytest.raises(KeyError):
        bank.record_attempt("does-not-exist", [0], True)


def test_domain_stats_counts_total_attempted_and_correct_per_domain(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions(
        [
            make_question(domain="Agentic Architecture & Orchestration"),
            make_question(domain="Agentic Architecture & Orchestration"),
            make_question(domain="Tool Design & MCP Integration"),
        ]
    )
    bank.record_attempt(bank.questions[0]["id"], [0], True)
    bank.record_attempt(bank.questions[1]["id"], [1], False)
    # third question (Tool Design) stays unattempted

    stats = bank.domain_stats()

    assert stats["Agentic Architecture & Orchestration"] == {
        "total": 2,
        "attempted": 2,
        "correct": 1,
    }
    assert stats["Tool Design & MCP Integration"] == {
        "total": 1,
        "attempted": 0,
        "correct": 0,
    }


def test_domain_stats_uses_most_recent_attempt(tmp_path):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question()])
    qid = bank.questions[0]["id"]

    bank.record_attempt(qid, [0], False)
    bank.record_attempt(qid, [0], True)

    stats = bank.domain_stats()

    assert stats["Agentic Architecture & Orchestration"]["correct"] == 1
