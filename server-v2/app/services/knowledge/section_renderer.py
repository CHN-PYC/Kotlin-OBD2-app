from app.services.knowledge.html_extractor import TextBlock


def render_section(blocks: list[TextBlock], *, safety_notes: list[str]) -> str:
    """Render one grouped section as text, retaining headings and safety notes.

    Reject empty input, heading paths shorter than two items, and mixed sections.
    Put document title and section title on separate lines. Prefix each safety
    note with 'Safety: '. Emit a third-level heading when it changes; emit list
    items with '- '. Separate all output entries with two newline characters.
    Inputs must not be modified. This exercise does not construct chunk metadata.
    """
    if not blocks:
        raise ValueError("Section must contain at least one block")

    section_key = blocks[0].heading_path[:2]
    for block in blocks:
        if len(block.heading_path) < 2 or block.heading_path[:2] != section_key:
            raise ValueError("Blocks must share a document title and section title")

    # Slicing creates a new list; appending must not change the source headings.
    lines = section_key.copy()
    for note in safety_notes:
        lines.append(f"Safety: {note}")

    previous_subheading: str | None = None
    for block in blocks:
        # Check the length before reading [2], otherwise two-level paths would fail.
        subheading = block.heading_path[2] if len(block.heading_path) > 2 else None
        if subheading is not None and subheading != previous_subheading:
            lines.append(subheading)
        previous_subheading = subheading

        if block.kind == "list_item":
            lines.append(f"- {block.text}")
        else:
            lines.append(block.text)

    # join returns one string. Return after the loop so every block is included.
    return "\n\n".join(lines)
