#!/usr/bin/env python3
"""Run the required standalone Stage 4 Colab verification scenarios.

Set GOOGLE_API_KEY in the Colab environment before executing this script. It
uses the saved Stage 3 FAISS index; it does not rebuild or modify the index.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


AI_SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_SERVICE))

from llm.advisor import LLMAdvisor
from rag.retriever import RAGRetriever


def main() -> None:
    retriever = RAGRetriever(threshold=0.40)
    advisor = LLMAdvisor()

    apple_class = "Apple___Apple_scab"
    apple_retrieval = retriever.retrieve(
        "Apple scab symptoms and management", disease_class=apple_class, top_k=3
    )
    initial = advisor.start_diagnosis(apple_class, apple_retrieval)
    follow_up = advisor.answer_follow_up(initial.session_id, "Is this safe for organic farming?")

    corn_class = "Corn_(maize)___Northern_Leaf_Blight"
    corn_retrieval = retriever.retrieve(
        "Corn Northern Leaf Blight symptoms and management", disease_class=corn_class, top_k=3
    )
    gap = advisor.start_diagnosis(corn_class, corn_retrieval)

    print(
        json.dumps(
            {
                "apple_initial": initial.to_dict(),
                "apple_follow_up": follow_up.to_dict(),
                "corn_gap": gap.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
