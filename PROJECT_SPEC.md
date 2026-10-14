# Note: Sections 1 and 18 describe the project as of spec creation; `PROGRESS_LOG.md` is the source of truth for current implementation state.

# PROJECT_SPEC.md

## AI-Based Plant Disease Detection and Diagnostic Advisory System Using CNN and Large Language Models

This document consolidates everything discussed and decided for this project into a single technical specification. It is intended to give a coding agent (or any implementer) full context to begin building without needing to re-derive decisions already made. Nothing in this document is invented beyond what was explicitly discussed; open questions and unmade decisions are flagged explicitly in their own section.

---

## 1. Project Identity

- **Title:** AI-Based Plant Disease Detection and Diagnostic Advisory System Using CNN and Large Language Models
- **Domain:** Artificial Intelligence / Machine Learning (Deep Learning, Natural Language Processing)
- **Context:** MCA capstone/dissertation project (VIT, Dissertation-I / Internship-1, PAMCA698J), single-semester timeline (~5 months, project-only semester with no competing coursework)
- **Current status:** Planning and documentation stage complete (title/abstract approved by guide, Review-1 report and presentation delivered). **No implementation has started.** Stage 1 (data collection and preprocessing) has not begun. No code has been written for any module.

---

## 2. Problem Statement

Existing plant disease detection systems are largely limited to image classification: a leaf image is processed and assigned a disease category with a confidence score. This is insufficient on its own — farmers need to know what the disease means, its causes, and how to treat or prevent it, not just a label.

Separately, agricultural chatbots built on generic LLMs risk providing inaccurate or ungrounded advice because they are not tied to verified agricultural knowledge sources — a serious reliability concern when the advice affects real crop treatment decisions.

**The gap identified through literature review:** very few existing systems integrate (a) accurate visual disease classification, (b) knowledge retrieval grounded in verified agricultural sources, and (c) sustained interactive follow-up support, all within a single accessible platform. This project's contribution is combining all three.

---

## 3. Goals / Objectives (as finalized)

1. Develop a CNN-based plant disease classification model from leaf images.
2. Apply transfer learning using a pretrained CNN backbone to reduce training/compute requirements.
3. Build a Retrieval-Augmented Generation (RAG) pipeline retrieving from curated, verified agricultural reference documents.
4. Integrate an LLM-based advisory layer that uses the detected disease + retrieved context to generate explanations, remedies, and preventive suggestions.
5. Support interactive, conversational follow-up questions — the system must maintain context across a multi-turn conversation, not just answer once.
6. Deliver the system as an accessible, deployed end-to-end web application.
7. Evaluate the complete system: CNN classification performance, RAG retrieval relevance, LLM output quality/groundedness, and overall usability.

---

## 4. Scope

### In scope
- Image-based plant disease classification (CNN)
- Dataset preprocessing and augmentation
- Transfer learning on a pretrained backbone
- Curated agricultural knowledge base construction
- RAG-based retrieval pipeline
- LLM-based explanation and advisory generation, grounded in retrieved content
- Conversational follow-up support (multi-turn, context-preserving)
- Storage of user diagnosis history
- Web interface: image upload, diagnosis display, chat-style interaction
- Backend + database integration

### Out of scope (this phase — noted as potential future extensions)
- Real-time deployment on dedicated agricultural hardware
- Mobile-based field devices
- Multilingual voice interaction
- Large-scale production infrastructure

---

## 5. Functional Requirements

