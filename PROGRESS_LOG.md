# PROGRESS_LOG.md

**Last updated:** 2026-10-14 by Codex — Stage 6 baseline evaluation started

This file tracks the *actual* implementation state of the project, separate from `PROJECT_SPEC.md` (which stays static as the design contract). Whenever a coding agent picks up this project — whether continuing a session or starting fresh — it should read this file first to know what is really done, what was decided along the way, and what to do next. Update this file at the end of every work session, even if a stage isn't finished yet.

---

## Current Stage

**Stage 6 in progress — baseline evaluation, automated regression tests, and browser checks.**

Stages 1–5 and AI-service Docker containerization are complete. Stage 6 has
started with the persisted CNN metrics, prior v2.6 RAG relevance audit, six
offline AI tests, three backend controller tests, and fresh browser-path
no-reference checks. A fresh
positive-reference Gemini quality evaluation remains pending because Gemini
returned HTTP 503 during the recent live test.

## Stage 3 RAG Cleanup and Re-ingestion — 2026-10-09

Completed the requested ingestion and retrieval-only cleanup. `rag/ingest.py`
now uses `pdfplumber` positional extraction to repair extractor-induced spaces
inside words (for example, `T arget spot` → `Target spot` and `Corynespor a`
→ `Corynespora`), strips photo-caption blocks, page navigation/headers/footers,
URLs, timestamps, credits and copyright boilerplate, and retains substantive
symptom, spread, impact, detection and management text. Chunking remains at
**800 characters with 120-character overlap**. It packs complete sentences
within section boundaries; the Target Spot “Impact” paragraph is now its own
chunk, and the “During growth” management advice is kept together through its
final sentence. A short cultural-control introduction is joined to the next
management chunk instead of becoming a heading-only retrieval vector. The
largest final chunk is 820 characters because a complete sentence is kept
intact rather than split; other chunks are at or below 800.

The manifest now carries `processing_version: 2.6` at both corpus and document
level. Ingestion skips a file only when source hash, processing version, chunk
size and overlap all match. The indexer also checks processing version, so a
cleaner/chunker change re-embeds unchanged PDFs. A repeat v2.6 ingestion kept
all 13 files; a repeat index build reported `added_chunks: 0`,
`updated_documents: 0`, `skipped_documents: 13`, `total_chunks: 211`. The v2.6
conversion reprocessed all 13 PDFs and created all 211 vectors in the Linux
Docker runtime, avoiding the known macOS inference segfault. The processed
corpus and FAISS index in the project are now v2.6 / **13 documents, 211
chunks**. The existing Docker image was used as a disposable Linux runtime;
the image and Compose stack were not rebuilt or redeployed.

“Junk” below means a complete old chunk containing no useful disease or
management information (only captions, navigation, credits, references, or
page-footer boilerplate). Mixed chunks that contained substantive material
were not counted as junk even if they also had footer noise. Manual whole-chunk
audit found **12 such chunks before and zero after**:

| Document | Chunks before | Chunks after | Junk before | Junk after |
| --- | ---: | ---: | ---: | ---: |
| `agriculture_diseases_tnau.pdf` | 117 | 144 | 0 | 0 |
| `apple_scab_tnau.pdf` | 3 | 2 | 0 | 0 |
| `citrus_greening_tnau.pdf` | 3 | 3 | 1 | 0 |
| `potato_early_blight_tnau.pdf` | 4 | 4 | 1 | 0 |
| `tomato_early_blight_tnau.pdf` | 3 | 4 | 1 | 0 |
| `tomato_fruit_canker_tnau.pdf` | 3 | 6 | 1 | 0 |
| `tomato_late_blight_tnau.pdf` | 3 | 9 | 0 | 0 |
| `tomato_leaf_curl_tnau.pdf` | 3 | 4 | 1 | 0 |
| `tomato_leaf_mold.pdf` | 9 | 9 | 2 | 0 |
| `tomato_mosaic_virus.pdf` | 5 | 4 | 1 | 0 |
| `tomato_septoria_leaf_spot_tnau.pdf` | 3 | 5 | 1 | 0 |
| `tomato_spider_mites.pdf` | 6 | 7 | 0 | 0 |
| `tomato_target_spot.pdf` | 9 | 10 | 3 | 0 |
| **Total** | **171** | **211** | **12** | **0** |

The cleaned chunk text was inspected in `data/agri_docs/processed/` for
`tomato_target_spot.jsonl` and `apple_scab_tnau.jsonl`. Target Spot now has a
standalone Impact chunk (`tomato_target_spot-0004`) and complete “During
growth” advice (`tomato_target_spot-0007`). The former caption-only chunk
0001 and footer/credit chunks 0008–0009 are gone. Apple Scab has two
substantive chunks (symptoms and management) and no footer-only chunk.

### v2.6 retrieval calibration (Linux/Docker)

Calibration used `all-MiniLM-L6-v2`, cosine threshold **0.40**, top 3, and
class-specific exact-coverage filtering. Every returned chunk below is from
that class’s registered reference. “Preview” is the first 150 characters of
the returned chunk.

