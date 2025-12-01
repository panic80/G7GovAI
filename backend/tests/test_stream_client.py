import os
import requests
import json


def test_stream():
    url = "http://localhost:8000/agent/govlens/stream"
    headers = {
        "Content-Type": "application/json",
        "X-GovAI-Key": os.getenv("GOVAI_API_KEY", "test-key"),
    }

    data = {"query": "what is bill c3", "language": "en"}

    print("Connecting to stream...")
    try:
        with requests.post(url, json=data, headers=headers, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    print(f"Received Chunk: {decoded_line[:100]}...")
                    # Parse to check contents
                    try:
                        json_data = json.loads(decoded_line)
                        if "final_answer" in json_data:
                            print("!!! FOUND FINAL ANSWER !!!")
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"Stream Error: {e}")


if __name__ == "__main__":
    test_stream()
