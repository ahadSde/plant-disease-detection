# Verdant — Plant Disease Assistant

The Stage 5 web application connects the React interface, Spring Boot API,
PostgreSQL history, and the containerized Python AI service. Each uploaded image
creates a separate diagnosis and chat thread.

## Run the complete application

Docker Desktop must be running. Keep the existing root `.env` file private; it
must define `GOOGLE_API_KEY` for the Gemini advisory service. From this project
folder, run:

```bash
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173). The first build can take a
while because it builds the Java and frontend images. Stop the stack with
`Ctrl+C`; add `-d` to run it in the background and use `docker compose down` to
stop it. PostgreSQL data and uploaded diagnosis images persist in Docker
volumes.

## Stage 5 request flow

The browser creates a UUID in `localStorage` and sends it in `X-Session-Id` on
diagnosis and chat API requests. React sends a leaf image to Spring Boot;
Spring saves it in the uploads volume, calls the Python container's
`POST /diagnose`, and stores the prediction, advisory, and initial assistant
message in PostgreSQL. Follow-up text is scoped to that diagnosis and sent to
the Python `POST /follow-up` endpoint with the advisory session ID. Diagnosis
history reloads its own image and stored conversation. Images are returned by
the Spring `/images/{filename}` route; they are never stored as database blobs.

History is available only in the same browser on the same device. Clearing
browser data, changing browsers/devices, or using private browsing loses access
to that session's history. There is no login or account system.

## Run services individually for development

- Backend: `cd backend && mvn spring-boot:run` (expects PostgreSQL at
  `localhost:5432` and the AI service at `localhost:8000`; configure with the
  `SPRING_DATASOURCE_*`, `AI_SERVICE_URL`, and `UPLOAD_DIR` environment
  variables).
- Frontend: `cd frontend && npm install && npm run dev` (Vite proxies API and
  image requests to `localhost:8080`).
- The AI service's Docker instructions and Gemini key handling are in
  `ai-service/README.md`.

## Known model and knowledge-base limits

CNN metrics are from controlled PlantVillage test images; field performance
may be lower. The classifier always selects one of its 38 classes, including
for unfamiliar inputs. Below 70% model confidence, the interface displays an
uncertainty warning. RAG coverage is incomplete: when there is no verified
reference for a diagnosis, the interface surfaces that message and does not
present unrelated source material as grounded advice.