| Class | Returned chunk | Score | Preview |
| --- | --- | ---: | --- |
| Apple Scab | `apple_scab_tnau-0001` | 0.543704 | Symptoms: Horticultural crops :: Fruits:: Apple Scab: Venturia inaequalis Symptom appears on leaves and fruits. On lower side of the leaf lesion appea |
| Citrus Greening | `citrus_greening_tnau-0002` | 0.648389 | Symptoms: Many twigs become upright and produce smaller leaves. Fruits small, lopsided with curved columella. The side exposed to direct sunlight deve |
| Citrus Greening | `citrus_greening_tnau-0001` | 0.629333 | Symptoms: Horticultural crops :: Fruits:: Citrus Greening : Liberobactor asiaticum ( Phloem limited bacteria) This disease affects almost all citrus v |
| Potato Early Blight | `potato_early_blight_tnau-0001` | 0.633849 | Symptom: Horticultural crops :: Vegetables:: Potato Early blight: Alternaria solani It is present in both hills & plains. Brown-black necrotic spot-an |
| Potato Early Blight | `potato_early_blight_tnau-0002` | 0.498221 | Identification of pathogen - Mode of spread and survival: The conidia and the mycelium in the soil or in the debris of the affected plants can remain |
| Tomato Early Blight | `tomato_early_blight_tnau-0001` | 0.563118 | Horticultural crops :: Vegetables:: Tomato Early Blight: Alternaria solani Field Diagnostic Symptoms Brown spots with concentric rings in a bull's eye |
| Tomato Late Blight | `tomato_late_blight_tnau-0001` | 0.587539 | Symptoms: Horticultural crops :: Vegetables:: Tomato Late blight: Phytophthora infestans Water-soaked black lesions on leaves and stems Lesions expand |
| Tomato Yellow Leaf Curl Virus | `tomato_leaf_curl_tnau-0001` | 0.736471 | Horticultural crops :: Vegetables:: Tomato Leaf curl : Tomato leaf curl virus Field Diagnostic Symptoms Severe stunting of plants Downward rolling and |
| Tomato Septoria Leaf Spot | `tomato_septoria_leaf_spot_tnau-0001` | 0.688705 | Symptoms: Horticultural crops :: Vegetables:: Tomato Septoria Leaf Spot:Septoria lycopersici Small, round to irregular spots with grey centre and dark |
| Tomato Target Spot | `tomato_target_spot-0001` | 0.736127 | Symptoms & Life Cycle: Tomato target spot (163) Target spot, leaf spot Corynespora cassiicola Widespread. In tropical countries. Asia, Africa, North, |
| Tomato Target Spot | `tomato_target_spot-0002` | 0.498825 | Symptoms & Life Cycle: Some of the spots enlarge up to 10 mm and show characteristics rings, hence the name of 'target spot' (larger spots Photos 1&2) |
| Tomato Target Spot | `tomato_target_spot-0004` | 0.496267 | Impact: The fungus causes plants to lose their leaves; it is a major disease. If infection occurs before the fruit has developed, yields are low. This |
| Tomato Spider Mites | `tomato_spider_mites-0005` | 0.559482 | GENERAL MANAGEMENT: Keep plants healthy, especially during times of drought. Stressed plants are more susceptible to spider mite damage. Use a strong |
| Tomato Spider Mites | `tomato_spider_mites-0006` | 0.519896 | GENERAL MANAGEMENT: The spray must come into contact with the mites, so thoroughly spray the tops and bottoms of leaves. Spray at night to reduce risk |
| Tomato Spider Mites | `tomato_spider_mites-0004` | 0.493443 | SCOUTING: Monitor for injury symptoms (leaf stippling) during hot, dry conditions. Check the undersides of leaves for tiny black specks of debris and |
| Tomato Mosaic Virus | `tomato_mosaic_virus-0001` | 0.709064 | BIOLOGY: Foliar Symptoms on Tobacco Tomato Eggplant Pepper Tobacco Mosaic Virus (TMV) and Tomato Mosaic Virus (ToMV) are Tobamoviruses spread by seed, |
| Tomato Mosaic Virus | `tomato_mosaic_virus-0003` | 0.580348 | GENERAL MANAGEMENT: TMV and ToMV are widespread in Utah tomato production and can survive for up to 50 years in plant debris and for weeks to months o |
| Tomato Mosaic Virus | `tomato_mosaic_virus-0002` | 0.507735 | SYMPTOMS: A wide range of symptoms include abnormally shaped fruit, fruit lesions, reduced fruit size, distorted growing points, abnormal color (often |
| Tomato Leaf Mold | `tomato_leaf_mold-0004` | 0.687880 | Detection & inspection: Look for the yellow spots and rapidly developing irregular patches on the upper surfaces of the lower leaves, with brown to gr |
| Tomato Leaf Mold | `tomato_leaf_mold-0001` | 0.686985 | Symptoms & Life Cycle: Pacific Pests, Pathogens & Weeds - Fact Sheets Tomato leaf mould (076) Tomato leaf mould Passalora fulva (previously known as F |
| Tomato Leaf Mold | `tomato_leaf_mold-0003` | 0.614033 | Impact: The fungus causes a serious disease in cooler, wetter areas. The loss of leaves, from the bottom of the plant upwards, is rapid. Yield reducti |

The lowest retained score in this calibration was **0.493443** (spider-mite
scouting), 0.093443 above the 0.40 cutoff. Keep **0.40**; these calibration
results provide no evidence to raise it. The explicit query `impact of Tomato
Target Spot` returned `tomato_target_spot-0001` at 0.627494 and the dedicated
Impact paragraph `tomato_target_spot-0004` at 0.487201 (rank 2).

The Corn Northern Leaf Blight query returned `no_reference_document` with no
eligible matches. Its broad-document diagnostics were
`agriculture_diseases_tnau-0060` (0.578033), `-0128` (0.554132), and `-0113`
(0.549888); these were blocked by exact-coverage gating. All **27 of 38**
PlantVillage classes without an exact catalog entry returned
`no_reference_document`, including Apple Black rot/Cedar apple rust/healthy,
Blueberry healthy, Cherry Powdery mildew/healthy, Corn Cercospora leaf spot,
Common rust, Northern Leaf Blight/healthy, Grape Black rot/Esca/Leaf blight/
healthy, Peach Bacterial spot/healthy, Bell pepper Bacterial spot/healthy,
Potato Late blight/healthy, Raspberry healthy, Soybean healthy, Squash Powdery
mildew, Strawberry Leaf scorch/healthy, Tomato Bacterial spot/healthy. No
Gemini calls, Spring/React changes, image rebuild, or Compose redeployment were
made for this work.

These are diagnostic raw candidates only; none was returned as a match:

| Candidate chunk | Score | Preview |
| --- | ---: | --- |
| `agriculture_diseases_tnau-0060` | 0.578033 | Symptoms: Leaf spots are brown and circular with small to large light grey centres and dark brown margins or dark black irregular spots with concentri |
| `agriculture_diseases_tnau-0128` | 0.554132 | Management : Management: Spraying with Mancozeb 0.2% (or) Carbendazim 0.1% 3. Leaf blight : Colletotrichum crossandra Symptoms :The symptoms of leaves |
| `agriculture_diseases_tnau-0113` | 0.549888 | Management: Buds and twig blight by Phomopsis gulabia from Uttar Pradesh has also been reported. DISEASES OF JASMINE Leaf spots: Alternaria leaf bligh |

## Stage 3 Index Extension — 2026-10-04

Added four exact-coverage references incrementally: `tomato_target_spot.pdf`
and `tomato_leaf_mold.pdf` from the Lucid Apps Pest & Disease Image Library,
and `tomato_spider_mites.pdf` and `tomato_mosaic_virus.pdf` from Utah State
University Extension. These are credible non-TNAU source families and are
identified as such in `rag/document_catalog.json`; the original nine TNAU
documents were not reprocessed. Ingestion reported nine unchanged documents
retained and wrote chunks only for the four new PDFs (29 chunks total). The
index build added 29 chunks, updated zero documents, skipped nine documents,
and now contains **13 documents / 171 chunks**.

At the existing `all-MiniLM-L6-v2` cosine threshold **0.40**, calibration
queries returned only their exact registered source in eligible matches:

| Class | Query | Returned source and useful chunk score(s) |
| --- | --- | --- |
| Tomato Target Spot | `Tomato Target Spot symptoms and management` | `tomato_target_spot.pdf`: chunk 0005 **0.653000** (substantive); top match chunk 0009 0.676369 is mostly footer/URL text |
| Tomato Spider mites | `Tomato Spider mites Two-spotted spider mite symptoms and management` | `tomato_spider_mites.pdf`: chunk 0002 **0.635309**; 0001 0.597534; 0003 0.596532 |
| Tomato mosaic virus | `Tomato Tomato mosaic virus symptoms and management` | `tomato_mosaic_virus.pdf`: chunk 0002 **0.747549**; 0003 0.672431; 0001 0.551072 |
| Tomato Leaf Mold | `Tomato Leaf Mold symptoms and management` | `tomato_leaf_mold.pdf`: chunk 0004 **0.699671**; 0005 0.632875; 0003 0.611970 |

The Target Spot raw diagnostic candidates also contained a high-scoring broad
TNAU chunk, but the exact-coverage guard excluded it from eligible matches.
The rebuilt Docker image contains all 13 catalog entries and 171 indexed
chunks. A web-facing Tomato Target Spot upload returned HTTP 200, predicted the
class at 99.95%, retrieved `tomato_target_spot.pdf`, and produced grounded
Gemini management guidance citing substantive chunk `tomato_target_spot-0005`.
The running AI service, Spring backend, and React frontend were recreated on
the rebuilt image. Stage 6 was not started.

---

## Latest Model Update — 2026-10-04

The owner retrained ResNet-50 on the merged **55,914-image, 38-class** dataset
and replaced the three files under `ai-service/outputs/`. The checkpoint is
**94,665,315 bytes**; the accompanying evaluation and history JSON files are
**6,025** and **2,387 bytes**. The current Dockerfile copies
`outputs/resnet50_best.pt` into the image. The rebuilt image's checkpoint was
verified byte-for-byte against the local file (SHA-256
`49a072f1ef1759e955c85a322b444d2bd251053933b84fdb3a7e7109b3030057`).

### Empirical lab-to-field generalization gap

The supplied `evaluation_metrics.json` measures **97.95%** test accuracy for
the ten tomato classes (support **2,975**, mixed PlantVillage lab and Mendeley
field images) and **99.65%** for the other 28 classes (support **5,445**,
PlantVillage lab-only): a **1.70 percentage-point** gap in the artifact's
unrounded values. This is direct empirical confirmation of the lab-to-field
generalization limitation already disclosed in `PROJECT_SPEC.md` Section 14.
The final report should cite this as measured evidence, not only as a caveat.

The metric artifact records overall accuracy **99.05%**, macro precision
**98.69%**, macro recall **98.94%**, and macro F1 **98.81%** (rounded to two
decimal places). These differ slightly from the figures supplied with the
retraining report (99.00%, 98.67%, 98.94%, 98.79%; tomato 97.82%, other
99.65%). Likewise, `training_history.json` records the best epoch as 8 with
validation loss **0.03248** and accuracy **98.96%**, rather than 0.0311 and
98.98%. The history contains epochs 1–11; epochs 9–11 fail to improve on epoch
8, consistent with patience-3 early stopping after the three later epochs. The
reported 11-epoch run and epoch-8 best-checkpoint selection are consistent
with the history and notebook save-on-best-validation-loss behavior, but the
checkpoint itself does not store its epoch. Until reconciled, use the JSON
artifacts as the reproducible metric source and preserve this discrepancy in
the final report notes.

Weights were recomputed from the regenerated `summary.json` training counts
using `N / (C × n_class)`; the new weight range is **0.2671–9.7128**. The
previous Stage 2 weights were not reused.

---

## Completed

- Created the Section 9 project structure: `ai-service/`, `backend/`, and
  `frontend/`, including every specified subfolder and placeholder file.
- Added `ai-service/download_plantvillage.py`, which downloads the public
  PlantVillage archive and organizes its RGB class folders at
  `ai-service/data/plantvillage/raw/`.
- Added `ai-service/preprocess_images.py`, which validates readable RGB images,
  creates deterministic stratified train/validation/test metadata, encodes
  labels, writes class/split summaries, and creates resized plus training-only
  augmentation previews.
- Implemented 224×224 ImageNet normalization and training-only random resized
  crop, rotation, horizontal/vertical flip, translation, brightness, and
  contrast augmentation using PyTorch/torchvision.
- Added `ai-service/rag/ingest.py`, a PDF-ready local document pipeline using
  PyPDF2 for extraction, text cleaning, repeated header/footer removal, and
  configurable chunking. It deliberately performs no embedding/vector storage,
  which belongs to Stage 3. No advisory PDFs were downloaded or fabricated.
- Added Stage 1 dependencies in `ai-service/requirements.txt` and verified the
  preprocessing transforms output 3×224×224 tensors for both validation and
  training paths.
- Verified the supplied standard `data/plantvillage/color/` layout: **38 class
  folders** and **54,305 RGB image files**. The separate grayscale directory is
  intentionally excluded from this Stage 1 pipeline.
- Ran the full image preprocessing pipeline successfully. It found no unreadable
  images and produced `metadata/splits.csv`, `metadata/class_to_index.json`,
  `metadata/summary.json`, and 10 PNG previews under `data/plantvillage/samples/`.
- Actual split sizes: **37,997 train**, **8,129 validation**, and **8,179 test**
  images (54,305 total). The per-class distribution is recorded in
  `data/plantvillage/metadata/summary.json`.
- Added `ai-service/train_cnn.ipynb`, a Google Colab-ready ResNet-50 transfer
  learning notebook. It trains the final residual block and classifier with
  Adam, uses early stopping on validation loss, saves the best checkpoint, and
  evaluates the untouched test set with accuracy plus macro precision, recall,
  and F1.
- Completed ResNet-50 transfer-learning training on a Google Colab T4 GPU:
  the pretrained backbone was frozen except for `layer4` and the replacement
  classifier; Adam with weighted cross-entropy was used. Training ran all 12
  epochs because validation loss continued to improve.
- Final held-out test metrics: **accuracy 0.9960876**, **macro precision
  0.9954639**, **macro recall 0.9952816**, and **macro F1 0.9953562**. These
  are the historical original PlantVillage-only Stage 2 results; the 2026-10-04
  retraining results near the top of this log are now current.
- Stage 3 processed all 9 curated PDFs with the confirmed 800-character chunks
  and 120-character overlap: **142 chunks** in total. The confirmed
  `all-MiniLM-L6-v2` sentence-transformers model generated normalized chunk
  embeddings, which are stored in a persistent local FAISS index.
- Added the incremental RAG components: `rag/document_catalog.json` records
  exact versus partial document coverage; `rag/ingest.py` now hashes sources
  and skips unchanged PDFs; and `rag/retriever.py` uses FAISS cosine search,
  source coverage checks, and a configurable top-3 threshold.
- Incremental behavior was verified after the initial index build: rerunning
  ingestion retained all 9 unchanged chunk files, and rerunning the FAISS build
  reported `added_chunks: 0`, `updated_documents: 0`, `skipped_documents: 9`,
  `total_chunks: 142`.
- Final Stage 3 calibration uses **cosine similarity threshold 0.40** with
  top-3 retrieval. Every exact-document query retained relevant context above
  the threshold. The observed cosine scores are below; entries marked
  "returned" are the chunks admitted after both thresholding and coverage
  checks.

  | Query / exact class | Returned cosine scores at 0.40 | Source document(s) |
  | --- | --- | --- |
  | Apple scab | 0.535378 | `apple_scab_tnau.pdf` |
  | Citrus greening | 0.627504, 0.534166, 0.517846 | `citrus_greening_tnau.pdf` |
  | Potato early blight | 0.516004, 0.411320 | `potato_early_blight_tnau.pdf` |
  | Tomato early blight | 0.505967, 0.465661 | `tomato_early_blight_tnau.pdf` |
  | Tomato late blight | 0.443833, 0.408389 | `tomato_late_blight_tnau.pdf` |
  | Tomato yellow leaf curl virus | 0.643117, 0.415762 | `tomato_leaf_curl_tnau.pdf` |
  | Tomato Septoria leaf spot | 0.534159, 0.432195 | `tomato_septoria_leaf_spot_tnau.pdf` |
  | Corn Northern Leaf Blight (known gap) | none returned | no exact reference document |

- The Corn gap query's raw top-3 cosine scores were **0.536395**, **0.530745**,
  and **0.526286**, all from `agriculture_diseases_tnau.pdf`. It correctly
  returned `no_reference_document`, not those chunks. Similarity alone is not
  sufficient because the broad supplementary document shares generic disease
  vocabulary; the retriever first consults `document_catalog.json` when given
  the CNN disease class, permits only documents registered as **exact** coverage
  for that class, and then applies the cosine threshold. Corn Northern Leaf
  Blight has no exact registered document, so its allowed-source set is empty.
  The related tomato fruit-canker PDF is likewise registered as partial only
  and cannot satisfy Tomato Bacterial spot coverage.
- Repeated the full Stage 3 retrieval suite in a Google Colab CPU runtime. It
  reproduced the local calibration scores and coverage-guard behavior exactly:

  | CNN class | Colab result |
  | --- | --- |
  | `Apple___Apple_scab` | returned `apple_scab_tnau-0001` at 0.535378 |
  | `Orange___Haunglongbing_(Citrus_greening)` | 3 `citrus_greening_tnau.pdf` matches: 0.627504, 0.534166, 0.517846 |
  | `Potato___Early_blight` | 2 `potato_early_blight_tnau.pdf` matches: 0.516004, 0.411320 |
  | `Tomato___Early_blight` | 2 `tomato_early_blight_tnau.pdf` matches: 0.505967, 0.465661; raw top score 0.625817 was from the broad PDF and was excluded by coverage gating |
  | `Tomato___Late_blight` | 2 `tomato_late_blight_tnau.pdf` matches: 0.443833, 0.408389; broad-PDF raw candidates scored higher but were excluded |
  | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | 2 `tomato_leaf_curl_tnau.pdf` matches: 0.643118, 0.415762 |
  | `Tomato___Septoria_leaf_spot` | 2 `tomato_septoria_leaf_spot_tnau.pdf` matches: 0.534159, 0.432195; broad-PDF raw candidates were excluded |
  | `Corn_(maize)___Northern_Leaf_Blight` | `no_reference_document`, empty matches; raw 0.53+ broad-PDF candidates blocked by coverage gating |
- Added standalone `ai-service/llm/advisor.py` for Stage 4. It accepts a
  manually supplied disease class and existing retrieval result, uses LangChain
  conversation memory, and sends the original verified chunks in every initial
  and follow-up prompt. It does not call the retriever itself, preserving the
  module-first boundary.
- Selected the Gemini API through LangChain (`gemini-3.6-flash`) for the
  intended free-tier development path. The original `gemini-2.5-flash` request
  returned 404 because it is no longer available to new users; the model was
  updated to Google's currently documented stable replacement. The prompt
  enforces chunk-ID citations and instructs the model to say that the verified
  context lacks an answer rather than introduce parametric advice. A
  no-reference retrieval returns a fixed transparent response without calling
  the LLM.
- The first Colab Apple Scab generation was **truncated** mid-sentence before
  the source-backed Management content. `max_output_tokens` was increased from
  600 to **1,400**, and `advisor.py` now exposes Gemini's `finish_reason` in
  every `AdvisoryResponse`/test JSON result. Stage 4 live tests must be rerun;
  require a natural ending plus a normal stop finish reason before marking this
  stage complete.
- Re-ran all standalone Stage 4 tests in Colab after increasing the response
  limit. All passed:

  | Test | Result |
  | --- | --- |
  | Apple Scab initial diagnosis | Full natural answer with leaf and fruit symptoms, source-grounded chunk citations, and `finish_reason: STOP`. No truncation remained. |
  | Apple Scab follow-up: organic farming | Same `session_id` was retained and the model correctly stated that the retrieved verified context did not cover organic-farming guidance, instead of adding unsupported advice. |
  | Corn Northern Leaf Blight gap | Returned `no_verified_reference` with an honest explanation and no fabricated treatment or advisory text. |
- Added the pre-Stage-5 Docker runtime for `ai-service/`: `Dockerfile`,
  `.dockerignore`, `README.md`, `app.py`, `models/cnn_classifier.py`, and a
  smoke-test helper. The Linux image is based on `python:3.11-slim`, installs
  CPU-only PyTorch plus the existing requirements, bundles the 94.7 MB
  ResNet-50 checkpoint, the FAISS index, catalog, processed/source documents,
  and all AI-service source. It exposes FastAPI on port 8000. FastAPI,
  Uvicorn, multipart upload handling, Pillow, and NumPy were added to
  `requirements.txt`; these are required to expose the already-completed AI
  modules as the specified FastAPI bridge, not Stage 5 web-app dependencies.
- The Docker image build completed successfully on Docker Desktop Linux
  (`plant-disease-ai-service:local`). It downloads `all-MiniLM-L6-v2` during
  image build and keeps the model cache at `/opt/hf-cache`; runtime sets the
  Hugging Face/Transformers offline flags and `SENTENCE_TRANSFORMERS_HOME` to
  that baked cache. This specifically prevents the prior host-cache/Hub lookup
  failure at query time.
- Container smoke verification completed for service startup, CNN inference,
  and offline RAG. `GET /health` returned `200 {"status":"ok"}`. Using the
  existing Apple Scab sample inside the running Linux container produced CNN
  class `Apple___Apple_scab` at confidence `0.954912`, then FAISS retrieval
  status `ok` with `apple_scab_tnau-0001` from `apple_scab_tnau.pdf` at cosine
  similarity `0.536440`. There was no macOS native-library segmentation fault
  and no runtime Hugging Face network/cache lookup after the cache-path fix.
- Completed the final live container smoke test through the exposed FastAPI
  port using `curl` plus `smoke_test.py` and a runtime-only key from root
  `.env` (`docker run --env-file .env`). All three modules worked together:
  the CNN returned Apple Scab at approximately **95.5% confidence**, RAG
  retrieved the correct Apple Scab chunk, and Gemini returned `status: ok`,
  source metadata, and `finish_reason: STOP`. This verifies the live
  `CNN → RAG → Gemini` path inside the Linux container, not only the prior
  independent Colab/module tests. The image, source, and secret handling are
  now ready for Stage 5 integration when approved.
- Training history:

  | Epoch | Train loss | Train accuracy | Validation loss | Validation accuracy |
  | ---: | ---: | ---: | ---: | ---: |
  | 01 | 0.5193 | 0.8864 | 0.0994 | 0.9681 |
  | 02 | 0.1033 | 0.9704 | 0.0643 | 0.9771 |
  | 03 | 0.0693 | 0.9790 | 0.0515 | 0.9827 |
  | 04 | 0.0529 | 0.9830 | 0.0345 | 0.9895 |
  | 05 | 0.0489 | 0.9854 | 0.0261 | 0.9913 |
  | 06 | 0.0383 | 0.9889 | 0.0293 | 0.9902 |
  | 07 | 0.0355 | 0.9898 | 0.0270 | 0.9922 |
  | 08 | 0.0327 | 0.9890 | 0.0248 | 0.9913 |
  | 09 | 0.0237 | 0.9930 | 0.0241 | 0.9918 |
  | 10 | 0.0235 | 0.9929 | 0.0197 | 0.9930 |
  | 11 | 0.0250 | 0.9934 | 0.0211 | 0.9929 |
  | 12 | 0.0199 | 0.9941 | 0.0211 | 0.9941 |

---

## Decisions Made During Implementation

*(Use this section to record any answers to `PROJECT_SPEC.md` Section 17 "Open Questions," or any other implementation-time decision not already fixed in the spec. Record what was decided and why, so it isn't re-litigated or silently redone differently by a later agent.)*

- The image split is **70% train / 15% validation / 15% test**, confirmed by
  the project owner on 2026-09-19. The split is deterministic with seed 42 and
  stratified within each class.
- Image preprocessing uses a 224×224 input and ImageNet mean/std because the
  finalized stack specifies PyTorch transfer learning with a pretrained CNN.
- The preprocessor supports both its downloader's `raw/` location and the
  supplied standard PlantVillage `color/` location. The current run uses
  `color/`, without moving or duplicating dataset images.
- **Class imbalance:** use weighted cross-entropy, not oversampling. The
  notebook reads each class's training count from `metadata/summary.json` and
  calculates weight `N / (C × n_class)`, where `N` is the training-set total,
  `C` is 38 classes, and `n_class` is that class's training count. This gives
  scarce classes more loss influence without duplicating samples.
- **CNN backbone:** ResNet-50 with ImageNet pretrained weights. All pretrained
  layers are frozen initially except the final residual block (`layer4`); the
  classifier is replaced for 38 classes and trained with `layer4` using Adam.
- PDF chunk size and overlap remain required command-line arguments, rather
  than fixed values, because Section 17 reserves their empirical selection for
  Stage 3.
- Stage 3 tuning values confirmed by the project owner: `all-MiniLM-L6-v2`,
  800-character chunks, 120-character overlap, and top-3 retrieval. The
  final cosine threshold is **0.40**. It retains all seven exact-document test
  queries (lowest retained score 0.408389) while removing lower-scoring chunks;
  coverage gating additionally prevents a high-scoring broad-document false
  match for known gaps. This remains a tunable starting point as more documents
  are curated.
- **No login/authentication:** Stage 5 will not implement registered or
  authenticated user accounts. On first visit, the frontend will generate a
  UUID session/device ID and store it in browser `localStorage`; diagnosis and
  chat requests will include it, and the backend will use it in the Diagnosis
  table in place of an authenticated `user_id` (the column may retain a similar
  name/type). The User entity's `register()`, `login()`, and `passwordHash`
  fields from Section 10 are dropped; Diagnosis and ChatMessage otherwise
  remain. This avoids authentication complexity and demo friction without
  improving the AI-pipeline focus of the capstone. History is limited to the
  same browser on the same device: it is lost if browser data is cleared, the
  user changes browser/device, or uses private/incognito mode. This limitation
  is accepted and must be disclosed.
- **Diagnosis image storage:** Stage 5 will save uploaded images in a local
  backend uploads folder and store the path/filename in `Diagnosis.imageUrl`.
  The frontend will retrieve images through a static resource route or a simple
  `/images/{filename}` endpoint. Images will not be stored as base64 blobs in
  the database. This keeps the database lean and avoids row bloat and query
  slowdown; using `imageUrl` for the path is consistent with Section 10.
- **Low-confidence warning:** show a prominent uncertainty warning whenever
  the CNN confidence is below **70%**. Wording: “Low confidence — treat this as
  uncertain. The model always selects one of its 38 trained classes, so
  unfamiliar plants, non-leaf photos, or field conditions can lead to a
  misleading label. Try a clearer leaf photo or ask a local agricultural
  expert.” This is a low-risk UI cue, not a calibrated rejection threshold or
  an out-of-distribution detector; the confidence value remains visible.
- **Mendeley field-condition tomato images:** the owner-provided dataset in
  `ai-service/data/tomato_realworld_raw/` is added to the matching ten
  `plantvillage/color/` tomato class folders, preserving all PlantVillage
  images. Exact filename collisions are retained by prefixing the added
  Mendeley copy with `Mendeley_`; non-tomato image folders are unchanged.
  Stage 1 manifests are regenerated over the combined dataset with seed 42
  and the existing stratified 70/15/15 allocation. This expands training data
  only; it does not authorize retraining the CNN.
- **Updated Stage 2 training/evaluation:** `train_cnn.ipynb` reads the merged
  `plantvillage/color/` directory and requires the regenerated 55,914-image
  summary/manifest, preventing accidental use of the prior dataset. It derives
  balanced weights again as `N / (C × n_class)` from the current training
  counts. Held-out reporting includes overall metrics and top-1 accuracy plus
  support for the ten tomato classes and the other 28 classes, grouped by the
  true class. The existing ResNet-50, frozen-backbone-except-`layer4`, Adam,
  weighted cross-entropy, 12-epoch cap, and patience-3 early stopping remain.
  The 2026-10-04 retraining was run by the owner in Colab; current metrics and
  the observed tomato-vs-other-class generalization gap are recorded above.
- **Stage 5 API contract:** React sends `multipart/form-data` field `image` to
  Spring `POST /api/diagnoses` with `X-Session-Id`. Spring persists the image
  and diagnosis, then sends that image to AI `POST /diagnose`. Follow-ups use
  `POST /api/diagnoses/{diagnosisId}/messages` with JSON `{ "message": "..." }`;
  Spring scopes the diagnosis to the same session and calls AI `POST
  /follow-up` with the AI-issued advisory `session_id` and question. History is
  `GET /api/diagnoses`; reopening a thread uses `GET
  /api/diagnoses/{diagnosisId}`. Spring is the only API called by the browser.
- **Gemini transient-error retry:** the AI advisory layer makes one
  application-level retry after a one-second delay for Gemini 429 quota
  throttling or 503 service unavailability. Other errors are surfaced without
  retry. Gemini documents RPM/TPM/RPD limits as project-level and identifies
  503 as temporary service overload/unavailability; active project quota
  values must be checked in AI Studio and cannot be inferred from a 503 alone.

## Stage 5 Implementation To Date

- Added the Spring Boot 3.3 / Java 17 backend with REST endpoints, PostgreSQL
  JPA entities/repositories for session-scoped diagnoses and per-diagnosis chat
  messages, image validation and local file storage, and an HTTP client for the
  existing FastAPI service. AI code remains in Python.
- Added a React/Vite application with one new thread per uploaded image,
  diagnosis history that reopens prior threads, follow-up chat, source
  citations, an explicit no-verified-reference notice, the PlantVillage field
  caveat, and the 70% confidence warning.
- Added Dockerfiles and a root Compose stack for PostgreSQL, AI service, Spring
  Boot, and the frontend. `README.md` documents setup and known limits.
- Frontend production build succeeds. Spring compilation succeeds, the Compose
  file validates, and the four-container stack starts successfully. The demo
  is served at `http://localhost:5173`; its default services are PostgreSQL 16,
  Spring Boot on internal port 8080, and the AI service on internal port 8000.
- Verified upload → CNN → coverage-guarded RAG → no-reference advisory for a
  Corn Northern Leaf Blight PlantVillage sample through the React-facing API.
  It returned HTTP 200, persisted the image and diagnosis, correctly returned
  `no_verified_reference` with no sources, and created an assistant thread
  message. A follow-up returned HTTP 200 with a safe no-reference response;
  reopening the diagnosis returned the persisted assistant/user/assistant
  messages, and the diagnosis appeared in that session's history.
- A positive-reference Apple Scab request reached Gemini after CNN and RAG,
  but earlier attempts returned HTTP 503 `UNAVAILABLE` due to temporary high
  demand on `gemini-3.6-flash` (confirmed in the AI service trace). The backend
  removes the uncommitted image on AI failure.
- On 2026-09-30, a fresh Apple Scab upload succeeded with HTTP 200, positive
  RAG retrieval (`apple_scab_tnau-0001` from `apple_scab_tnau.pdf`), and a
  grounded Gemini answer. A direct call to the AI follow-up route with the
  stored advisory session also succeeded and returned a cited answer. However,
  follow-up requests through Spring repeatedly received HTTP 422 from the AI
  route, which Spring currently maps to a generic HTTP 503. This is a request
  integration issue, not evidence of a Gemini 503; the end-to-end follow-up
  through the browser-facing API remains unverified and needs investigation.
  The one-time 1-second 429/503 retry was added to the Python advisor, but this
  particular follow-up did not exercise it because the upstream response was
  422.
- The exact Spring follow-up 422 body was
  `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}`.
  The old Spring client logged a JSON object containing `question` and
  `session_id`, but FastAPI received no request body. A successful direct
  Python request sent those same fields as UTF-8 JSON bytes. Spring follow-ups
  now use `RestTemplate` with an explicit UTF-8 JSON byte body and JSON headers.
  A follow-up through the React chat UI then returned HTTP 200, persisted the
  user question and assistant answer, and displayed the cited response in the
  reopened thread. The uploaded diagnosis was seeded under the browser's
  session through the local Spring API because Chrome's file chooser bridge
  blocked programmatic file selection; the question itself was submitted in
  the visible UI.
- On 2026-10-01, the Apple Scab sample was uploaded through the browser's
  visible file chooser; the UI created and displayed a new diagnosis at 95%
  confidence with `apple_scab_tnau-0001`. The follow-up was submitted in that
  same UI thread. Gemini returned `429 RESOURCE_EXHAUSTED`, identifying the
  free-tier `gemini-3.6-flash` per-day project request quota (20 requests) and
  a suggested retry delay of about 49 seconds. The UI showed its retry message;
  a follow-up retry after that delay hit the quota again, so no assistant
  reply was saved. The complete UI upload path is verified, but a successful
  browser-to-Gemini follow-up remains pending quota availability.
- On 2026-10-04, rebuilt `plantdiseasedetection-ai-service:latest` from the
  replaced checkpoint; build output confirmed the Dockerfile's checkpoint
  `COPY` step. Recreated the AI service, backend, and frontend containers
  without rebuilding unrelated services. The image checkpoint matched the
  local checkpoint byte-for-byte. Through the React-facing `/api/diagnoses`
  route, an Apple Scab sample returned HTTP 200, class Apple Scab (99.99996%),
  and grounded Gemini guidance citing `apple_scab_tnau-0001` (score 0.53644).
  A Mendeley real-world Tomato Early Blight sample also returned HTTP 200 and
  Tomato Early Blight (63.26%), with grounded Gemini guidance citing
  `tomato_early_blight_tnau-0003` and `tomato_early_blight_tnau-0001`. The
  frontend returned HTTP 200 and Spring `/api/health` reported `aiService: ok`.
  These confirm the full CNN → RAG → Gemini path through the restarted web
  stack. The tomato confidence is below the logged 70% warning threshold.

---

## Deviations from PROJECT_SPEC.md

*(If actual implementation diverges from what the spec says — e.g., a different dataset, a different library, a changed folder path — log it here with a reason. If there are no deviations, leave as below.)*

- Section 10's User login/password entity is intentionally omitted in favor of
  the session/device ID decision above.

---

## Known Issues / Unfinished Items

*(Anything flagged as a problem, todo, or incomplete edge case during implementation — so it isn't forgotten or silently ignored by whoever picks this up next.)*

- `ai-service/data/agri_docs/` now contains 13 references: the original 9 TNAU
  PDFs plus 4 credible non-TNAU sources (2 Lucid Apps and 2 Utah State
  University Extension documents). Matching coverage remains incomplete for
  the gap classes listed below. More matching documents must be curated; do not
  weaken groundedness to compensate.
- The near-99.6% held-out accuracy reflects PlantVillage's controlled,
  lab-condition images. Per the Section 14 limitation, it must not be presented
  as real-world field performance; field photos may produce lower accuracy.
  This is an expected dataset limitation, not a model bug.
- `ai-service/outputs/resnet50_best.pt` (94,665,315 bytes),
  `evaluation_metrics.json`, and `training_history.json` are present locally.
  The CNN checkpoint was bundled into the Docker image.
- The source PDFs, processed chunks, and FAISS index are present at these exact
  project paths:
  `ai-service/data/agri_docs/processed/ingestion_manifest.json`,
  `ai-service/data/agri_docs/processed/*.jsonl`,
  `ai-service/rag/vector_store/chunks.faiss`, and
  `ai-service/rag/vector_store/index_manifest.json`. The embedding model is
  cached by sentence-transformers outside the project under the current user's
  Hugging Face cache. No embedding cache is stored inside the repository.
- A local native-library segmentation fault (`exit code 139`) occurred when
  attempting to rerun query embedding from the cached model with offline-only
  settings. It does not affect the saved FAISS index or the completed measured
  calibration scores above. This environment-specific macOS runtime issue will
  not be pursued: the Docker Linux runtime is the supported way to run
  `ai-service`, so native macOS inference is not required. Colab CPU
  verification reproduced all results exactly, confirming this is not a
  retriever logic or FAISS-index issue; no code change is required.
- Docker runtime verification is complete. A root `.env` template holds only a
  user-supplied local `GOOGLE_API_KEY` placeholder and is ignored by Git; the
  real key is passed at runtime with `--env-file .env`, never committed or
  baked into the image.
- Observation only: `agriculture_diseases_tnau.pdf` often ranks above exact
  Tomato references in raw cosine search because its generic disease-description
  language overlaps the queries. Exact-coverage gating currently handles this
  correctly. Monitor it as the corpus grows in case the broad reference begins
  to crowd out legitimate retrieval candidates.
- Future RAG-tuning opportunity, not a current bug: Apple Scab retrieval
  returned only `apple_scab_tnau-0001`. The advisor correctly cited the
  available symptom/clean-cultivation content and declined to invent the
  fungicide schedule that appears in a later source chunk. Evaluate increasing
  same-document retrieval depth or revisiting chunk boundaries after more
  documents are added; do not weaken groundedness to compensate.
- Known documentation gaps: Apple Black rot; Apple Cedar apple rust; Grape
  Black rot; Grape Esca (Black Measles); Grape Leaf blight (Isariopsis Leaf
  Spot); Peach Bacterial spot; Tomato Bacterial spot (only partial, non-exact
  tomato fruit canker coverage); and all disease classes for Corn, Cherry,
  Strawberry, Blueberry, and Raspberry. These classes must return no grounded
  context rather than unrelated advice until matching documents are curated.
- Gemini may temporarily return HTTP 503 during high demand. The backend maps
  AI-service 5xx errors to a retryable user-facing service-unavailable response;
  no diagnosis record or image is retained when initial advisory generation
  fails.

---

## Next Step

Continue Stage 6 by completing a positive-reference live Gemini quality check
when the provider is available, re-exercising the low-confidence UI warning,
then consolidate the evaluation findings and remaining limitations. The latest browser upload returned a transparent
503-friendly UI error without saving a diagnosis; it was not a quota 429. The
`ai-service` Docker Linux runtime remains the supported runtime and avoids the
local macOS native-library failure.

## Stage 6 Baseline Evaluation — 2026-10-14

### CNN held-out metrics audit

Read `outputs/evaluation_metrics.json` and verified the per-class test supports
sum to **8,420**, matching `metadata/summary.json`. The tomato support sums to
**2,975** and the other 28 classes to **5,445**, also matching the split
summary. The artifact values are:

| Metric | Result |
| --- | ---: |
| Overall accuracy | 99.05% |
| Macro precision | 98.69% |
| Macro recall | 98.94% |
| Macro F1 | 98.81% |
| Tomato classes accuracy (n=2,975) | 97.95% |
| Other classes accuracy (n=5,445) | 99.65% |
| Group gap (other minus tomato) | 1.70 percentage points |

Among tomato classes, the lowest per-class F1 values in the artifact are Leaf
Mold (91.32%), Early Blight (92.80%), and Late Blight (97.53%). These are
candidate priorities for error review. The JSON contains aggregate metrics,
not saved per-image predictions or a confusion matrix, so error types,
confidence calibration, and source-specific field-vs-lab accuracy cannot be
recomputed from the available evaluation artifacts.

**Interpretation caveat:** the tomato-vs-other accuracy gap is consistent with
the documented generalization concern, but it is not a controlled estimate of
the field-domain penalty. The tomato group mixes PlantVillage and Mendeley
images and also differs from the other group in crop/class composition; the
split manifest has no source-provenance field. The final report may cite the
1.70-point observed group gap, but should not attribute all of it exclusively
to field conditions without a source-stratified evaluation.

### RAG relevance and coverage evidence

The current v2.6 retrieval changes were exercised in Linux/Docker during the
preceding offline audit. Across the **11 exact-covered classes / 61 indexed
chunks**, each class's registered document is returned in full, and all 11
retrieval contexts contain both symptom and management material. The
question-specific checks confirmed Target Spot Impact (`tomato_target_spot-0004`),
chemical management (`tomato_target_spot-0010`), pre-planting advice
(`tomato_target_spot-0006`), and Apple Scab fungicide management
(`apple_scab_tnau-0002`) are present in context. The organic-certification
question has no supporting passage, and the advisor prompt requires a decline
rather than inference. All **27 uncovered classes** return
`no_reference_document` with zero chunks and no query embedding; Corn Northern
Leaf Blight is included in this guard check.

This verifies coverage/context availability, not an automated human relevance
score or generated-answer groundedness score. Returning every chunk from an
exact-class document favors recall and citations but increases prompt/context
size; the advisor must select passages relevant to each question. Document
growth may require a measured context-size/retrieval-depth review.

### Full application and build checks

- `frontend`: `npm run build` passed (Vite production build completed in about
  1.1 seconds).
- `backend`: `mvn test` completed successfully, but reported **“No tests to
  run” on the initial baseline. A focused `DiagnosisControllerTest` suite has
  since been added and now passes all **3 tests**: health status, malformed
  session UUID rejection, and valid follow-up request delegation. These are
  MVC/controller tests with mocked services, not database persistence tests.
- Live Docker/browser check used the held-out Corn Northern Leaf Blight test
  image `10c52456-18c0-43ec-afeb-0ff505b912cb___RS_NLB 3505.JPG`. The browser
  upload returned HTTP 200, predicted the expected class at 94% confidence,
  displayed the no-verified-reference warning and static safe advisory, and
  loaded the uploaded image successfully from `/images/{filename}` (HTTP 200).
  A follow-up sent in the same browser thread returned HTTP 200 and the
  no-reference fallback; the diagnosis/thread was fetched again with its
  messages persisted. This gap-class flow does not call Gemini. Proxy logs
  show approximately 3 seconds from multipart request receipt to response for
  this upload (one local observation, not a latency benchmark).
- The frontend proxy `/api/health` returned HTTP 200 with
  `{"aiService":"ok","status":"ok"}` earlier in this session.
- During this Stage 6 continuation, a held-out Apple Scab image
  (`70fa2c8f-5657-444f-b57b-3ad6755acc74___FREC_Scab 3275.JPG`) was submitted
  through the browser UI. CNN and positive-reference RAG reached Gemini, but
  the one-time retry also ended in HTTP 503 `UNAVAILABLE`. The browser surfaced
  the temporary-service message and confirmed no diagnosis was saved. No
  follow-up was possible, and no additional live calls were made after this
  failure. Therefore there is no new live generated-output
  relevance/clarity/groundedness rating yet; prior successful smoke responses
  are documented in Stage 5. The UI request remained in progress for about
  120 seconds before the HTTP 503 appeared, which is a significant live-demo
  latency risk during provider overload; this observation includes client
  retry behavior and is not a normal-path latency measurement.
- The frontend still has no automated test script; its covered paths were
  checked manually in the browser. A new `ai-service/tests/test_retrieval_contract.py`
  suite passed **6 tests** in the supported Linux container: all 11 covered
  classes return exact-source context with symptoms and management; Target
  Spot Impact/chemical passages and Apple Scab management context are present;
  the Corn gap returns no context; fake-model checks confirm citation/decline
  prompt constraints, multi-turn history, and no model call for a no-reference
  diagnosis, and a simulated transient 503 performs exactly one application
  retry after the one-second delay. Together with the 3 Java tests, **9
  automated tests pass**.
- The Linux test run emits a `LangChainDeprecationWarning`: `InMemoryChatMessageHistory`
  is deprecated in the installed LangChain version and scheduled for removal
  in 2.0. It works today; migrate memory storage before upgrading to LangChain
  2.x.
- The 70% low-confidence warning is present in the React diagnosis component,
  but this pass did not obtain a new saved low-confidence diagnosis in the UI.
  Existing Stage 5 logs record a 63.26% Tomato Early Blight result; a fresh
  interactive warning check remains desirable.

Stage 6 remains in progress because no fresh positive-reference LLM response
could be evaluated while Gemini returned 503, and low-confidence UI behavior
was not re-exercised. Added only test infrastructure (the Python unittest file,
Spring Boot test dependency, and controller test class); runtime application
source is unchanged. Validation generated `frontend/dist/` and `backend/target/`.

---

## Session History

*(Optional but useful: one line per work session, so there's a timeline of who/what happened when.)*

- [Date] — Planning phase complete. `PROJECT_SPEC.md` and this log created. No implementation started.
- 2026-09-19 — Created the Section 9 structure and Stage 1 image/PDF
  preprocessing tooling. Confirmed 70/15/15 split and installed specified
  Python dependencies.
- 2026-09-19 — Verified supplied PlantVillage `color/` data (38 classes,
  54,305 images) and completed preprocessing: 37,997/8,129/8,179
  train/validation/test records, numeric class encoding, ImageNet-compatible
  transforms, and 10 visual sample outputs. Stage 1 complete; awaiting review
  before Stage 2.
- 2026-09-19 — Stage 1 approved. Added a Colab-ready weighted ResNet-50
  transfer-learning notebook for Stage 2. Training and held-out test evaluation
  remain pending execution on Google Colab.
- 2026-09-19 — Recorded completed Stage 2 Google Colab T4 training: weighted
  ResNet-50 transfer learning ran for 12 epochs, with held-out accuracy
  0.9960876 and macro F1 0.9953562. Stage 3 remains blocked pending explicit
  project-owner approval.
- 2026-09-23 — Began Stage 3. Extracted 142 chunks from 9 PDFs, generated
  `all-MiniLM-L6-v2` embeddings, and built an incremental FAISS index. Initial
  tests exposed high raw similarity from the broad reference for the Corn gap;
  the coverage guard correctly blocked it. Checkpointed before final 0.40
  threshold retest and reporting.
- 2026-09-23 — Finalized Stage 3 calibration at cosine threshold 0.40: all
  seven exact-document test queries retained relevant chunks; Corn Northern
  Leaf Blight returned no context despite high raw broad-document similarity,
  due to exact-coverage gating. Stage 4 awaits explicit approval.
- 2026-09-24 — Planned Docker containerization of `ai-service/` before Stage 5
  so the eventual local Spring Boot integration calls a stable Linux-hosted AI
  service. Colab is retained only for interim Stage 3–4 verification.
- 2026-09-24 — Began Stage 4. Implemented standalone LangChain/Gemini grounded
  advisory and multi-turn memory module. Live Colab testing is pending a Gemini
  API key; Stage 5 has not started.
- 2026-09-24 — Updated the Stage 4 model from unavailable `gemini-2.5-flash`
  to stable `gemini-3.6-flash` after the Colab API returned 404 for new-user
  access. Retesting remains pending.
- 2026-09-24 — Verified the entire Stage 3 retrieval suite in Colab CPU:
  matched-class scores and coverage-gated Corn gap behavior reproduced exactly.
  Confirmed the macOS segmentation fault is environment-specific, not a RAG
  retrieval logic bug. Stage 4 remains awaiting approval.
- 2026-09-24 — Completed Stage 4 Colab verification using `gemini-3.6-flash`:
  Apple Scab initial and follow-up responses remained grounded with preserved
  session memory; the Corn gap surfaced no verified reference. The 1,400-token
  limit removed the earlier truncation (`finish_reason: STOP`). Stage 5 awaits
  explicit approval.
- 2026-09-25 — Built and started the Linux `ai-service` Docker image using
  Python 3.11 slim and CPU dependencies. Fixed the container's baked
  sentence-transformers cache path, then verified FastAPI startup, ResNet-50
  Apple Scab inference, and offline FAISS retrieval without the macOS segfault
  or Hub lookup. Live Gemini smoke verification awaits a runtime-only API key;
  Stage 5 was not started.
- 2026-09-25 — Ran the final live Docker smoke test using the root ignored
  `.env` file at container runtime. The FastAPI CNN → FAISS RAG → Gemini path
  returned Apple Scab (~95.5%), the correct reference chunk, and a sourced
  Gemini response with `status: ok` / `finish_reason: STOP`. Docker
  containerization is complete; Stage 5 was not started.
- 2026-09-29 — Began Stage 5. Added the Spring Boot/PostgreSQL REST backend,
  React diagnosis/thread/history interface, Dockerfiles and Compose stack.
  Recorded the 70% confidence-warning decision. Local frontend build, backend
  compilation, and Compose startup succeeded. Verified the complete no-
  reference diagnosis/follow-up/history path for Corn. The positive-reference
  Apple request reached Gemini, which returned temporary 503 high demand twice;
  complete positive-reference chat verification remains pending. Stage 6 was
  not started.
- 2026-10-03 — Added 1,609 Mendeley real-world tomato images to the ten matching
  PlantVillage `color/` classes. Preserved all 665 filename-colliding source
  images using the `Mendeley_` prefix; no non-tomato image folders were changed.
  Re-ran Stage 1 preprocessing and validated all 55,914 images: 39,123 train,
  8,371 validation, and 8,420 test (seed 42; 38 classes). CNN retraining was
  not performed.
- 2026-10-04 — Updated `ai-service/train_cnn.ipynb` for owner-run Colab
  retraining on the merged dataset. The notebook guards against stale manifests,
  recomputes class weights from the regenerated training distribution, and
  reports held-out tomato-10 and other-28 subset accuracy alongside the overall
  metrics. Training was not run.
- 2026-10-04 — Logged owner-reported CNN retraining and inspected all three
  replacement artifacts. Evaluation/history JSON figures differ slightly from
  the supplied summary; exact artifact values and that discrepancy are
  recorded above. Rebuilt the AI image, confirmed the embedded checkpoint hash,
  recreated AI/backend/frontend Compose services, and verified Apple Scab plus
  real-world Tomato Early Blight diagnosis flows through the web-facing API.
  No Stage 6 work was started.
- 2026-10-04 — Incrementally ingested four non-TNAU tomato references; all nine
  existing TNAU documents were skipped unchanged. Added 29 chunks to the FAISS
  index (13 documents / 171 chunks total), calibrated exact coverage for the
  four new classes, rebuilt the Docker image, recreated the web stack, and
  verified Tomato Target Spot through CNN → RAG → Gemini via the web-facing API.
  Stage 6 was not started.
- 2026-10-05 — Fixed uploaded diagnosis image display in chat and history:
  stored `/images/{filename}` URLs were proxied to `/images/` on the backend,
  while Spring serves them at `/api/images/{filename}`. Updated both Vite dev
  and production Nginx proxies, rebuilt/recreated the frontend, and confirmed
  an existing uploaded image loads through the frontend with HTTP 200 and
  `image/jpeg` content type.
- 2026-10-09 — Cleaned and re-ingested all 13 RAG PDFs with processing version
  2.6, rebuilt the 211-chunk FAISS index in Linux Docker, and confirmed a
  repeat run skips all 13 unchanged documents. Junk-only chunks fell from 12
  to zero. Calibrated all 11 exact-covered classes plus Corn Northern Leaf
  Blight; all 27 uncovered classes remain blocked by the coverage guard. Kept
  the 0.40 cosine threshold. No Gemini, web-stack, or full-image rebuild work
  was performed; waiting for approval before the separate retrieval fix.

## RAG Retrieval and Advisor Fix — 2026-10-14

### Read-only investigation (before the change)

`app.py` diagnosed an image using `retriever.retrieve(query, disease_class, top_k=3)` with the 0.40 floor. `LLMAdvisor.start_diagnosis()` stored only those returned matches in `_Conversation.source_chunks`. The `/follow-up` handler called only `advisor.answer_follow_up(session_id, question)`; that method re-sent the stored source chunks and conversation history and did not call the retriever. The hypothesis is confirmed: follow-ups did not retrieve question-specific context, and the initial top-3/floor could omit relevant sections.

The audit query was the app-generated `disease_class.replace("_", " ") + " symptoms and management"`. Scores below are cosine similarity for **every chunk** in the exact-coverage document. “Returned” means the prior 0.40/top-3 path would have admitted it when it ranked in that top 3; all below-floor rows would have been excluded regardless of rank. Labels are the primary section/content label.

| Class | Chunk ID | Score | Old 0.40 status | Content label |
| --- | --- | ---: | --- | --- |
| `Apple___Apple_scab` | `apple_scab_tnau-0001` | 0.536275 | returned (if top 3) | symptoms |
| `Apple___Apple_scab` | `apple_scab_tnau-0002` | 0.134920 | below 0.40 | management |
| `Orange___Haunglongbing_(Citrus_greening)` | `citrus_greening_tnau-0001` | 0.581571 | returned (if top 3) | symptoms |
| `Orange___Haunglongbing_(Citrus_greening)` | `citrus_greening_tnau-0002` | 0.575612 | returned (if top 3) | symptoms |
| `Orange___Haunglongbing_(Citrus_greening)` | `citrus_greening_tnau-0003` | 0.203969 | below 0.40 | management |
| `Potato___Early_blight` | `potato_early_blight_tnau-0001` | 0.633849 | returned (if top 3) | symptoms |
| `Potato___Early_blight` | `potato_early_blight_tnau-0002` | 0.498221 | returned (if top 3) | spread |
| `Potato___Early_blight` | `potato_early_blight_tnau-0003` | 0.249124 | below 0.40 | other |
| `Potato___Early_blight` | `potato_early_blight_tnau-0004` | 0.231020 | below 0.40 | management |
| `Tomato___Early_blight` | `tomato_early_blight_tnau-0001` | 0.563118 | returned (if top 3) | management |
| `Tomato___Early_blight` | `tomato_early_blight_tnau-0004` | 0.221999 | below 0.40 | spread |
| `Tomato___Early_blight` | `tomato_early_blight_tnau-0002` | 0.173254 | below 0.40 | other |
| `Tomato___Early_blight` | `tomato_early_blight_tnau-0003` | 0.163604 | below 0.40 | other |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0001` | 0.587539 | returned (if top 3) | symptoms |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0009` | 0.214864 | below 0.40 | management |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0006` | 0.183702 | below 0.40 | spread |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0002` | 0.131266 | below 0.40 | other |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0005` | 0.107883 | below 0.40 | spread |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0004` | 0.094440 | below 0.40 | other |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0008` | 0.075069 | below 0.40 | other |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0003` | 0.061338 | below 0.40 | other |
| `Tomato___Late_blight` | `tomato_late_blight_tnau-0007` | 0.025129 | below 0.40 | spread |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0004` | 0.687880 | returned (if top 3) | detection |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0001` | 0.686985 | returned (if top 3) | symptoms |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0003` | 0.614033 | returned (if top 3) | impact |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0002` | 0.605295 | returned (if top 3) | symptoms |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0005` | 0.454076 | returned (if top 3) | management |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0009` | 0.442025 | returned (if top 3) | management |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0008` | 0.382910 | below 0.40 | management |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0006` | 0.380358 | below 0.40 | management |
| `Tomato___Leaf_Mold` | `tomato_leaf_mold-0007` | 0.151900 | below 0.40 | management |
| `Tomato___Septoria_leaf_spot` | `tomato_septoria_leaf_spot_tnau-0001` | 0.688705 | returned (if top 3) | symptoms |
| `Tomato___Septoria_leaf_spot` | `tomato_septoria_leaf_spot_tnau-0002` | 0.264824 | below 0.40 | spread |
| `Tomato___Septoria_leaf_spot` | `tomato_septoria_leaf_spot_tnau-0003` | 0.230178 | below 0.40 | management |
| `Tomato___Septoria_leaf_spot` | `tomato_septoria_leaf_spot_tnau-0004` | 0.195484 | below 0.40 | management |
| `Tomato___Septoria_leaf_spot` | `tomato_septoria_leaf_spot_tnau-0005` | 0.002569 | below 0.40 | management |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0005` | 0.559482 | returned (if top 3) | management |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0006` | 0.519896 | returned (if top 3) | management |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0004` | 0.493443 | returned (if top 3) | detection |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0002` | 0.416754 | returned (if top 3) | spread |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0003` | 0.371280 | below 0.40 | symptoms |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0001` | 0.295954 | below 0.40 | symptoms |
| `Tomato___Spider_mites Two-spotted_spider_mite` | `tomato_spider_mites-0007` | 0.200969 | below 0.40 | management |
| `Tomato___Target_Spot` | `tomato_target_spot-0001` | 0.736127 | returned (if top 3) | symptoms |
| `Tomato___Target_Spot` | `tomato_target_spot-0002` | 0.498825 | returned (if top 3) | symptoms |
| `Tomato___Target_Spot` | `tomato_target_spot-0004` | 0.496267 | returned (if top 3) | impact |
| `Tomato___Target_Spot` | `tomato_target_spot-0005` | 0.449322 | returned (if top 3) | detection |
| `Tomato___Target_Spot` | `tomato_target_spot-0007` | 0.378462 | below 0.40 | management |
| `Tomato___Target_Spot` | `tomato_target_spot-0010` | 0.375653 | below 0.40 | management |
| `Tomato___Target_Spot` | `tomato_target_spot-0008` | 0.368292 | below 0.40 | management |
| `Tomato___Target_Spot` | `tomato_target_spot-0009` | 0.365237 | below 0.40 | management |
| `Tomato___Target_Spot` | `tomato_target_spot-0003` | 0.341564 | below 0.40 | symptoms |
| `Tomato___Target_Spot` | `tomato_target_spot-0006` | 0.333845 | below 0.40 | management |
| `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | `tomato_leaf_curl_tnau-0001` | 0.736089 | returned (if top 3) | management |
| `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | `tomato_leaf_curl_tnau-0004` | 0.343368 | below 0.40 | spread |
| `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | `tomato_leaf_curl_tnau-0002` | 0.165666 | below 0.40 | spread |
| `Tomato___Tomato_Yellow_Leaf_Curl_Virus` | `tomato_leaf_curl_tnau-0003` | 0.091035 | below 0.40 | spread |
| `Tomato___Tomato_mosaic_virus` | `tomato_mosaic_virus-0001` | 0.718263 | returned (if top 3) | spread |
| `Tomato___Tomato_mosaic_virus` | `tomato_mosaic_virus-0003` | 0.602610 | returned (if top 3) | management |
| `Tomato___Tomato_mosaic_virus` | `tomato_mosaic_virus-0002` | 0.471763 | returned (if top 3) | symptoms |
| `Tomato___Tomato_mosaic_virus` | `tomato_mosaic_virus-0004` | 0.165299 | below 0.40 | management |

Examples showing why the floor is unsuitable *inside an exact-coverage document*: Apple Scab management `apple_scab_tnau-0002` scored **0.134920**; Potato Early Blight management `potato_early_blight_tnau-0004` **0.231020**; Tomato Late Blight management `tomato_late_blight_tnau-0009` **0.214864**; Tomato Yellow Leaf Curl management `tomato_leaf_curl_tnau-0004` **0.343368**; Target Spot fungicide management `tomato_target_spot-0010` **0.375653**. A single generic class query is not a good proxy for whether a passage is valid in its already-verified source.

### Implementation choice and threshold

Chose **all chunks from the exact-coverage document** (the prompt’s option b). The eleven exact documents total 61 chunks and the largest is 4,504 characters; at a rough 4 characters/token estimate, the largest context is about 1,126 tokens before prompt overhead. A symptoms+management pair of semantic queries and per-follow-up in-document query (option a) can lower prompt size on some turns, but introduces additional ranking/query behavior and can still omit relevant sections. For the current corpus, a bounded 2–10 chunks per exact class gives more dependable recall and simpler auditable behavior. Token cost scales with the size of the selected class document, so this should be revisited if a reference grows substantially beyond the current ~10-chunk size. Follow-ups receive the same full verified document on every turn plus session history; the system prompt directs the model to use only passages directly relevant to the question and to decline when none answers it.

For a covered class, `RAGRetriever.retrieve()` now does a **class-keyed document lookup** using the exact `document_catalog.json` mapping. It bypasses semantic chunk selection, top-k and the 0.40 floor, and returns all chunks from only the registered exact-coverage document, ordered by chunk ID. It does not embed the query for this covered-class path. The score field is therefore absent from this runtime response; the scores above are audit measurements, not selection scores. Calls without a disease class retain generic semantic top-k/0.40 behavior. Unknown/uncovered classes return `no_reference_document` with empty context before any query embedding; the broad supplementary PDF remains excluded. The 0.40 floor is **not applied within an exact-verified document**; it remains the generic unconditioned retrieval threshold.

`LLMAdvisor` still stores the diagnosis chunks and LangChain session history. Because diagnosis now supplies the full exact document, every follow-up gets the passage it may need. The system prompt now explicitly asks the model to locate directly relevant passages and decline unsupported questions. Chunk-ID citation instructions, in-memory multi-turn history, one-time Gemini 429/503 retry, and the no-reference/no-Gemini path remain in place.

### Offline prompt/context audit (no Gemini calls)

Tested every exact-covered class using a fake model that records prompts and returns a fixed placeholder. The retrieved context contained **all 61 exact-document chunks**; every class had both symptom and management content (`has_symptoms=true`, `has_management=true`). The full exact chunk text below is the context sent in the initial Gemini request. It is also the complete source context repeated in each follow-up prompt for that class. Labels follow the same primary-content convention as the score table.


#### Apple / Apple scab — symptoms: true, management: true


- `apple_scab_tnau-0001` — **symptoms**

  ```text
  Symptoms: Horticultural crops :: Fruits:: Apple Scab: Venturia inaequalis Symptom appears on leaves and fruits. On lower side of the leaf lesion appear as olivaceous spots which turn dark brown to black and become velvety. On young foliage, the spots have a radiating appearance with a feathery edge. On older leaves the lesions are more definite in outline. The lesion may form a convex surface with corresponding concave area on the opposite side. In severe infection leaf blade curved, dwarfed and distorted. Fruits show small, rough, black circular lesions. The centre of the spots become corky and on mature fruits, yellow halo is seen around the lesions.
  ```


- `apple_scab_tnau-0002` — **management**

  ```text
  Management: Clean cultivation, collection and destruction of fallen leaves and pruned materials in winter to prevent the sexual cycle. Spray Tridemorph 0.1% before flowering. Spray Mancozeb 0.25 % at bearing stage. Spray 5 % urea prior to leaf fall in autumn and 2 % before bud break to hasten the decomposition of leaves. S.No Tree stage Fungicide/100lit 1 Silver tip to given tip Captafol 200 gm (or) Captan 300 g or Mancozeb 400 g 2 Pink bud or 15 days after 1 st Captan 250 g or Mancozeb 300 g. spray 3 Petal fall Carbendazim 50 g 4 10 days later Captan 200 g.or Mancozeb 300g 5 14 days after fruit set Captofol 150 g Add stickers – teepol or triton 6 ml/10 lit of spray fluid.
  ```


#### Orange / Haunglongbing (Citrus greening) — symptoms: true, management: true


- `citrus_greening_tnau-0001` — **symptoms**

  ```text
  Symptoms: Horticultural crops :: Fruits:: Citrus Greening : Liberobactor asiaticum ( Phloem limited bacteria) This disease affects almost all citrus varieties irrespective of root stock. Stunting of leaf, sparse foliation, twig die back, poor crop of predominantly greened, worthless fruits. Sometimes only a portion of tree is affected.A diversity of foliar chlorosis. A type of mottling resembling zinc deficiency often predominates. Young leaves appear normal but soon assume on outright position, become leathery and develop prominant veins and dull olive green colour. Green circular dots on leaves. Many twigs become upright and produce smaller leaves. Fruits small, lopsided with curved columella.
  ```


- `citrus_greening_tnau-0002` — **symptoms**

  ```text
  Symptoms: Many twigs become upright and produce smaller leaves. Fruits small, lopsided with curved columella. The side exposed to direct sunlight develops full orange colour but the other side remain dull olive green. Low in juice and soluble solids, high in acid. Worthless either as fresh fruit or for processing. Seeds poorly developed, dark coloured, aborted. Infected budwood; psyllid vector-Diaphorina citri Greening symptom on leaf
  ```


- `citrus_greening_tnau-0003` — **management**

  ```text
  Management: Control psyllids with insecticides. Use pathogen free bud wood for propagation. 500 ppm tetracycline spray, requires fortnightly application.
  ```


#### Potato / Early blight — symptoms: true, management: true


- `potato_early_blight_tnau-0001` — **symptoms**

  ```text
  Symptom: Horticultural crops :: Vegetables:: Potato Early blight: Alternaria solani It is present in both hills & plains. Brown-black necrotic spot-angular, oval shape characterized by concentric rings. Several spot coalesce & spread all over the leaf. Shot holes on fruits. Angular spot on leaf Concentric rings Infected crop Shot holes in tuber
  ```


- `potato_early_blight_tnau-0002` — **spread**

  ```text
  Identification of pathogen - Mode of spread and survival: The conidia and the mycelium in the soil or in the debris of the affected plants can remain viable for more than 17 months. These conidia or the new conidia found on the overwintered mycelium bring about the primary infection of the succeeding potato crop. Secondary infection is more important in the spread of the disease. The conidia formed on the spots developed due to primary infection are disseminated by wind to long distances. The conidia from the affected plant may also be disseminated to the adjoining plants by rain and insects.
  ```


- `potato_early_blight_tnau-0003` — **other**

  ```text
  Epidemiology: Dry warm weather with intermittent rain. Poor vigor. Temperature: 25-30°C. Poorly manured crop.
  ```


- `potato_early_blight_tnau-0004` — **management**

  ```text
  Management: Disease free seed tubers should be used for planting. Removal and destruction of infected plant debris should be done because the spores lying in the soil are the primary source of infection. Very early spraying with Zineb or captan 0.2% and repeating it for every 15 – 20 days gives effective control. The variety Kufri Sindhuri possesses a fair degree of resistance.
  ```


#### Tomato / Early blight — symptoms: true, management: true


- `tomato_early_blight_tnau-0001` — **management**

  ```text
  Horticultural crops :: Vegetables:: Tomato Early Blight: Alternaria solani Field Diagnostic Symptoms Brown spots with concentric rings in a bull's eye pattern with yellow margin. Fruit gets infected through calyx or stem attachment. Brown concentric rings on fruits. Early symptom Affected plant at advanced Concentric ring on Fruits Conidia stage Causal organism Alternaria solani
  ```


- `tomato_early_blight_tnau-0002` — **other**

  ```text
  Mycelium : coloured and septate
  ```


- `tomato_early_blight_tnau-0003` — **other**

  ```text
  Pathogen : coloured, beaked conidia with transverse and longitudinal septae, borne singly or in chains
  ```


- `tomato_early_blight_tnau-0004` — **spread**

  ```text
  Survival and Mode of Spread: Survival: Infected plant debris Primary spread: Infected seed Secondary spread: Conidia carried through rain, wind borne Favourable conditions Warm, humid (24-29 degree C), rainy and wet weather. Integrated Disease Management Removal and destruction of crop debris. Crop rotation. Seed treatment: Trichoderma asperellum @ 4g/kg seeds. Spray Iprodione 50% WP @ 600 g/ac or Azoxystrobin 23% SC @ 200 ml/ac or Mancozeb 35% SC @ 1 kg/ac or Metiram 70% WG @ 1.0 kg/ac or Pyraclostrobin 20% WG @ 200 g/ac or Zineb 75% WP @ 800 g/ac or Azoxystrobin 18.2%+Difenoconazole 11.4% SC @ 200 ml/ac or Metiram55% + Pyraclostrobin5% WG @ 600 g/ac or Tebuconazole 50% + Trifloxystrobin 25% WG@ 140g/ac
  ```


#### Tomato / Late blight — symptoms: true, management: true


- `tomato_late_blight_tnau-0001` — **symptoms**

  ```text
  Symptoms: Horticultural crops :: Vegetables:: Tomato Late blight: Phytophthora infestans Water-soaked black lesions on leaves and stems Lesions expand rapidly and the entire leaf becomes necrotic. White sporulation (sporangia and sporangiophores) on leaves. Fruit Dark brown lesions on fruit Soft rot and disintegration of fruits. Symptoms on leaves Fruit infection Sporangiophores and sporangium Oospore Causal organism Phytophthora infestans (Mont.) de Bary
  ```


- `tomato_late_blight_tnau-0002` — **other**

  ```text
  Asexual spores : Indeterminate sporangiophores, Zoospores: Biflagellate with one tinsel flagellum directed anteriorly and one whiplash flagellum directed posteriorly
  ```


- `tomato_late_blight_tnau-0003` — **other**

  ```text
  Pathogen: Hyaline and coenocytic
  ```


- `tomato_late_blight_tnau-0004` — **other**

  ```text
  Sexual spores : Thick-walled oospore
  ```


- `tomato_late_blight_tnau-0005` — **spread**

  ```text
  Survival : Infected Debris
  ```


- `tomato_late_blight_tnau-0006` — **spread**

  ```text
  Primary spread: Infected debris
  ```


- `tomato_late_blight_tnau-0007` — **spread**

  ```text
  Secondary spread: Wind
  ```


- `tomato_late_blight_tnau-0008` — **other**

  ```text
  Favourable conditions : Cool nights, warm days and extended wet conditions from rain and fog Sporangia formed when RH is < 90% Optimum temp for sporulation is 18 - 22oC
  ```


- `tomato_late_blight_tnau-0009` — **management**

  ```text
  Integrated Disease Management: Proper drainage Crop rotation Soil application of Trichoderma asperellum (viride) @ 1.0 kg/ac. Spray Cyazofamid 34.5% SC @ 80 ml/ac or Azoxystrobin 23% SC @ 200 ml/ac or Mancozeb 35% SC @ 1000 g/ac or Zineb 75% WP @ 800 g/ac or Azoxystrobin 18.2%+ Difenoconazole 11.4% SC @ 200 ml/ac
  ```


#### Tomato / Leaf Mold — symptoms: true, management: true


- `tomato_leaf_mold-0001` — **symptoms**

  ```text
  Symptoms & Life Cycle: Pacific Pests, Pathogens & Weeds - Fact Sheets Tomato leaf mould (076) Tomato leaf mould Passalora fulva (previously known as Fulvia fulva, Mycovellosiella fulva and Cladosporium fulvum). Worldwide. In warm temperate and tropical countries. Asai, Africa, North, South and Central America, the Caribbean, Europe, Oceania. It is recorded from American Samoa, Australia, Fiji, French Polynesia, New Caledonia, New Zealand, Papua New Guinea, Samoa, Solomon Islands, and Tonga. Tomato Yellow spots and patches occur on the top surface of the leaves (Photo 1), with brown to green spore masses on the lower surface (Photos 2&3). The diseased areas join together and the leaves dry up and die. Survival between crops occurs in a number of ways.
  ```


- `tomato_leaf_mold-0002` — **symptoms**

  ```text
  Symptoms & Life Cycle: The diseased areas join together and the leaves dry up and die. Survival between crops occurs in a number of ways. The fungus survives as spores or as "mycelium" (the cotton-like growth of the fungus) in dead tomato plants of the previous crop. It is spread as spores in air currents, by water splash, or on tools and clothing. There is a possibility that spread also occurs by insects and on seed.
  ```


- `tomato_leaf_mold-0003` — **impact**

  ```text
  Impact: The fungus causes a serious disease in cooler, wetter areas. The loss of leaves, from the bottom of the plant upwards, is rapid. Yield reduction is related to the time of infection. If plants are infected before fruits are formed, considerable crop loss occurs. In severe cases, the flowers and, occasionally, the fruit are attacked. Infected flowers may fail to set fruit. Occasionally, the fungus causes an internal blackening of the fruit. Note, in Samoa, fruit yields of susceptible varieties were tripled when fungicides were used to control the disease. In Solomon Islands, it is an important disease in the highlands. It is less common in coastal areas where another leaf mould disease occurs on tomatoes called black leaf mould, Pseudocercospora fuligena (see Fact Sheet no. 45).
  ```


- `tomato_leaf_mold-0004` — **detection**

  ```text
  Detection & inspection: Look for the yellow spots and rapidly developing irregular patches on the upper surfaces of the lower leaves, with brown to green areas on the under surface. Look for plants where leaves dry up and die rapidly. Note, there is another disease that has similar symptoms. It is called tomato black leaf mould, caused by the fungus, Pseudocercospora fuligena (see Fact Sheet no. 45). This fungus and Passalora fulva can only be distinguished by looking at their spores under a microscope.
  ```


- `tomato_leaf_mold-0005` — **management**

  ```text
  Management - CULTURAL CONTROL - Before planting: Do not plant successive crops of tomatoes on the land or in the same garden; use a 3-year crop rotation. Do not plant new crops next to those that have the disease; otherwise spread of the disease to the new crop will be rapid and significant. It is not known for certain whether seed is important in the spread of the fungus. However, hot water treatment has been used as a method of producing seed free from contamination by fungal spores. Seed is treated with water for 25 minutes at exactly 50°C. Note, this is not a method that farmers would use, because of the need for a thermometer. Also, treatment of seed by this method would only be done as a last resort, after other methods have been tried and failed.
  ```


- `tomato_leaf_mold-0006` — **management**

  ```text
  Management - CULTURAL CONTROL - During growth: Remove infected lower leaves as soon as the first three or four fruit trusses (bunches) have been picked. Do not use overhead irrigation; otherwise, it will create conditions for spore production and infection.
  ```


- `tomato_leaf_mold-0007` — **management**

  ```text
  Management - CULTURAL CONTROL - After harvest: Collect plant remains and burn them, or dig them deeply into the soil.
  ```


- `tomato_leaf_mold-0008` — **management**

  ```text
  Management - CULTURAL CONTROL - RESISTANT VARIETIES: Leaf-mould resistant varieties are available. However, the fungus mutates readily (there are at least 12 races), and varieties may not be resistant to them all.
  ```


- `tomato_leaf_mold-0009` — **management**

  ```text
  Management - CULTURAL CONTROL - CHEMICAL CONTROL: The cool, wet, conditions in Pacific island countries favour the disease such that fungicides are needed to give adequate control. The products to use are chlorothalonil, copper oxychloride or mancozeb. Treatment should start when the yellow spots are first seen, and continue at 10-14-day intervals until 3-4 weeks before last harvest. It is important to spray both sides of the leaves. AUTHORS Helen Tsatsia & Grahame Jackson Photo 3 Kohler F, Pellegrin F, Jackson G, McKenzie E (1997) Diseases of cultivated crops in Pacific Island countries. South Pacific Commission. Pirie Printers Pty Limited, Canberra, Australia.
  ```


#### Tomato / Septoria leaf spot — symptoms: true, management: true


- `tomato_septoria_leaf_spot_tnau-0001` — **symptoms**

  ```text
  Symptoms: Horticultural crops :: Vegetables:: Tomato Septoria Leaf Spot:Septoria lycopersici Small, round to irregular spots with grey centre and dark margin on leaves. Spots coalesce and leaves are blighted. Complete defoliation. Stems and flowers are affected. Irregular spots on leaves Leaf spots Causal Organism – Septoria lycopersici Speg. Mycelium : Hyaline and septate Fruiting body : Pycnidium: globose, without distinct ostiole Pathogen: Pycnidiospore : filiform, septate, hyaline
  ```


- `tomato_septoria_leaf_spot_tnau-0002` — **spread**

  ```text
  Survival and Mode of Spread: Survival: Infected plant debris Primary spread: Mycelium or conidia Secondary spread: Conidia through rain splash or wind Favourable conditions High humidity . Integrated Disease Management
  ```


- `tomato_septoria_leaf_spot_tnau-0003` — **management**

  ```text
  Cultural: Removal and destruction of affected plant parts
  ```


- `tomato_septoria_leaf_spot_tnau-0004` — **management**

  ```text
  Biological : Seed treatment :Trichoderma asperellum @ 4g/kg seeds
  ```


- `tomato_septoria_leaf_spot_tnau-0005` — **management**

  ```text
  Chemical: Fluxapyroxad 250 g/l + Pyraclostrobin 250 g/l SC - 200-250 ml/ha.
  ```


#### Tomato / Spider mites Two-spotted spider mite — symptoms: true, management: true


- `tomato_spider_mites-0001` — **symptoms**

  ```text
  DESCRIPTION: Stippling on tomato foliage and fruit. Berry crops Corn Cucurbits Hemp Legumes Onions Root crops Solanaceae crops Many weeds, fruit trees, and ornamentals Adults are tiny, with a yellowish-clear body and two dark spots on either side of its back. Eggs are very small, spherical, translucent initially, and turn opaque as they age. All life stages most frequently occur on the undersides of leaves.
  ```


- `tomato_spider_mites-0002` — **spread**

  ```text
  BIOLOGY: Egg | Larvae | Nymph | Adult Spider mites overwinter as adults in the ground cover and weed residue. They become active in spring and begin feeding on weeds before laying eggs. Females are capable of laying large quantities of eggs during their lifespan, which can lead to rapid population growth. The time it takes for spider mites to develop is heavily influenced by temperature. In the hot summer months, a generation may be completed in as few as 10 to 14 days. This can lead to 8 or more generations occurring each year.
  ```


- `tomato_spider_mites-0003` — **symptoms**

  ```text
  SYMPTOMS: Stippled (small yellow spots) leaves. Generalized bronzing or reddish discoloration on foliage and stems. Foliar die-back. Reduced plant vigor. Premature leaf drop. Plants appear dirty or dusty, especially when webbing is present.
  ```


- `tomato_spider_mites-0004` — **detection**

  ```text
  SCOUTING: Monitor for injury symptoms (leaf stippling) during hot, dry conditions. Check the undersides of leaves for tiny black specks of debris and slow-moving mites with a hand lens. Shake stems over paper or cloth tray and watch for tiny moving dots (spider mites).
  ```


- `tomato_spider_mites-0005` — **management**

  ```text
  GENERAL MANAGEMENT: Keep plants healthy, especially during times of drought. Stressed plants are more susceptible to spider mite damage. Use a strong stream of water from a hose-end nozzle to physically wash mites off infested plants. Avoid using malathion and pyrethroid insecticides for other pests, as these stimulate spider mite reproduction. Prevent dust from settling on foliage as this promotes spider mite survival. Attract and conserve natural enemies, including predatory mites, lacewings, and ladybugs. An organic option is insecticidal soap, and there are many brands for sale in garden centers and farm stores. The spray must come into contact with the mites, so thoroughly spray the tops and bottoms of leaves.
  ```


- `tomato_spider_mites-0006` — **management**

  ```text
  GENERAL MANAGEMENT: The spray must come into contact with the mites, so thoroughly spray the tops and bottoms of leaves. Spray at night to reduce risk of the soap harming the plants in hot weather. Click hereto reference insecticide options for small-scale use on tomato and other solanaceous crops. Click here to reference insecticide options for commercial use on tomato and other solanaceous crops. Always verify that the product you are using is labeled for the intended plant. Precautionary Statement: Utah State University and its employees are not responsible for the use, misuse, or damage caused by application or misapplication of products or information mentioned in this document.
  ```


- `tomato_spider_mites-0007` — **management**

  ```text
  GENERAL MANAGEMENT: Precautionary Statement: Utah State University and its employees are not responsible for the use, misuse, or damage caused by application or misapplication of products or information mentioned in this document. All pesticides are labeled with ingredients, instructions, and risks, and not all are registered for edible crops. “Restricted use” pesticides may only be applied by a licensed applicator. The pesticide applicator is legally responsible for proper use. USU makes no endorsement of the products listed in this publication.
  ```


#### Tomato / Target Spot — symptoms: true, management: true


- `tomato_target_spot-0001` — **symptoms**

  ```text
  Symptoms & Life Cycle: Tomato target spot (163) Target spot, leaf spot Corynespora cassiicola Widespread. In tropical countries. Asia, Africa, North, South and Central America, the Caribbean, Europe, Oceania. It is recorded on tomato from Fiji, Niue, Samoa, Solomon Islands, Tonga, and Vanuatu. Tomato, papaya (see Fact Sheet no. 300), cucumber (see Fact Sheet no. 189), legumes and probably weeds. The disease starts on the older leaves and spreads upwards. The first signs are irregular-shaped spots (less than 1 mm) with a yellow margin (Photo 1). Some of the spots enlarge up to 10 mm and show characteristics rings, hence the name of 'target spot' (larger spots Photos 1&2).
  ```


- `tomato_target_spot-0002` — **symptoms**

  ```text
  Symptoms & Life Cycle: Some of the spots enlarge up to 10 mm and show characteristics rings, hence the name of 'target spot' (larger spots Photos 1&2). Spread to all leaflets and to other leaves is rapid (Photo 3), causing the leaves to turn yellow, collapse and die (Photo 4). Spots also occur on the stems. They are long and thin. Small light brown spots with dark margins may also occur on the fruit. The spores are spread by wind-blown rain, and if windy wet weather continues for a few days, spread is fast and plants lose their leaves quickly. The source of the fungus is from other crops, the remains of the previous crop and, perhaps, other host species.
  ```


- `tomato_target_spot-0003` — **symptoms**

  ```text
  Symptoms & Life Cycle: The source of the fungus is from other crops, the remains of the previous crop and, perhaps, other host species. The fungus is very common on papaya leaves causing angular, light brown or grey spots, 2 mm diameter, sometimes surrounded by a yellow margin; the centres of the spots often fall out producing a 'shot-hole' effect (Photo 5). It is also a disease of cucumber (see Fact Sheet no. 189).
  ```


- `tomato_target_spot-0004` — **impact**

  ```text
  Impact: The fungus causes plants to lose their leaves; it is a major disease. If infection occurs before the fruit has developed, yields are low. This is a common disease on tomato in Pacific island countries. The disease occurs in the screen house and in the field.
  ```


- `tomato_target_spot-0005` — **detection**

  ```text
  Detection & Inspection: Look for the disease on the bottom leaves. Look for tiny brown spots with yellow margins. Look for larger spots up to 10 mm that have ring patterns. Spots may be present on the stems and on the fruit.
  ```


- `tomato_target_spot-0006` — **management**

  ```text
  Management - Before planting: Cultural control is important. The following should be done: Do not plant new crops next to older ones that have the disease. Plant as far as possible from papaya, especially if leaves have small angular spots (Photo 5). Check all seedlings in the nursery, and throw away any with leaf spots.
  ```


- `tomato_target_spot-0007` — **management**

  ```text
  Management - During growth: Remove a few branches from the lower part of the plants to allow better airflow at the base. Remove and burn the lower leaves as soon as the disease is seen, especially after the lower fruit trusses have been picked. Keep plots free from weeds, as some may be hosts of the fungus. Do not use overhead irrigation; otherwise, it will create conditions for spore production and infection.
  ```


- `tomato_target_spot-0008` — **management**

  ```text
  Management - After harvest: Collect and burn as much of the crop as possible when the harvest is complete. Practise crop rotation, leaving 3 years before replanting tomato on the same land.
  ```


- `tomato_target_spot-0009` — **management**

  ```text
  Management - RESISTANT VARIETIES: Trials have been done in Solomon Islands with lines of tomatoes from AVRDC (now known as The World Vegetable Center). One variety has been released and this has some tolerance to the disease, BUT is not resistant. It has the number CLN2585D.
  ```


- `tomato_target_spot-0010` — **management**

  ```text
  Management - CHEMICAL CONTROL: Warm wet conditions favour the disease such that fungicides are needed to give adequate control. The products to use are chlorothalonil, copper oxychloride or mancozeb. Treatment should start when the first spots are seen and continue at 10-14-day intervals until 3-4 weeks before last harvest. It is important to spray both sides of the leaves.
  ```


#### Tomato / Tomato Yellow Leaf Curl Virus — symptoms: true, management: true


- `tomato_leaf_curl_tnau-0001` — **management**

  ```text
  Horticultural crops :: Vegetables:: Tomato Leaf curl : Tomato leaf curl virus Field Diagnostic Symptoms Severe stunting of plants Downward rolling and crinkling of the leaves Older leaves become leathery and brittle Shortening of internodes Appearence of more lateral branches - bushy appearance Infected plant Downward curling of leaf Causal organism - Tomato leaf curl virus (TLCV)
  ```


- `tomato_leaf_curl_tnau-0002` — **spread**

  ```text
  Vector : Whiteflies –Bemisia tabaci
  ```


- `tomato_leaf_curl_tnau-0003` — **spread**

  ```text
  Survival and Mode of Spread - Primary spread: Whiteflies.
  ```


- `tomato_leaf_curl_tnau-0004` — **spread**

  ```text
  Secondary spread: Movement of infected plants Integrated Disease Management Raising nursery in protected condition Growing Sorghum, Maize or Bajra as barrier crop Use of disease free seeds Yellow sticky traps @ 5nos./ac. Remove alternate weed host - Abutilon indicum Spraying Dimethoate 30 EC @ 200 ml/ac or Methyl demeton 25 EC @ 200 ml/ac or Thiamethoxam 25 WG @ 200 g/ac or Imidacloprid 17.8 SL @ 200 ml/ac
  ```


#### Tomato / Tomato mosaic virus — symptoms: true, management: true


- `tomato_mosaic_virus-0001` — **spread**

  ```text
  BIOLOGY: Foliar Symptoms on Tobacco Tomato Eggplant Pepper Tobacco Mosaic Virus (TMV) and Tomato Mosaic Virus (ToMV) are Tobamoviruses spread by seed, artificial grafting, human handling, and tobacco products. The virus is a concern throughout the growing season. Infection occurs when the virus enters the plant through wounds as small as torn plant hairs. TMV, ToMV, PMMoV, and TMoMV are seedborne. Overwinters in seed coats, plant debris, perennial (weedy) hosts, and soil.
  ```


- `tomato_mosaic_virus-0002` — **symptoms**

  ```text
  SYMPTOMS: A wide range of symptoms include abnormally shaped fruit, fruit lesions, reduced fruit size, distorted growing points, abnormal color (often yellowing), form, and patterns on leaves, distorted stems, and distortion and dwarfing of the plant as a whole.
  ```


- `tomato_mosaic_virus-0003` — **management**

  ```text
  GENERAL MANAGEMENT: TMV and ToMV are widespread in Utah tomato production and can survive for up to 50 years in plant debris and for weeks to months on trellises or wooden stakes. Watch for symptoms throughout the growing season. Symptoms vary depending on the age of the infected plant, environmental conditions, virus strain, and genetic background of the host plant. Remove infected plants immediately. Source certified disease-free seed. Grow resistant varieties. There are no chemical controls for TMV and ToMV. Precautionary Statement: Utah State University and its employees are not responsible for the use, misuse, or damage caused by application or misapplication of products or information mentioned in this document.
  ```


- `tomato_mosaic_virus-0004` — **management**

  ```text
  GENERAL MANAGEMENT: Precautionary Statement: Utah State University and its employees are not responsible for the use, misuse, or damage caused by application or misapplication of products or information mentioned in this document. All pesticides are labeled with ingredients, instructions, and risks, and not all are registered for edible crops. “Restricted use” pesticides may only be applied by a licensed applicator. The pesticide applicator is legally responsible for proper use. USU makes no endorsement of the products listed in this publication.
  ```


Question-specific offline assertions:

- Tomato Target Spot — “what is the impact”: context includes `tomato_target_spot-0004` (Impact).

- Tomato Target Spot — “which fungicides can I use”: context includes `tomato_target_spot-0010` (Chemical Control).

- Tomato Target Spot — “what should I do before planting”: context includes `tomato_target_spot-0006` (Before planting).

- Tomato Target Spot — “is this safe for organic certification”: the complete Target Spot document is present, but it contains no organic-certification assurance; prompt includes the required decline rule. The resistant-variety passage is not treated as certification evidence.

- Apple Scab — “which fungicide should I spray and when”: context includes `apple_scab_tnau-0002` (Management, including the fungicide schedule).

- Corn Northern Leaf Blight: retrieval status `no_reference_document`, zero chunks, advisory status `no_verified_reference`; the fake model call count increased by zero.

- Multi-turn check: four consecutive Target Spot follow-ups retained the same session and complete context; conversation history grew from 2 to 10 messages. The Apple follow-up likewise retained its initial context and history. The fake model recorded 16 total invocations for the 11 initial covered-class prompts and five follow-ups, and made no network calls.


Offline test limitation: the placeholder model verifies the exact prompt/context and refusal instruction, not Gemini’s generated wording. Live Gemini verification and redeployment are tracked below.

### Runtime and live-check addendum — 2026-10-14

- Rebuilt the `ai-service` Docker image with the updated class-keyed exact-coverage retrieval and follow-up prompt behavior. Recreated the AI service, backend, frontend, and started PostgreSQL as needed. The app stack was confirmed healthy earlier in this session: the frontend-proxied `/api/health` returned HTTP 200 with `{"aiService":"ok","status":"ok"}`. No Spring Boot or React source was changed.
- Browser-path verification used the held-out Tomato Target Spot test image `Tomato___Target_Spot/1ecca1a2-c028-4cf8-8861-6fcb365bffca___Com.G_TgS_FL 9707.JPG` via the upload UI. CNN classification reached the advisory step, but Gemini returned HTTP 503 `UNAVAILABLE` (temporary high demand). The UI showed: “The AI advisory service is temporarily unavailable. No diagnosis was saved; please try again shortly.” No diagnosis was saved, so this attempt did not verify a successful browser diagnosis/follow-up. This was a 503, not a quota 429; no further live Gemini calls were made after the failure.
- Logs also confirmed the class-keyed coverage guard returns all 27 uncovered classes as `no_reference_document` without matches. The retrieval model remained uninitialized for these lookups, including Corn Northern Leaf Blight, so the guard does not invoke embedding or the LLM.
- The in-container score audit and offline context assertions above remain the completed evidence for the retrieval change; live Gemini wording remains unverified due to the 503.