- The system shall accept a leaf image upload from the user.
- The system shall classify the uploaded image into a disease category with a confidence score.
- The system shall retrieve relevant reference content for the identified disease from the knowledge base.
- The system shall generate a natural-language explanation and remedy suggestion grounded in the retrieved content (not purely from the LLM's trained/parametric knowledge).
- The system shall allow the user to ask follow-up questions related to the diagnosis, with the system maintaining conversational context (disease + retrieved chunks) across turns. **This is a required part of scope, not optional polish** — the system must not be a one-shot, non-conversational report generator.
- The system shall store user diagnosis history for later retrieval.

## 6. Non-Functional Requirements

- **Performance:** Classification result should return within a few seconds of image upload.
- **Usability:** Interface simple enough for non-technical users (farmers) to use without training.
- **Reliability:** Advisory responses must remain grounded in verified reference material to minimize incorrect guidance.
- **Scalability:** Architecture should allow additional crops, diseases, or reference documents to be added without redesign.
- **Security:** User data and diagnosis history stored securely with appropriate access control.

---

## 7. System Architecture

Layered, microservice-oriented architecture with four components:

1. **React Frontend** — image upload, result display, chat interface for follow-up questions.
2. **Spring Boot Backend** — REST API, business logic, user data, diagnosis/chat history persistence via PostgreSQL. Calls the AI service internally over HTTP.
3. **PostgreSQL Database** — persistent storage for users, diagnoses, chat history.
4. **Python AI Service (FastAPI)** — hosts the three AI modules below, exposed as an internal REST service that the Spring Boot backend calls.

### Request flow
User uploads image (or sends follow-up message) via React frontend → Spring Boot backend receives request → backend calls Python AI service → AI service runs CNN classification (first turn) and/or RAG retrieval and/or LLM generation → response flows back through backend → frontend displays diagnosis / chat reply.

### The three AI modules (inside the Python AI service)

**Module 1 — CNN Classifier**
- Input: leaf image. Output: disease class + confidence score.
- Pretrained backbone (ResNet-50 or EfficientNet), adapted via transfer learning — not trained from scratch.
- Training environment: Google Colab (free GPU).

**Module 2 — RAG Knowledge Base**
- Curated agricultural documents (ICAR / TNAU advisories), chunked and embedded, stored in a vector database.
- Given a disease name/query, retrieves the most relevant chunks for grounding.
- **Important: RAG is not "trained."** No weight updates occur in this module. It is a configured pipeline: document ingestion → chunking → embedding (via a pretrained, off-the-shelf embedding model, not one trained by this project) → vector storage → similarity search at query time. Improvements come from tuning chunk size/overlap, embedding model choice, top-k retrieval count, and query formulation — not from a training loop.

**Module 3 — LLM Advisory Layer**
- Takes classified disease + retrieved chunks + (on follow-up turns) the user's question and prior conversation context.
- Generates explanation + remedy on the first turn, or a grounded conversational answer on follow-up turns.
- Must maintain conversational memory across turns — this is a hard requirement, not optional.
- Uses an existing LLM via API (not trained/fine-tuned by this project).

---

## 8. Technology Stack (finalized)

| Layer | Technology |
|---|---|
| CNN Classifier | Python, PyTorch, ResNet-50 or EfficientNet (transfer learning), trained on Google Colab |
| RAG — Embeddings | `sentence-transformers` (HuggingFace, open-source, free) |
| RAG — Vector DB | Chroma or FAISS (local, free, no external service dependency) |
| RAG — Document parsing | `PyPDF2` / `pdfplumber` |
| RAG/LLM — Orchestration | LangChain (or LlamaIndex) for chunking, retrieval, and conversation memory |
| LLM | Google Gemini API or Groq (free tier — avoid paid API credits) |
| AI service bridge | FastAPI (Python), exposing Modules 1–3 as an internal REST API |
| Backend | Spring Boot (Java) |
| Database | PostgreSQL |
| Frontend | React |

**Rationale for polyglot split:** Python owns AI/ML logic because that's where the relevant libraries live; Spring Boot owns product/business logic — deliberately chosen to (a) mirror a realistic industry pattern (ML service behind a Java/Spring backend) and (b) let the builder apply Spring Boot, which is being learned concurrently this semester. **Known risk, explicitly accepted:** Spring Boot is a less mature skill for the builder than the MERN stack; extra buffer time is planned for the web app module (Stage 5) for this reason, and the AI logic is kept stack-independent so a simpler interface could be substituted without losing AI work if time runs short.

---

## 9. Folder Structure

```
plant-disease-assistant/
├── ai-service/                    # Python - Modules 1, 2, 3
│   ├── app.py                     # FastAPI entrypoint
│   ├── models/
│   │   └── cnn_classifier.py      # Module 1: CNN inference
│   ├── rag/
│   │   ├── ingest.py              # Module 2: PDF chunking + embedding
│   │   └── retriever.py           # Module 2: retrieval logic
│   ├── llm/
│   │   └── advisor.py             # Module 3: LLM prompt + generation + conversation memory
│   ├── data/
│   │   ├── plantvillage/          # image dataset (not committed to git)
│   │   └── agri_docs/             # ICAR/TNAU PDFs
│   ├── requirements.txt
│   └── train_cnn.ipynb            # Colab notebook for training
│
├── backend/                       # Spring Boot - web backend
│   ├── src/main/java/.../
│   │   ├── controller/            # REST endpoints
│   │   ├── service/                # business logic, calls ai-service
│   │   ├── repository/            # PostgreSQL JPA repos
│   │   └── model/                  # entities (User, Diagnosis, ChatMessage, etc.)
│   ├── src/main/resources/
│   │   └── application.properties
│   └── pom.xml
│
├── frontend/                      # React - UI
│   ├── src/
│   │   ├── components/
│   │   │   ├── ImageUpload.jsx
│   │   │   ├── DiagnosisResult.jsx
│   │   │   └── ChatFollowUp.jsx
│   │   └── App.jsx
│   └── package.json
│
└── README.md
```

---

## 10. Data Model (from class diagram, as designed for Review-1)

**Persistent entities (Spring Boot / PostgreSQL side):**

- **User**: `id`, `name`, `email`, `passwordHash` — methods: `register()`, `login()`, `viewHistory()`
- **Diagnosis**: `id`, `userId`, `imageUrl`, `diseaseClass`, `confidence`, `explanation`, `remedy`, `createdAt` — methods: `createDiagnosis()`, `getSummary()`. One User has many Diagnoses (1..*).
- **ChatMessage**: `id`, `diagnosisId`, `sender`, `message`, `timestamp` — methods: `sendMessage()`. One Diagnosis has many ChatMessages (1..*), representing the follow-up conversation thread tied to that diagnosis.

**AI-service-side classes (conceptual, Python):**

- **CNNClassifier**: `modelPath` — methods: `preprocessImage()`, `classify(image)`
- **RAGRetriever**: `vectorStore` — methods: `embedQuery()`, `retrieveContext(query)`
- **LLMAdvisor**: `apiKey` — methods: `generateExplanation()`, `generateRemedy()`, `answerFollowUp()`
- **ReferenceDocument**: `id`, `title`, `source`, `filePath` — methods: `ingest()`, `chunkAndEmbed()`. RAGRetriever indexes ReferenceDocuments.

A Diagnosis depends on (uses) CNNClassifier, RAGRetriever, and LLMAdvisor to produce its result.

---

## 11. Use Cases (from use case diagram, as designed for Review-1)

**Actor: Farmer / User**
- Upload leaf image
- View disease classification result (includes: view classification result — <<include>>)
- View diagnosis explanation & remedy (includes: view classification result — <<include>>)
- Ask follow-up question
- View diagnosis history

**Actor: System Admin**
- Manage reference documents (the RAG knowledge base)
- Retrain / update CNN model

---

## 12. Build Order / Methodology (module-first, incremental — finalized approach)

The system must be built so that a working component exists at every stage — integration happens last, not in parallel with core logic development.

**Stage 1 — Data Collection and Preprocessing** *(not yet started)*
- Collect PlantVillage dataset (primary; optionally FieldPlant and/or PlantDoc for real-world robustness — see Section 14 on limitations).
- Curate ICAR / TNAU advisory documents (~15–20 documents, matched to the disease classes present in the chosen image dataset; quality/relevance over volume) for the RAG knowledge base.
- Image preprocessing: resizing to a fixed input size (e.g., 224×224 to match the CNN backbone), pixel normalization (typically using ImageNet mean/std since a pretrained backbone is used), consistent RGB color format, train/validation/test split (e.g., 70/15/15 or 80/10/10), label encoding of class folders into numeric labels.
- Data augmentation (training set only, never validation/test): random rotation, horizontal/vertical flip, random zoom/crop, brightness/contrast jitter, random shift/translation.
- Optional/nice-to-have, time permitting: class balancing (oversampling or class weights if PlantVillage classes are imbalanced), background/noise augmentation or blur simulation to improve real-world tolerance.
- Document preprocessing (separate pipeline, for RAG): text extraction from PDFs, cleaning (remove headers/footers/page numbers), chunking into passages (with tuning of chunk size/overlap), embedding generation per chunk before vector storage.

**Stage 2 — CNN Model Development**
- Fine-tune a pretrained backbone (ResNet-50 or EfficientNet) via transfer learning: freeze early general-purpose layers, replace and train the final classification layer(s) (and optionally unfreeze some later layers depending on dataset size).
- Training loop: forward pass → cross-entropy loss → backpropagation → weight update via an optimizer (e.g., Adam).
- Tune: learning rate, number of epochs (watch for overfitting via validation performance; consider early stopping), batch size.
- Evaluate on a held-out test set using accuracy, precision, recall, and F1-score (especially important if classes are imbalanced).

**Stage 3 — Knowledge Base and RAG Pipeline Development**
- Build and test the retrieval pipeline independently of the CNN and LLM: chunk documents, generate embeddings, store in vector DB, verify retrieval returns sensible results for a manually-typed disease name/query.

**Stage 4 — LLM Advisory Integration**
- Wire CNN output → RAG retrieval → LLM prompt → generated answer, end-to-end, including conversational memory for follow-up handling. At the end of this stage, the full "brain" of the system should work via script/notebook input-output, even without a UI.

**Stage 5 — Web Application Development**
- Build Spring Boot backend + PostgreSQL schema + React frontend around the already-working AI pipeline. Do not begin this stage before Modules 1–3 work end-to-end in raw form.

**Stage 6 — Testing and Evaluation**
- CNN: classification performance metrics.
- RAG: relevance of retrieved information.
- LLM output: relevance, clarity, and groundedness in retrieved content (i.e., does the generated explanation stay consistent with what was retrieved, without introducing unsupported claims).
- Full application: functionality, response time, usability, reliability.
- Testing should happen incrementally throughout development, not only at the end.

---

## 13. Datasets & Reference Material

**Image dataset:**
- **PlantVillage** (primary) — ~54,000 labeled leaf images, 14 crop species, 38 disease/healthy classes.
- **FieldPlant** (optional extension) — real-world field-condition images; addresses PlantVillage's lab-controlled-background limitation.
- **PlantDoc** (optional extension) — another real-world-condition dataset.

**Reference material for RAG grounding:**
- ICAR (Indian Council of Agricultural Research) publications and Krishi Vigyan Kendra (KVK) advisories.
- TNAU Agritech Portal extension bulletins (Tamil Nadu Agricultural University).
- FAO plant health guides (for internationally common diseases), if needed.
- Target: ~15–20 well-chosen documents covering the disease classes present in the image dataset.

---

## 14. Known Limitations (explicitly discussed — do not silently "fix" or hide these; they are accepted, documented constraints)

1. **Closed-set classification:** The CNN can only recognize plant/disease combinations present in its training data (PlantVillage's 38 classes). It has no mechanism to say "I don't know" — an out-of-distribution input (a plant/disease not in training data) will still produce a confident-looking but meaningless prediction.

2. **Lab-condition vs. real-world images:** PlantVillage images are captured in controlled conditions (clean backgrounds, consistent lighting, single centered leaf). Real-world farm photos (messy backgrounds, variable lighting, occlusion, phone camera artifacts) are out-of-distribution relative to this training data, and classification accuracy is expected to drop on such images unless the model is extended with a field-condition dataset (FieldPlant/PlantDoc) or heavier augmentation is applied. **This is a stated, accepted limitation for the current project scope — not a bug to silently patch.** If asked (e.g., during review), the honest framing is: "trained on PlantVillage (lab-condition data), so real-world accuracy may be lower; extending with a field-condition dataset is a planned improvement, not yet implemented."

3. **RAG groundedness is a mitigation, not a guarantee:** Grounding reduces but does not eliminate the risk of the LLM generating unsupported or slightly inaccurate content. The system is not claimed to be 100% reliable.

4. **CNN misclassification propagates downstream:** Since RAG retrieval is triggered by the CNN's predicted disease, a misclassification will cause the advisory layer to ground its answer in the wrong disease's information. The confidence score is exposed specifically so low-confidence predictions could be flagged rather than presented as certain (flagging behavior itself has not been designed in detail — see Open Questions).

---

## 15. Literature Survey Summary (context for design rationale, not implementation detail)

15 papers were reviewed, falling into three broad groups:
- **CNN/vision-only systems** — strong classification accuracy, but stop at a label with no advisory output.
- **LLM/chatbot-only agricultural systems** — conversational, but often not grounded in verified domain-specific sources.
- **Emerging RAG-driven systems** (a smaller, more recent group) — combine detection with retrieval-grounded generation, validating this project's direction.

**Identified gap (the project's core motivation):** very few reviewed systems combine accurate classification + RAG-grounded explanation + sustained interactive follow-up in one deployed, accessible platform.

(Full 15-paper reference list with merits/demerits exists in the Review-1 report and is not duplicated here, as it is documentation rather than a build requirement — available on request.)

---

## 16. Explicitly Out-of-Scope Technical Approaches (considered and rejected, with reasoning — for context, so they are not re-proposed without reason)

- **Fine-tuning the LLM directly on agricultural data**, instead of RAG: rejected because it requires a large labeled dataset and significant compute, "bakes in" knowledge that goes stale as new advisories are published, and loses the traceability-to-source that RAG provides.
- **Vision Transformers or YOLO** instead of a CNN: rejected — Vision Transformers need more data/compute than is practical for this timeline; YOLO is built for object detection/localization, whereas this task is whole-image classification, so a CNN classifier is the correct fit.
- **Fine-tuning the RAG embedding model** on agriculture-specific text: considered as a possible advanced extension but explicitly deprioritized as beyond capstone scope; an off-the-shelf pretrained embedding model is used instead, which is standard practice even in production RAG systems.

---

## 17. Open Questions / Not Yet Decided

These were raised in discussion but not finalized, and should not be assumed one way or another by an implementer without further input from the project owner:

- Exact behavior when CNN confidence is low (e.g., below what threshold, and what the system should display/do differently) has not been designed in detail.
- Exact chunk size/overlap, top-k retrieval count, and specific embedding model choice for RAG have not been finalized — these are meant to be tuned empirically during Stage 3, not pre-specified.
- Whether FieldPlant/PlantDoc will actually be incorporated (vs. remaining PlantVillage-only) depends on time available — not yet decided; currently framed as an optional extension.
- Exact list of ICAR/TNAU documents to curate for the knowledge base has not been selected yet — only the source types (ICAR, TNAU, optionally FAO) and target count (~15–20) have been agreed.
- Authentication/authorization is resolved: the implementation will use session/device ID tracking without login or authenticated accounts. See the corresponding decision in `PROGRESS_LOG.md` under “Decisions Made During Implementation.”
- Whether/how a paper will be submitted from this work (mentioned as a stretch goal, tied to IEEE conference venues similar to those in the literature survey) is undecided and depends on having real results first.

---

## 18. Project Timeline Context

- Semester is project-only (~5 months / ~18–20 usable weeks after accounting for breaks), no competing coursework or exams.
- Guide (Dr. Vijayan E) provides minimal day-to-day oversight — the builder is expected to self-direct, with periodic approval check-ins on major decisions.
- Review-1 (covering everything through Section 7/proposed architecture) has been completed and presented.
- Next milestone: begin Stage 1 (data collection and preprocessing) — not yet started as of this document.
