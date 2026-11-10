# The Relay — Technical Report



## 1. What I built and why.



I built a Python research assistant that answers questions using three specified arXiv papers: \*Attention Is All You Need\* (v7), \*Moshi\* (v1), and \*Dynamic Chunking for End-to-End Hierarchical Sequence Modeling\* (v2).



The pipeline extracts PDF text using PyMuPDF, splits it into overlapping passages, retrieves relevant passages using BM25, and sends the retrieved evidence to Groq's hosted `openai/gpt-oss-20b` model. Answers are expected to include paper-page citations. The system also refuses questions when retrieval finds no lexical evidence.



I added request logging and a FastAPI stand-in service to investigate latency, streaming, failures, timeouts, concurrency, and request-rate limits.



## 2. The real service and my stand-in.



The real service was accessed through the Groq API. I disabled automatic retries (`max\_retries=0`) so that rate-limit responses could be observed directly.



The stand-in was implemented with FastAPI and Uvicorn. It supports normal, slow, timeout, error, and streaming modes, along with configurable limits of 30 requests per minute and five concurrent requests. It uses artificial delays and approximate word-based token counts. These settings are simulation parameters, not measurements of Groq.



## 3. Results.



I ran 40 requests against each service across steady, burst, and sustained-overload scenarios.



| Service and scenario | Requests | Successful | Limited/errors |

|---|---:|---:|---:|

| Groq — steady | 8 | 8 | 0 |

| Groq — burst | 12 | 12 | 0 |

| Groq — sustained overload | 20 | 11 | 9 |

| Stand-in — steady | 8 | 8 | 0 |

| Stand-in — burst | 12 | 5 | 7 |

| Stand-in — sustained overload | 20 | 5 | 15 |



The real service returned nine HTTP 429 responses during sustained overload. The stand-in rejected excess concurrent requests with synthetic concurrency errors.



For Groq, successful-request latency measurements were:



| Scenario (successful requests) | First-text p50 | First-text p95/p99 | Total p50 | Total p95/p99 |

|---|---:|---:|---:|---:|

| Steady (8) | 497.63 ms | 1631.49 ms | 549.92 ms | 1672.47 ms |

| Burst (12) | 797.04 ms | 1240.39 ms | 825.04 ms | 1313.37 ms |

| Overload (11) | 803.41 ms | 1922.20 ms | 839.94 ms | 1950.00 ms |



First-text latency measures the time until the Python client received its first non-empty visible text, not the model's internal first token. Percentiles use small samples, so p95 and p99 both equal the maximum observation in each scenario.



The stand-in's average successful-request latency was 278.89 ms in steady load, 493.67 ms in burst load, and 484.80 ms in sustained overload. Its separate mode tests also demonstrated slow responses, synthetic HTTP 503 errors, client timeouts, and streaming.



The 15-question manual quality evaluation produced acceptable answers for all 12 supported questions: 10 fully correct and 2 correct with minor qualifications (Q03 and Q06). All 3 unsupported questions were refused correctly. The required CSV schema records Q03 and Q06 as `correct`; their minor qualifications are retained in this report. These results describe this test set only.



## 4. Where the time goes.



BM25 retrieval was inexpensive in the local evaluation: average measured retrieval time was approximately 1.3–4.9 ms across the tested top-k settings. By comparison, Groq's observed total response times were generally hundreds of milliseconds and sometimes exceeded one second.



This suggests that model generation and network/service overhead dominate the observed end-to-end latency. The experiment did not separately measure provider-side queueing, model computation, or network time, so I cannot assign exact proportions to them.



## 5. When a limit is hit.



The Groq error explicitly reported a requests-per-minute limit of 30 for the tested model, organisation, and service tier. The response was HTTP 429 and suggested retrying after two seconds. A later probe received HTTP 200 about 286.92 seconds after the latest recorded 429, but returned no visible answer text. The exact recovery interval was therefore not established.



| Limit or behaviour | Groq measurement | Stand-in configuration or observation |
|---|---|---|
| Requests per minute | 30 RPM reported by provider | Synthetic limit: 30 requests per rolling 60 seconds |
| Tokens per minute | Not measured | Not modelled |
| Requests per day | Not measured | Not modelled |
| Tokens per day | Not measured | Not modelled |
| Concurrent requests | Provider limit not measured | Configured maximum: 5 in flight |
| Limit response | HTTP 429; provider suggested retry after 2 seconds | HTTP 429 for RPM; HTTP 503 for excess concurrency |
| Recovery | Exact recovery time not measured; later HTTP 200 probe had no visible answer text | Rolling-window behaviour; no provider recovery simulation |



