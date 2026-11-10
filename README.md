\# The Relay — Research Assistant and Load-Testing System



\## Overview



The Relay is a research assistant pipeline built for the Vaani ML Engineering assignment.



It retrieves relevant passages from three specified research papers, uses a hosted language model through the Groq API to generate answers, and records request-level measurements.



The project also includes a local stand-in model service to simulate latency, streaming, failures, timeouts, concurrency limits, and request-rate limits.



\## Research Papers



The system uses these paper versions:



1\. \*\*Attention Is All You Need\*\* — arXiv:1706.03762, v7

2\. \*\*Moshi: a speech-text foundation model for real-time dialogue\*\* — arXiv:2410.00037, v1

3\. \*\*Dynamic Chunking for End-to-End Hierarchical Sequence Modeling\*\* — arXiv:2507.07955, v2



\## Architecture



The pipeline has the following stages:



1\. \*\*Ingestion:\*\* Extract text from PDF pages using PyMuPDF.

2\. \*\*Chunking:\*\* Clean extracted text and split it into overlapping character-based passages.

3\. \*\*Retrieval:\*\* Tokenize the query and passages, then rank passages using BM25.

4\. \*\*Answer generation:\*\* Send retrieved evidence to the Groq-hosted model.

5\. \*\*Grounding:\*\* Require answers to use paper evidence and citations; refuse unsupported questions.

6\. \*\*Logging:\*\* Record request metadata, latency, token counts, status, and answer grades.



\## Technology Stack



\- Python

\- PyMuPDF

\- rank-bm25

\- Groq API

\- FastAPI and Uvicorn

\- HTTPX

\- pandas

\- pytest

\- python-dotenv



\## Project Structure



```text

The\_Relay/

├── src/

│   ├── answer.py

│   ├── evaluate\_retrieval.py

│   ├── ingest.py

│   ├── list\_models.py

│   ├── retriever.py

│   ├── standin.py

│   ├── test\_groq.py

│   ├── test\_groq\_load.py

│   ├── test\_groq\_recovery.py

│   ├── test\_standin\_load.py

│   ├── test\_standin\_modes.py

│   └── test\_standin\_rpm.py

├── data/

│   ├── papers/

│   │   ├── attention\_is\_all\_you\_need\_v7.pdf

│   │   ├── moshi\_v1.pdf

│   │   └── dynamic\_chunking\_v2.pdf

│   └── passages.json

├── experiments/

│   ├── groq\_load\_results.csv

│   ├── groq\_load\_results\_v2.csv

│   ├── groq\_recovery\_probe.csv

│   ├── groq\_stream\_validation.csv

│   ├── quality\_answers.jsonl

│   ├── quality\_questions.json

│   ├── retrieval\_comparison.csv

│   ├── retrieval\_results.csv

│   ├── standin\_load\_results.csv

│   ├── standin\_load\_results\_v2.csv

│   ├── standin\_modes\_results.csv

│   └── standin\_rpm\_results.csv

├── tests/

│   ├── test\_ingest.py

│   └── test\_retriever.py

├── conversation\_history/

├── .env.example

├── .gitignore

├── README.md

├── requirements.txt

└── results.csv

```



\## Setup



Python 3.14.7 was used during development.



Create and activate a virtual environment:



```powershell

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

```



Install dependencies:



```powershell

pip install -r requirements.txt

```



Create a `.env` file in the project root:



```env

GROQ\_API\_KEY=your\_groq\_api\_key

GROQ\_MODEL=openai/gpt-oss-20b

```



Use your own Groq API key. Do not commit or share the `.env` file.



The `.env.example` file provides a placeholder configuration. Copy it to `.env` and replace the placeholder with your own API key.



\## Running the Pipeline



\### 1. Extract passages from PDFs



```powershell

python src/ingest.py

```



This creates `data/passages.json`.



\### 2. Test retrieval



```powershell

python src/retriever.py

```



\### 3. Generate an answer



```powershell

python src/answer.py

```



Enter a question ID and research question when prompted.



Generated answer records are stored in `experiments/quality\_answers.jsonl`, and request-level results are appended to `results.csv`.



\## Running the Stand-in Service



Start the local FastAPI service:



```powershell

uvicorn src.standin:app --host 127.0.0.1 --port 8000

```



Keep this terminal running.



In another terminal, check its health:



