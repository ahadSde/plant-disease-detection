# AI service Docker runtime

This container runs the completed CNN, FAISS retriever, and Gemini advisor on
Linux. It contains the ResNet-50 checkpoint, curated document processing
artifacts, document catalog, FAISS index, and the Python service source. The
54k-image training corpus is deliberately excluded because inference does not
need it.

## Build

Run from `ai-service/`:

```bash
docker build -t plant-disease-ai-service .
```

The build downloads and caches `all-MiniLM-L6-v2`. At runtime Hugging Face is
set offline, so query embedding uses the baked cache rather than the host cache
or Hub network.

## Run

Set the key only in your shell, then pass it at runtime. Do not place it in the
Dockerfile or commit it to a file.

```bash
export GOOGLE_API_KEY='your-Gemini-key'
docker run --rm --name plant-disease-ai-service -p 8000:8000 \
  -e GOOGLE_API_KEY \
  plant-disease-ai-service
```

In a second terminal, confirm the service is reachable:

```bash
curl --fail http://localhost:8000/health
```

## End-to-end smoke test

Use the existing Apple Scab image as a host-side fixture (the full dataset is
not placed in the image):

```bash
curl --fail -X POST http://localhost:8000/diagnose \
  -F "image=@data/plantvillage/color/Apple___Apple_scab/14c623e5-051c-42f6-9e4f-f7a93e6a723c___FREC_Scab 2965.JPG" \
  -o /tmp/plant-disease-diagnosis.json
python smoke_test.py /tmp/plant-disease-diagnosis.json
```

The check asserts all three components: a non-empty CNN prediction, an
`ok` FAISS retrieval with source chunks, and a grounded Gemini answer with
sources. It requires an active Gemini key because that call is intentionally
live. The API also exposes `POST /follow-up` with JSON
`{"session_id": "...", "question": "..."}` for the already-created advisory
session.
