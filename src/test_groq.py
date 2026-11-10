import os
import time

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL")

if not api_key or not model:
    raise RuntimeError("Check GROQ_API_KEY and GROQ_MODEL in .env")

client = Groq(api_key=api_key)

print(f"Testing model: {model}")
print("Sending request to Groq...\n")

start_time = time.perf_counter()
first_token_time = None
response_text = ""
input_tokens = 0
output_tokens = 0

stream = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Explain what self-attention means in one simple sentence."
        }
    ],
    max_completion_tokens=250,
    stream=True,
)

for chunk in stream:
    if chunk.choices:
        content = chunk.choices[0].delta.content

        if content:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            response_text += content
            print(content, end="", flush=True)

    if chunk.usage:
        input_tokens = chunk.usage.prompt_tokens
        output_tokens = chunk.usage.completion_tokens

end_time = time.perf_counter()

print("\n\n--- Measurements ---")

if first_token_time is not None:
    print(
        f"Time to first token: "
        f"{(first_token_time - start_time) * 1000:.2f} ms"
    )
else:
    print("Time to first token: Not measured")


print(f"Total response time: {(end_time - start_time) * 1000:.2f} ms")
print(f"Input tokens: {input_tokens}")
print(f"Output tokens: {output_tokens}")
print("Status: OK")