import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from archforge_mcp.server import bank, mcp


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


@pytest.fixture(autouse=True)
def _isolated_bank(tmp_path, monkeypatch):
    """Point the server's module-level `bank` at a throwaway file so tests
    never touch the real data/bank.json."""
    monkeypatch.setattr(bank, "bank_path", str(tmp_path / "bank.json"))


async def test_add_questions_saves_to_bank():
    async with Client(mcp) as client:
        result = await client.call_tool("add_questions", {"questions": [make_question()]})

    assert result.data == {"added": 1, "bank_size": 1}
    saved = bank.load_bank()
    assert len(saved) == 1
    assert saved[0]["domain"] == "Agentic Architecture & Orchestration"
    assert saved[0]["attempts"] == []
    assert saved[0]["id"]


async def test_add_questions_appends_to_existing_bank():
    async with Client(mcp) as client:
        await client.call_tool("add_questions", {"questions": [make_question()]})
        result = await client.call_tool("add_questions", {"questions": [make_question()]})

    assert result.data == {"added": 1, "bank_size": 2}
    assert len(bank.load_bank()) == 2


async def test_add_questions_rejects_missing_required_field():
    bad_question = make_question()
    del bad_question["scenario"]

    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("add_questions", {"questions": [bad_question]})

    assert bank.load_bank() == []


async def test_add_questions_rejects_unknown_field():
    bad_question = make_question()
    bad_question["unexpected_field"] = "nope"

    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("add_questions", {"questions": [bad_question]})

    assert bank.load_bank() == []


async def test_unattempted_returns_questions_with_correct_indices():
    seeded = bank.add_questions([], [make_question()])
    bank.save_bank(seeded)

    async with Client(mcp) as client:
        result = await client.call_tool("unattempted", {})

    assert len(result.data) == 1
    assert result.data[0]["correct_indices"] == [0]


async def test_unattempted_excludes_already_attempted_questions():
    seeded = bank.add_questions([], [make_question(), make_question()])
    bank.record_attempt(seeded, seeded[0]["id"], [0], True)
    bank.save_bank(seeded)

    async with Client(mcp) as client:
        result = await client.call_tool("unattempted", {})

    assert len(result.data) == 1
    assert result.data[0]["id"] == seeded[1]["id"]


async def test_unattempted_filters_by_domain():
    seeded = bank.add_questions(
        [],
        [
            make_question(domain="Tool Design & MCP Integration"),
            make_question(domain="Context Management & Reliability"),
        ],
    )
    bank.save_bank(seeded)

    async with Client(mcp) as client:
        result = await client.call_tool("unattempted", {"domain": "Tool Design & MCP Integration"})

    assert len(result.data) == 1
    assert result.data[0]["domain"] == "Tool Design & MCP Integration"


async def test_unattempted_returns_empty_list_when_bank_is_empty():
    async with Client(mcp) as client:
        result = await client.call_tool("unattempted", {})

    assert result.data == []
