"""Run from server-v2: python -m scripts.extract_hella. No network or LLM calls."""

import hashlib
import json
from pathlib import Path

from app.services.knowledge.html_extractor import extract_hella_article


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    metadata = json.loads(
        (root / "data/sources/hella_air_mass_sensor.json").read_text(encoding="utf-8")
    )
    raw = (root / metadata["raw_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise ValueError("Source hash changed; review snapshot and metadata before extraction")
    article = extract_hella_article(raw.decode("utf-8"))
    output = root / "data/processed/hella_air_mass_sensor.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": metadata, "extractor_version": "hella-v1", **article.model_dump()}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(article.blocks)} blocks; {len(article.safety_notes)} safety notes")
    print(output)


if __name__ == "__main__":
    main()
