"""Offline contract tests for class coverage and retrieved context."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from llm.advisor import LLMAdvisor
from rag.retriever import RAGRetriever


class RetrievalContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.retriever = RAGRetriever()
        cls.covered_classes = sorted(
            {disease_class for entry in cls.retriever.catalog.values() for disease_class in entry["coverage"]}
        )

    def test_each_covered_class_returns_only_its_registered_document(self) -> None:
        total_chunks = 0
        for disease_class in self.covered_classes:
            result = self.retriever.retrieve(
                f"{disease_class.replace('___', ' ').replace('_', ' ')} symptoms and management",
                disease_class=disease_class,
                top_k=3,
            )
            self.assertEqual("ok", result.status, disease_class)
            self.assertTrue(result.matches, disease_class)
            allowed = {
                filename
                for filename, entry in self.retriever.catalog.items()
                if disease_class in entry["coverage"]
            }
            returned = {chunk["source_file"] for chunk in result.matches}
            self.assertLessEqual(returned, allowed, disease_class)
            text = " ".join(chunk["text"].lower() for chunk in result.matches)
            self.assertIn("symptom", text, disease_class)
            self.assertIn("management", text, disease_class)
            total_chunks += len(result.matches)

        self.assertEqual(11, len(self.covered_classes))
        self.assertEqual(61, total_chunks)
        self.assertIsNone(self.retriever.model, "exact class lookup should not embed the query")

    def test_question_specific_target_spot_and_apple_context_is_present(self) -> None:
        target = self.retriever.retrieve(
            "What is the impact of Tomato Target Spot?",
            disease_class="Tomato___Target_Spot",
        )
        target_chunks = {chunk["chunk_id"]: chunk["text"].lower() for chunk in target.matches}
        self.assertIn("tomato_target_spot-0004", target_chunks)
        self.assertIn("impact", target_chunks["tomato_target_spot-0004"])

        fungicide = self.retriever.retrieve(
            "Which fungicides are listed for Tomato Target Spot?",
            disease_class="Tomato___Target_Spot",
        )
        fungicide_chunks = {chunk["chunk_id"]: chunk["text"].lower() for chunk in fungicide.matches}
        self.assertIn("tomato_target_spot-0010", fungicide_chunks)
        self.assertIn("chlorothalonil", fungicide_chunks["tomato_target_spot-0010"])

        apple = self.retriever.retrieve(
            "Apple Scab symptoms and management",
            disease_class="Apple___Apple_scab",
        )
        self.assertIn("apple_scab_tnau-0002", {chunk["chunk_id"] for chunk in apple.matches})

    def test_uncovered_corn_has_no_context_and_does_not_embed(self) -> None:
        result = self.retriever.retrieve(
            "Corn Northern Leaf Blight symptoms and management",
            disease_class="Corn_(maize)___Northern_Leaf_Blight",
        )
        self.assertEqual("no_reference_document", result.status)
        self.assertEqual([], result.matches)
        self.assertEqual([], result.diagnostic_candidates)
        self.assertIsNone(self.retriever.model)


class _FakeChatModel:
    def __init__(self) -> None:
        self.calls: list[list[object]] = []

    def invoke(self, messages: list[object]) -> SimpleNamespace:
        self.calls.append(messages)
        return SimpleNamespace(content="Use the cited management guidance [apple-0001].", response_metadata={"finish_reason": "STOP"})


class _Transient503Model(_FakeChatModel):
    def invoke(self, messages: list[object]) -> SimpleNamespace:
        self.calls.append(messages)
        if len(self.calls) == 1:
            error = RuntimeError("503 UNAVAILABLE")
            error.status_code = 503  # type: ignore[attr-defined]
            raise error
        return SimpleNamespace(content="Recovered after retry.", response_metadata={"finish_reason": "STOP"})


class AdvisorContractTest(unittest.TestCase):
    def test_transient_503_gets_one_application_retry(self) -> None:
        advisor = LLMAdvisor(api_key="offline-test-key")
        fake = _Transient503Model()
        advisor._llm = fake  # type: ignore[assignment]

        with patch("llm.advisor.time.sleep") as sleep:
            answer, finish_reason = advisor._generate([HumanMessage("test")])

        self.assertEqual("Recovered after retry.", answer)
        self.assertEqual("STOP", finish_reason)
        self.assertEqual(2, len(fake.calls))
        sleep.assert_called_once_with(1)

    def test_follow_up_keeps_original_context_history_and_grounding_rules(self) -> None:
        chunks = [{
            "chunk_id": "apple-0001",
            "source_file": "apple_scab_tnau.pdf",
            "text": "Management: remove infected leaves and follow the cited local guidance.",
        }]
        retrieval = SimpleNamespace(status="ok", matches=chunks)
        advisor = LLMAdvisor(api_key="offline-test-key")
        fake = _FakeChatModel()
        advisor._llm = fake  # type: ignore[assignment]

        initial = advisor.start_diagnosis("Apple___Apple_scab", retrieval)
        follow_up = advisor.answer_follow_up(initial.session_id, "What about next season?")

        self.assertEqual(2, len(fake.calls))
        self.assertEqual(initial.session_id, follow_up.session_id)
        self.assertEqual("ok", follow_up.status)
        self.assertIn("apple-0001", follow_up.sources[0]["chunk_id"])
        follow_up_messages = fake.calls[1]
        system_prompt = next(message.content for message in follow_up_messages if isinstance(message, SystemMessage))
        self.assertIn("[Source: apple-0001 | apple_scab_tnau.pdf]", system_prompt)
        self.assertIn("do not infer an answer from unrelated passages", system_prompt.lower())
        self.assertTrue(any(isinstance(message, HumanMessage) and "Provide the initial explanation" in message.content for message in follow_up_messages))
        self.assertTrue(any(isinstance(message, AIMessage) and "[apple-0001]" in message.content for message in follow_up_messages))
        self.assertTrue(any(isinstance(message, HumanMessage) and message.content == "What about next season?" for message in follow_up_messages))

    def test_no_reference_response_skips_model_invocation(self) -> None:
        advisor = LLMAdvisor(api_key="offline-test-key")
        fake = _FakeChatModel()
        advisor._llm = fake  # type: ignore[assignment]

        result = advisor.start_diagnosis(
            "Corn_(maize)___Northern_Leaf_Blight",
            SimpleNamespace(status="no_reference_document", matches=[]),
        )

        self.assertEqual("no_verified_reference", result.status)
        self.assertEqual([], result.sources)
        self.assertIn("No verified reference document", result.answer)
        self.assertEqual([], fake.calls)


if __name__ == "__main__":
    unittest.main()
