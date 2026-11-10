\# AI Assistant Usage Disclosure



\## How I Used the Assistant



I used ChatGPT as a coding and debugging assistant during the development of The Relay. It helped me understand implementation requirements, draft and revise code, diagnose errors, develop tests, and organize experiment findings into technical documentation.



I executed the code and experiments locally and checked the outputs rather than treating generated suggestions as automatically correct.



\## Three Important Prompts



1\. \*\*"do in whole code"\*\*



&#x20;  I used this when I needed a complete, consistent replacement for a source file rather than separate code fragments. This helped me apply changes and verify the complete implementation.



2\. \*\*"before moving next, so tell about progess"\*\*



&#x20;  I used this to request progress checkpoints before moving to another assignment stage. This helped me track completed requirements and identify remaining work.



3\. \*\*"please by command, or verify"\*\*



&#x20;  I used this to request reproducible terminal commands and verification steps instead of relying only on explanations. This helped me check files, tests, and experiment outputs locally.



\## One AI Mistake I Caught



An initial assistant suggestion used `stream\_options={"include\_usage": True}` with the installed Groq SDK. The SDK raised a `TypeError` because that argument was unsupported in the installed configuration. I removed the argument and verified that streaming measurements could still be collected.



\## A Decision I Changed or Overruled



I do not recall a specific instance where I deliberately overruled an assistant recommendation. I independently checked suggested implementations and experiment results before accepting or changing them. I have not invented an example to fill this section.



\## My Own Contributions



My own work included:



\- Setting up the project structure and Python environment.

\- Obtaining the specified versions of the three research papers.

\- Configuring the Groq API key locally.

\- Running PDF ingestion and building the BM25 retrieval pipeline.

\- Running the answer-generation and quality-evaluation experiments.

\- Implementing and testing the FastAPI stand-in service.

\- Running the real Groq and stand-in load experiments.

\- Inspecting CSV results and checking the required output schema.

\- Manually reviewing and grading the 15 research answers.

\- Identifying implementation and test issues, applying corrections, and running the full test suite.

\- Reviewing the README and technical report.



ChatGPT assisted with suggestions and code drafting, but I ran the project, examined the results, and made the final decisions about what to include in the submission.

