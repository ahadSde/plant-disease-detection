#!/usr/bin/env python3
"""Exercise the container's live CNN → RAG → Gemini endpoint.

Run this from the host only after the container reports /health.  The sample
image is mounted into the container for the curl command documented in README.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python smoke_test.py /path/to/diagnosis-response.json")
    response = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    prediction = response["prediction"]
    retrieval = response["retrieval"]
    advisory = response["advisory"]
    if not prediction["disease_class"]:
        raise AssertionError("CNN returned no class")
    if retrieval["status"] != "ok" or not retrieval["matches"]:
        raise AssertionError(f"RAG did not return grounded context: {retrieval['status']}")
    if advisory["status"] != "ok" or not advisory["answer"] or not advisory["sources"]:
        raise AssertionError("Gemini advisory did not return a grounded answer")
    print(json.dumps({
        "cnn": prediction,
        "rag": {"status": retrieval["status"], "matches": [
            {"chunk_id": item["chunk_id"], "source_file": item["source_file"], "score": item["score"]}
            for item in retrieval["matches"]
        ]},
        "gemini": {"status": advisory["status"], "finish_reason": advisory["finish_reason"], "sources": advisory["sources"]},
    }, indent=2))


if __name__ == "__main__":
    main()
