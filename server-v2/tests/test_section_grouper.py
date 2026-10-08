import pytest

from app.services.knowledge.html_extractor import TextBlock
from app.services.knowledge.section_grouper import group_section_blocks


def block(path: list[str], text: str = "Example evidence") -> TextBlock:
    return TextBlock(heading_path=path, kind="paragraph", text=text)


def test_groups_steps_under_same_section_and_preserves_inputs() -> None:
    blocks = [
        block(["Sensor"], "Introduction"),
        block(["Sensor", "Principle"]),
        block(["Sensor", "Checks"], "Before checking"),
        block(["Sensor", "Checks", "Step one"]),
        block(["Sensor", "Checks", "Step two"]),
    ]
    before = [item.model_dump() for item in blocks]
    groups = group_section_blocks(blocks)
    assert groups == [[blocks[1]], blocks[2:]]
    groups[0].clear()
    assert [item.model_dump() for item in blocks] == before


def test_does_not_merge_non_adjacent_sections_with_same_name() -> None:
    blocks = [block(["Sensor", name]) for name in ["Checks", "Causes", "Checks"]]
    assert group_section_blocks(blocks) == [[item] for item in blocks]


def test_keeps_document_titles_in_grouping_key() -> None:
    blocks = [block([name, "Checks"]) for name in ["Sensor A", "Sensor B"]]
    assert group_section_blocks(blocks) == [[item] for item in blocks]


@pytest.mark.parametrize("blocks", [[], [block(["Sensor"])]])
def test_empty_input_or_introduction_only_returns_no_groups(blocks: list[TextBlock]) -> None:
    assert group_section_blocks(blocks) == []


def test_rejects_empty_heading_path() -> None:
    with pytest.raises(ValueError):
        group_section_blocks([block([])])