```powershell

Invoke-RestMethod http://127.0.0.1:8000/health

```



The service supports normal, slow, timeout, error, and streaming modes, along with simulated concurrency and RPM limits.



\## Running Experiments



Run the relevant scripts from the project root:



```powershell

python src/test\_groq.py

python src/test\_groq\_load.py

python src/test\_groq\_recovery.py

python src/test\_standin\_load.py

python src/test\_standin\_modes.py

python src/test\_standin\_rpm.py

python src/evaluate\_retrieval.py

```



The experiment scripts save their measurements under `experiments/`.



The stand-in's limits and delays are simulation settings, not measurements of Groq's actual limits.



\## Running Automated Tests



Run the complete test suite:



```powershell

python -m pytest -v

```



The current automated suite contains 13 tests covering text cleaning, chunking, passage metadata, PDF-ingestion behaviour, tokenization, retrieval, and input validation.



Latest recorded result: \*\*13 passed\*\*.



\## Results and Evaluation



The project maintains:



\- `results.csv`: consolidated request-level results.

\- `experiments/quality\_questions.json`: the 15-question evaluation set.

\- `experiments/quality\_answers.jsonl`: generated answers and retrieved evidence metadata.

\- Retrieval comparison and load-test CSV files: experiment-specific measurements.



The revised manual quality evaluation shows:



\- **Supported questions:** 12/12 acceptable answers (100%): 10 fully correct and 2 correct with minor qualifications (Q03 and Q06).

\- **Unsupported questions:** 3/3 correctly refused (100%).

\- No unsupported question was incorrectly answered.

\- No supported question was refused.



The CSV uses the required grades `correct` and `refused_correctly`; the two minor qualifications are described separately here. These results are based on manual review of generated answers and their citations, not proof of general answer accuracy.



\### Load-Test Summary



\*\*Real Groq service (`openai/gpt-oss-20b`):\*\*



| Scenario | Requests | Successful | Rate-limited |

|---|---:|---:|---:|

| Steady | 8 | 8 | 0 |

| Burst | 12 | 12 | 0 |

| Sustained overload | 20 | 11 | 9 |

| \*\*Total\*\* | \*\*40\*\* | \*\*31\*\* | \*\*9\*\* |



The sustained-overload test produced HTTP 429 responses. The provider error reported an RPM limit of 30 for the tested model and service tier.



\*\*Local stand-in service:\*\*



| Scenario | Requests | Successful | Concurrency errors |

|---|---:|---:|---:|

| Steady | 8 | 8 | 0 |

| Burst | 12 | 5 | 7 |

| Sustained overload | 20 | 5 | 15 |

| \*\*Total\*\* | \*\*40\*\* | \*\*18\*\* | \*\*22\*\* |



The stand-in was configured with a 30 RPM limit and a maximum of 5 concurrent requests. These are simulation settings, not measured Groq limits.



The tests are small experiments under specific conditions, not a comprehensive capacity assessment.



\## Known Limitations



\- Character-based chunking can split sentences and does not preserve semantic boundaries.

\- PDF text extraction may contain formatting artefacts or noisy text.

\- Hyphenation cleanup can remove meaningful hyphens in some cases.

\- BM25 is lexical retrieval and does not establish semantic relevance or factual support.

\- A positive BM25 score does not prove that a passage supports the question.

\- The stand-in service uses artificial delays and approximate token counts.

\- The stand-in's RPM and concurrency settings are configurable simulation values.

\- The stand-in rejects excess concurrent requests rather than implementing a realistic provider queue.

\- The stand-in does not reproduce all provider-side rate-limit, retry, or recovery behaviour.

\- Groq measurements represent the tested model, account/service tier, prompts, and experiment windows; they should not be generalized to all users or conditions.

\- The revised manual evaluation found acceptable answers for all 12 supported questions and correct refusals for all 3 unsupported questions. Q03 and Q06 had minor qualifications, so citation coverage and precise wording remain areas for improvement.



\## Security



\- Keep API credentials in `.env`.

\- Never include `.env` in the submission folder.

\- Do not publish API keys in source files, reports, screenshots, or conversation-history exports.

\- Use `.env.example` only for placeholder configuration.



\## Reproducibility



The source code, paper PDFs, extracted passages, experiment scripts, raw experiment CSVs, consolidated results, and dependency versions are included to support review and reproduction.

