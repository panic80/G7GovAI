import re
import json

raw_json = """
{
  "answer": "This is a complex answer with \"unescaped quotes\" inside it.\n\nAnd multiple paragraphs.",
  "lang": "en",
  "bullets": ["Point 1", "Point 2"],
  "citations": [],
  "confidence": 0.95,
  "abstained": false
}
"""

print("--- Testing Improved Rescue Logic ---")

# 1. Main Answer Regex
match = re.search(
    r'"answer"\s*:\s*"(.*?)"\s*,\s*"(?:lang|bullets|citations|confidence|abstained)"',
    raw_json,
    re.DOTALL,
)

rescued_confidence = 0.0
rescued_bullets = []

if match:
    rescued_answer = match.group(1)
    rescued_answer = rescued_answer.replace('"', '"').replace("\\n", "\n")
    print(f"Rescued Answer: {rescued_answer[:30]}...")

    # 2. Confidence Regex
    conf_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', raw_json)
    if conf_match:
        rescued_confidence = float(conf_match.group(1))
        print(f"Rescued Confidence: {rescued_confidence}")

    # 3. Bullets Regex
    bullets_match = re.search(r'"bullets"\s*:\s*(\[.*?\])', raw_json, re.DOTALL)
    if bullets_match:
        try:
            rescued_bullets = json.loads(bullets_match.group(1))
            print(f"Rescued Bullets: {rescued_bullets}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse bullets JSON: {e}")
else:
    print("Main regex failed")
