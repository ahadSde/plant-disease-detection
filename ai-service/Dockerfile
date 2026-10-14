# Python 3.11 is compatible with the unpinned PyTorch/FAISS requirements and
# matches the Python generation used by the project's Colab development runtime.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

COPY requirements.txt ./
# Install CPU-only PyTorch so this image does not pull CUDA libraries.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && pip install -r requirements.txt

# Download the exact embedding model while the image is built.  Runtime is
# offline for Hugging Face so retrieval never depends on Hub/network state.
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/opt/hf-cache')"

# Match SentenceTransformer's runtime cache lookup to the location populated
# above.  This is deliberately set after the model-download layer so code-only
# rebuilds retain the expensive dependency/model cache.
ENV SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache

COPY app.py ./
COPY models/ ./models/
COPY rag/ ./rag/
COPY llm/ ./llm/
COPY outputs/resnet50_best.pt ./outputs/resnet50_best.pt
COPY data/agri_docs/ ./data/agri_docs/

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