The stand-in's limits are synthetic test settings, not claims about Groq's limits.



## 6. Retries.



Automatic Groq SDK retries were disabled to preserve the original provider responses and avoid hiding rate-limit behaviour. The experiments did not implement or benchmark a production retry policy.



A real deployment should consider bounded retries with exponential backoff and jitter for retryable failures, while respecting provider instructions and avoiding repeated requests that worsen overload.



## 7. What the person sees.



A user enters a question ID and research question. The application retrieves passages and either generates an evidence-based answer or returns a refusal when no passages have positive lexical scores.



The application records request IDs, timings, token counts, status, retrieval settings, and manually reviewed answer grades. A limitation is that a positive BM25 score does not guarantee that retrieved evidence actually supports the answer.



## 8. What I'm unsure about, what I left out, what I learned.



The experiments use small request samples and one Groq model/account configuration. They do not establish general provider capacity or behaviour under long-running production traffic.



The stand-in is deliberately simplified: it uses artificial delays, approximate token counts, immediate concurrency rejection, and does not reproduce provider-side queueing or retry behaviour. The recovery interval was not measured precisely.



The revised manual evaluation found acceptable answers for all 12 supported questions: 10 fully correct and 2 correct with minor qualifications (Q03 and Q06). All 3 unsupported questions were refused correctly. This small evaluation set does not establish general answer accuracy; citation coverage, evidence relevance, and careful refusal behaviour still require separate evaluation.



## Retrieval: quality versus cost



I compared BM25 retrieval with top-k values of 3, 5, and 8.



| Top-k | Supported questions with expected paper in results | Average retrieval time |

|---|---:|---:|

| 3 | 12/12 | 1.894 ms |

| 5 | 12/12 | 1.312 ms |

| 8 | 12/12 | 4.904 ms |



Top-5 was retained as the working default. All three settings retrieved the expected paper for the 12 supported questions, but this metric does not establish that every retrieved passage was relevant or sufficient. The top-8 timing was affected by a single 57.143 ms observation.



## How this library will mislead a naive retriever



BM25 relies on lexical overlap, not an understanding of meaning. The PDF extraction and character-based chunking can also introduce noisy passages, repetitive text, and broken sentence boundaries.



In the evaluation, all three unsupported questions still retrieved passages at each tested top-k setting. This demonstrates that a retriever can return apparently relevant material even when the library contains no evidence for the requested fact. A positive retrieval score must not be treated as proof of answerability.



## Your feedback on Vaani



The assignment provides a useful practical exercise combining document retrieval, hosted-model integration, load testing, measurement, and technical reporting. Requiring both real-service observations and a local stand-in encourages investigation beyond simply building a chatbot.



One improvement would be to provide an explicit example of the expected raw measurement format and clarify how provider-specific limits should be reported when some limits cannot be measured using a free-tier account.



## How I worked with the assistant



I used ChatGPT as a coding and debugging assistant for implementation guidance, error diagnosis, test development, and interpretation of experiment outputs. I ran the code and experiments locally, inspected the results, corrected issues, and manually reviewed and graded the generated answers.



Important prompts included asking for a complete code replacement when a file needed restructuring, requesting progress checkpoints before moving to the next stage, and asking for verification of the README and project files.



One AI mistake I caught was an incorrect test expectation around PDF dehyphenation: the implementation removed a line-break hyphen, but the initial test expected it to remain. I corrected the test after checking the actual behaviour. I also caught an unsupported `stream\_options` argument in an initial Groq SDK example and removed it after the SDK raised a `TypeError`.



My own work included setting up the project, obtaining the specified paper versions, configuring the API locally, running the ingestion and retrieval pipeline, conducting the real and stand-in experiments, checking the CSV outputs, running the automated tests, and manually evaluating the 15 answers.



**A specific recommendation I deliberately overruled or changed:** I do not recall a specific instance where I deliberately overruled an assistant recommendation. I independently checked suggested implementations and experiment results before accepting or changing them.

