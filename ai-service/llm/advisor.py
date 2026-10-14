"""Grounded, multi-turn advisory generation for Stage 4."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI


DEFAULT_MODEL = "gemini-3.6-flash"


@dataclass
class AdvisoryResponse:
    session_id: str
    status: str
    disease_class: str
    answer: str
    sources: list[dict[str, Any]]
    finish_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class _Conversation:
    disease_class: str
    source_chunks: list[dict[str, Any]]
    history: InMemoryChatMessageHistory


class LLMAdvisor:
    """Gemini-backed advisory layer constrained to retrieved reference chunks."""

    def __init__(self, model_name: str = DEFAULT_MODEL, api_key: str | None = None) -> None:
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self._llm: ChatGoogleGenerativeAI | None = None
        self._conversations: dict[str, _Conversation] = {}

    def _chat_model(self) -> ChatGoogleGenerativeAI:
        if not self.api_key:
            raise RuntimeError("Set GOOGLE_API_KEY or GEMINI_API_KEY to call the Gemini API.")
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.1,
                max_output_tokens=1400,
            )
        return self._llm

    @staticmethod
    def _source_summary(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {"chunk_id": chunk["chunk_id"], "source_file": chunk["source_file"], "score": chunk.get("score")}
            for chunk in chunks
        ]

    @staticmethod
    def _context(chunks: list[dict[str, Any]]) -> str:
        return "\n\n".join(
            f"[Source: {chunk['chunk_id']} | {chunk['source_file']}]\n{chunk['text']}"
            for chunk in chunks
        )

    @staticmethod
    def _system_prompt(disease_class: str, chunks: list[dict[str, Any]]) -> str:
        return f"""You are a plant-disease advisory assistant. The diagnosed PlantVillage class is:
{disease_class}

Use only the verified SOURCE CONTEXT below. Do not add pesticide, dosage,
organic-farming, safety, symptom, prevention, or treatment claims unsupported
by it. If the context does not answer a question, say that the verified
reference context does not provide that information. Do not use general
knowledge to fill a gap.

For the initial answer, give a concise explanation and remedy/management
suggestion. For follow-ups, remain within this diagnosis and the same context.
For each follow-up, identify and use the passage(s) that directly address the
question. If none do, say that the verified reference context does not cover
it; do not infer an answer from unrelated passages. Cite every substantive
claim using a chunk ID in square brackets.

SOURCE CONTEXT:
{LLMAdvisor._context(chunks)}"""

    @staticmethod
    def _no_reference_answer(disease_class: str) -> str:
        return (
            f"No verified reference document is currently available for {disease_class}. "
            "I cannot provide a grounded explanation or remedy for this diagnosis yet. "
            "Please consult a qualified local agricultural extension service while an appropriate "
            "reference is curated for the knowledge base."
        )

    @staticmethod
    def _content_as_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        return str(content)

    def _generate(self, messages: list[Any]) -> tuple[str, str | None]:
        """Invoke Gemini and preserve its finish reason for truncation checks."""
        model = self._chat_model()
        try:
            response = model.invoke(messages)
        except Exception as error:
            # Gemini can transiently return 429 (quota throttling) or 503
            # (service unavailable). Retry once; do not retry permanent errors.
            error_text = f"{type(error).__name__} {error}".upper()
            status = getattr(error, "status_code", None)
            code = getattr(error, "code", None)
            if callable(code):
                try:
                    code = code()
                except Exception:
                    code = None
            code_text = str(code).upper()
            retryable = (
                status in (429, 503)
                or "429" in error_text
                or "503" in error_text
                or "RESOURCE_EXHAUSTED" in code_text
                or "UNAVAILABLE" in code_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "UNAVAILABLE" in error_text
            )
            if not retryable:
                raise
            time.sleep(1)
            response = model.invoke(messages)
        metadata = getattr(response, "response_metadata", {}) or {}
        finish_reason = metadata.get("finish_reason") or metadata.get("finishReason")
        return self._content_as_text(response.content), finish_reason

    def start_diagnosis(self, disease_class: str, retrieval_result: Any) -> AdvisoryResponse:
        """Generate the initial grounded answer and create a conversation session."""
        session_id = str(uuid.uuid4())
        chunks = list(getattr(retrieval_result, "matches", []))
        status = getattr(retrieval_result, "status", "below_similarity_threshold")
        if status != "ok" or not chunks:
            return AdvisoryResponse(
                session_id,
                "no_verified_reference",
                disease_class,
                self._no_reference_answer(disease_class),
                [],
                "not_applicable",
            )

        history = InMemoryChatMessageHistory()
        initial_request = "Provide the initial explanation and remedy/management suggestion for this diagnosis."
        answer, finish_reason = self._generate(
            [SystemMessage(self._system_prompt(disease_class, chunks)), HumanMessage(initial_request)]
        )
        history.add_user_message(initial_request)
        history.add_ai_message(answer)
        self._conversations[session_id] = _Conversation(disease_class, chunks, history)
        return AdvisoryResponse(session_id, "ok", disease_class, answer, self._source_summary(chunks), finish_reason)

    def answer_follow_up(self, session_id: str, question: str) -> AdvisoryResponse:
        """Answer with the original diagnosis, RAG context, and prior turns."""
        if session_id not in self._conversations:
            raise KeyError("Unknown advisory session. Start a diagnosis before asking follow-ups.")
        conversation = self._conversations[session_id]
        messages = [SystemMessage(self._system_prompt(conversation.disease_class, conversation.source_chunks))]
        messages.extend(conversation.history.messages)
        messages.append(HumanMessage(question))
        answer, finish_reason = self._generate(messages)
        conversation.history.add_user_message(question)
        conversation.history.add_ai_message(answer)
        return AdvisoryResponse(
            session_id,
            "ok",
            conversation.disease_class,
            answer,
            self._source_summary(conversation.source_chunks),
            finish_reason,
        )
