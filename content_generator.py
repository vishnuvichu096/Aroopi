import random
import json
import time
import os
import requests
import re

STATE_FILE = "story_state.json"

TOPICS = [
    "A mysterious disappearance of an entire town overnight",
    "A haunted mirror that shows tomorrow's death",
    "A deep space signal that plays a human lullaby",
    "An abandoned amusement park that activates at midnight",
    "A man who wakes up inside his own funeral",
    "A woman who finds her own obituary written 3 years in the future",
    "A lighthouse keeper who realizes the ships aren't really ships",
    "A child's imaginary friend who starts leaving physical evidence",
    "A doctor who discovers all his patients share the same recurring nightmare",
    "A hotel room that exists on no floor of the building",
]

def load_story_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                # Ensure structure is valid
                if all(k in state for k in ["story_name", "topic", "current_part", "previous_summary"]):
                    return state
        except Exception as e:
            print(f"  [WARN] Failed to load story state: {e}")
    return None

def save_story_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        print(f"  [OK] Saved story state for Part {state['current_part']} of '{state['story_name']}'")
    except Exception as e:
        print(f"  [ERROR] Failed to save story state: {e}")

def sanitize_segment(text: str) -> str:
    """Cleans up narration segments to ensure no prompting leaks into the voiceover."""
    # Remove bracketed and parenthesized text like [Image prompt], (narrator: ...)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'\([^\)]*\)', '', text)
    # Remove any quotes or escape characters
    text = text.replace('"', '').replace("'", "").strip()
    return text

def generate_script_and_prompts():
    """
    Manages a 10-part serial story using local Mistral via Ollama.
    Returns: (story_name: str, current_part: int, script_segments: list[str], image_prompts: list[str])
    """
    state = load_story_state()
    
    if state and state.get("current_part", 1) > 10:
        print("\n  >> 10-part story series finished! Starting a new story...")
        state = None
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)

    if not state:
        selected_topic = random.choice(TOPICS)
        state = {
            "story_name": "", # Will be filled by Mistral
            "topic": selected_topic,
            "current_part": 1,
            "previous_summary": ""
        }
        print(f"  >> Starting a NEW 10-part series. Topic: {state['topic']}")
    else:
        print(f"  >> Continuing '{state['story_name']}' - Part {state['current_part']}/10")

    # Construct prompt based on current part
    if state["current_part"] == 1:
        narrative_instruction = (
            f"Write Part 1 of a 10-part horror story series about: {state['topic']}. "
            f"Start with a highly engaging, creepy hook. Establish the setting and introduce the mystery."
        )
    else:
        narrative_instruction = (
            f"Write Part {state['current_part']} of the 10-part horror story series '{state['story_name']}'. "
            f"The overall topic is: {state['topic']}. "
            f"In the previous part: '{state['previous_summary']}'. "
            f"Continue the narrative directly from that ending, building up the suspense further."
        )

    # Instructions for ending of script segment
    if state["current_part"] == 10:
        outro_instruction = "This is the final Part 10. Bring the story to a chilling, definitive climax."
    else:
        outro_instruction = "The final segment of the script MUST end with the hook: 'Follow and subscribe for the next part.'"

    prompt = f"""You are an expert storyteller for a Suspense and Horror YouTube Shorts channel called "I'm Faceless".
{narrative_instruction}

CRITICAL INSTRUCTIONS:
1. SCRIPT SEGMENTS: Write exactly 5 script segments (sentences/phrases) in chronological order that tell this part of the story. Total spoken word count should be around 100-120 words.
2. NO LEAKED DIRECTIONS: The script segments must contain ONLY the spoken words. Do NOT include '[image]', 'visual:', 'Narrator:', or similar.
3. OUTRO: {outro_instruction}
4. IMAGE PROMPTS: Write exactly 5 image prompts matching each script segment. Each prompt must be hyper-specific, cinematic, and dramatic — describing eerie lighting, dark mood, and portrait composition (9:16 aspect ratio).
5. STORY TITLE: Generate a catchy, terrifying title for the entire 10-part story (if Part 1) or reuse the title '{state['story_name']}' (if Part > 1).
6. SUMMARY: Write a brief 1-sentence summary of what happens in this part, to help write the next part tomorrow.

Return ONLY a raw JSON object in this exact format (no markdown code blocks, no leading/trailing text):
{{
    "story_name": "Name of the story",
    "script_segments": [
        "Narration for segment 1...",
        "Narration for segment 2...",
        "Narration for segment 3...",
        "Narration for segment 4...",
        "Narration for segment 5..."
    ],
    "image_prompts": [
        "Portrait horror prompt matching segment 1...",
        "Portrait horror prompt matching segment 2...",
        "Portrait horror prompt matching segment 3...",
        "Portrait horror prompt matching segment 4...",
        "Portrait horror prompt matching segment 5..."
    ],
    "part_summary": "1-sentence summary of this part..."
}}"""

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY in environment variables.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  >> Querying Gemini API... (Attempt {attempt}/{max_retries})")
            response = requests.post(url, json=payload, timeout=45)

            if response.status_code == 200:
                raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                try:
                    parsed = json.loads(raw_text)
                    
                    story_name = parsed.get("story_name", "").strip() or state["story_name"] or "Untitled Horror"
                    script_segments = [sanitize_segment(s) for s in parsed.get("script_segments", [])]
                    image_prompts = parsed.get("image_prompts", [])
                    part_summary = parsed.get("part_summary", "").strip()

                    # Validations
                    if len(script_segments) != 5 or len(image_prompts) != 5:
                        raise ValueError(f"Got {len(script_segments)} segments and {len(image_prompts)} prompts. Need exactly 5 of each.")
                    
                    # Update and save state
                    state["story_name"] = story_name
                    state["previous_summary"] = part_summary
                    state["current_part"] += 1
                    save_story_state(state)

                    return story_name, state["current_part"] - 1, script_segments, image_prompts

                except (json.JSONDecodeError, ValueError, KeyError) as parse_err:
                    print(f"  [WARN] Parsing error: {parse_err}")
                    print(f"  Raw output preview: {raw_text[:300]}")
                    time.sleep(5)
            else:
                print(f"  [ERROR] Gemini API HTTP status: {response.status_code}: {response.text[:200]}")
                time.sleep(5)

        except Exception as e:
            print(f"  [ERROR] Request exception: {e}")
            time.sleep(5)

    raise RuntimeError("Failed to generate content after all retries.")
