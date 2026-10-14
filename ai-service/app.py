"""Container-facing FastAPI bridge for the completed AI modules.

This service is intentionally limited to the AI boundary.  Spring Boot, the
database, and the React application remain Stage 5 work.
"""

from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from llm.advisor import LLMAdvisor
from models.cnn_classifier import CNNClassifier
from rag.retriever import RAGRetriever


app = FastAPI(title="Plant Disease AI Service", version="1.0.0")
classifier = CNNClassifier()
retriever = RAGRetriever(threshold=0.40)
advisor = LLMAdvisor()


class FollowUpRequest(BaseModel):
    session_id: str
    question: str


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service process is reachable without making network calls."""
    return {"status": "ok"}


@app.post("/diagnose")
async def diagnose(image: UploadFile = File(...)) -> dict[str, object]:
    """Run the CNN → coverage-gated RAG → grounded Gemini advisory flow."""
    try:
        prediction = classifier.predict_bytes(await image.read())
        query = prediction.disease_class.replace("_", " ") + " symptoms and management"
        retrieval = retriever.retrieve(query, disease_class=prediction.disease_class, top_k=3)
        advisory = advisor.start_diagnosis(prediction.disease_class, retrieval)
        return {
            "prediction": prediction.to_dict(),
            "retrieval": retrieval.to_dict(),
            "advisory": advisory.to_dict(),
        }
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=f"Unable to process image: {error}") from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/follow-up")
def follow_up(request: FollowUpRequest) -> dict[str, object]:
    """Continue a grounded advisory conversation created by /diagnose."""
    try:
        return advisor.answer_follow_up(request.session_id, request.question).to_dict()
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
