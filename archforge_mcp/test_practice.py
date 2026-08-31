import pytest

from archforge_mcp.bank import Bank
from archforge_mcp.practice import parse_answer, run_practice


def make_question(
    domain: str = "Agentic Architecture & Orchestration",
    correct_indices: list[int] | None = None,
) -> dict:
    return {
        "scenario": "A team is designing a multi-agent pipeline.",
        "question": "What should they do?",
        "choices": ["A", "B", "C", "D"],
        "correct_indices": correct_indices if correct_indices is not None else [0],
        "select_count_hint": "Select one answer.",
        "difficulty": "medium",
        "grounding_notes": "Because A is correct.",
        "domain": domain,
    }


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("A", [0]),
        ("a", [0]),
        ("A,C", [0, 2]),
        ("a, c", [0, 2]),
        (" C , A ", [0, 2]),
    ],
)
def test_parse_answer(raw, expected):
    assert parse_answer(raw) == expected


def test_run_practice_no_unattempted_questions_prints_and_returns(tmp_path, monkeypatch, capsys):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question()])
    bank.record_attempt(bank.questions[0]["id"], [0], True)

    def fail_input(_prompt: str) -> str:
        raise AssertionError("input() should not be called when there is nothing to practice")

    monkeypatch.setattr("builtins.input", fail_input)

    run_practice(bank, domain=None, count=None)

    assert "No unattempted questions." in capsys.readouterr().out


def test_run_practice_records_correct_attempt(tmp_path, monkeypatch):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(correct_indices=[0])])

    monkeypatch.setattr("builtins.input", lambda _prompt: "A")

    run_practice(bank, domain=None, count=None)

    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    assert len(reloaded.questions[0]["attempts"]) == 1
    assert reloaded.questions[0]["attempts"][0]["correct"] is True
    assert reloaded.questions[0]["attempts"][0]["given_indices"] == [0]


def test_run_practice_records_incorrect_attempt(tmp_path, monkeypatch):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(correct_indices=[0])])

    monkeypatch.setattr("builtins.input", lambda _prompt: "B")

    run_practice(bank, domain=None, count=None)

    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    assert reloaded.questions[0]["attempts"][0]["correct"] is False


def test_run_practice_respects_count(tmp_path, monkeypatch):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(), make_question(), make_question()])

    calls = 0

    def counting_input(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return "A"

    monkeypatch.setattr("builtins.input", counting_input)

    run_practice(bank, domain=None, count=2)

    assert calls == 2
    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    assert sum(len(q["attempts"]) for q in reloaded.questions) == 2


def test_run_practice_respects_domain_filter(tmp_path, monkeypatch):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions(
        [
            make_question(domain="Tool Design & MCP Integration"),
            make_question(domain="Context Management & Reliability"),
        ]
    )

    monkeypatch.setattr("builtins.input", lambda _prompt: "A")

    run_practice(bank, domain="Tool Design & MCP Integration", count=None)

    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    attempted = [q for q in reloaded.questions if q["attempts"]]
    assert len(attempted) == 1
    assert attempted[0]["domain"] == "Tool Design & MCP Integration"


def test_run_practice_quits_on_q_without_recording_an_attempt(tmp_path, monkeypatch, capsys):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(), make_question()])

    monkeypatch.setattr("builtins.input", lambda _prompt: "Q")

    run_practice(bank, domain=None, count=None)

    assert "Exiting." in capsys.readouterr().out
    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    assert all(len(q["attempts"]) == 0 for q in reloaded.questions)


def test_run_practice_quitting_midway_keeps_prior_attempts(tmp_path, monkeypatch):
    bank = Bank(bank_path=str(tmp_path / "bank.json"))
    bank.add_questions([make_question(), make_question(), make_question()])

    answers = iter(["A", "Q"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    run_practice(bank, domain=None, count=None)

    reloaded = Bank(bank_path=bank.bank_path)
    reloaded.load()
    assert sum(len(q["attempts"]) for q in reloaded.questions) == 1
