import pytest

from app.services.knowledge.html_extractor import TextBlock
from app.services.knowledge.section_renderer import render_section


def block(path: list[str], text: str = "Evidence") -> TextBlock:
    return TextBlock(heading_path=path, kind="paragraph", text=text)


def test_renders_headings_safety_lists_and_steps_without_changing_inputs() -> None:
    blocks = [
        block(["Sensor", "Checks"], "Prepare first."),
        block(["Sensor", "Checks", "Connection"], "Inspect connector."),
        TextBlock(
            heading_path=["Sensor", "Checks", "Connection"],
            kind="list_item",
            text="Record findings.",
        ),
        block(["Sensor", "Checks", "Supply"], "Inspect supply."),
    ]
    notes = ["Qualified personnel only."]
    before = [item.model_dump() for item in blocks]
    result = render_section(blocks, safety_notes=notes)
    assert result.split("\n\n") == [
        "Sensor",
        "Checks",
        "Safety: Qualified personnel only.",
        "Prepare first.",
        "Connection",
        "Inspect connector.",
        "- Record findings.",
        "Supply",
        "Inspect supply.",
    ]
    assert [item.model_dump() for item in blocks] == before
    assert notes == ["Qualified personnel only."]


def test_renders_section_without_safety_notes_or_subheadings() -> None:
    assert render_section([block(["Sensor", "Principle"])], safety_notes=[]) == (
        "Sensor\n\nPrinciple\n\nEvidence"
    )


def test_repeated_subheading_is_emitted_again_after_a_different_heading() -> None:
    blocks = [block(["Sensor", "Checks", name]) for name in ["A", "B", "A"]]
    assert render_section(blocks, safety_notes=[]).split("\n\n") == [
        "Sensor",
        "Checks",
        "A",
        "Evidence",
        "B",
        "Evidence",
        "A",
        "Evidence",
    ]


@pytest.mark.parametrize(
    "blocks",
    [
        [],
        [block([])],
        [block(["Sensor"])],
        [block(["Sensor", "Checks"]), block(["Sensor", "Causes"])],
        [block(["Sensor A", "Checks"]), block(["Sensor B", "Checks"])],
    ],
)
def test_rejects_empty_or_mixed_sections(blocks: list[TextBlock]) -> None:
    with pytest.raises(ValueError):
        render_section(blocks, safety_notes=[])
