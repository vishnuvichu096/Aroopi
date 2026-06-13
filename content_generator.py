import random
import json
import time
import os
import requests
import re

STATE_FILE = "story_state.json"

TOPICS = [
    "A cursed ancestral house (tharavadu) in Kadamattom where a yakshi resides",
    "A mysterious black magician (Odiyan) who can shape-shift into animals at night in a Palakkad village",
    "A cursed temple in Wayanad where the deity's eyes glow red at midnight",
    "A traveler stranded in a foggy, deserted tea estate of Vagamon who meets a mysterious old man",
    "A snake charmer who unleashes an ancient curse in a village near Alappuzha backwaters",
    "A haunted forest path in Athirappilly where people hear distant whispers calling their name",
    "A cursed mirror inside a grand old palace in Thiruvananthapuram",
    "A haunted well in a remote village in Malappuram that starts calling out names at midnight",
    "A mysterious train that stops at an abandoned station in Shoranur only on full moon nights",
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
        outro_instruction = "This is the final Part 10. Bring the story to a chilling, definitive climax in Malayalam."
    else:
        outro_instruction = "The final segment of the script MUST end with the hook: 'അടുത്ത ഭാഗത്തിനായി ഇപ്പോൾ തന്നെ ഫോളോ ചെയ്യൂ.'"

    prompt = f"""You are an expert storyteller for a Suspense and Horror YouTube Shorts channel called "Aroopi" based in Kerala, India.
{narrative_instruction}

CRITICAL INSTRUCTIONS:
1. MALAYALAM SCRIPT SEGMENTS: Write exactly 5 script segments (sentences/phrases) in chronological order that tell this part of the story. The script segments MUST be written in the MALAYALAM language (using Malayalam script).
   - Word Count: Total spoken word count should be around 115-130 Malayalam words.
   - Character names and settings: Use common Kerala names (like Unni, Devi, Madhavan, Ammu, Bhaskaran, etc.) and specify locations in Kerala.
   - Vocabulary: Use simple, standard, and highly engaging Malayalam words that are easy for any native speaker to understand. Do not use complex, obscure, or overly formal words.
   - SEGMENT 1 (First 5 seconds): This MUST start with an immediate, jaw-dropping, terrifying cliffhanger or creepy hook in Malayalam (e.g. a sudden shocking revelation, bizarre mystery, or intense moment) that instantly grabs the viewer's attention. Do not start with slow setting descriptions.
   - SEGMENTS 2-4: Build the setting, details, and rising suspense in Malayalam.
   - SEGMENT 5: Delivers a final suspense builder/hook in Malayalam.
2. NO LEAKED DIRECTIONS: The script segments must contain ONLY the spoken Malayalam words. Do NOT include '[image]', 'visual:', 'Narrator:', or similar.
3. OUTRO: {outro_instruction}
4. ENGLISH IMAGE PROMPTS: Write exactly 5 image prompts matching each script segment.
   - Language: The image prompts MUST be written in ENGLISH (as the image generation models only understand English).
   - Kerala Aesthetic: Each image prompt must specify a realistic Kerala aesthetic (e.g. traditional Kerala ancestral houses/tharavadus, coconut palms, dark monsoon rainy skies, traditional attire like Mundu or Kasavu saree, local South Indian facial features, and dense tropical foliage) to match the location of the story.
   - Format: Portrait composition (9:16 aspect ratio), cinematic lighting, dark mood.
5. STORY TITLE: Generate a catchy, terrifying title for the entire 10-part story in MALAYALAM (if Part 1) or reuse the title '{state['story_name']}' (if Part > 1).
6. SUMMARY: Write a brief 1-sentence summary of what happens in this part in ENGLISH (to help the AI write the next part tomorrow).

Return ONLY a raw JSON object in this exact format (no markdown code blocks, no leading/trailing text):
{{
    "story_name": "Name of the story in Malayalam",
    "script_segments": [
        "Narration for segment 1 in Malayalam...",
        "Narration for segment 2 in Malayalam...",
        "Narration for segment 3 in Malayalam...",
        "Narration for segment 4 in Malayalam...",
        "Narration for segment 5 in Malayalam..."
    ],
    "image_prompts": [
        "English portrait horror prompt matching segment 1 with Kerala aesthetic...",
        "English portrait horror prompt matching segment 2 with Kerala aesthetic...",
        "English portrait horror prompt matching segment 3 with Kerala aesthetic...",
        "English portrait horror prompt matching segment 4 with Kerala aesthetic...",
        "English portrait horror prompt matching segment 5 with Kerala aesthetic..."
    ],
    "part_summary": "1-sentence summary of this part in English..."
}}"""

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

    parsed = None
    success = False

    # ── [1/2] Try OpenAI API (Primary) ────────────────────────────────────────
    if OPENAI_API_KEY:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a creative horror writer that outputs JSON matching the exact schema requested."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  >> Querying OpenAI API... (Attempt {attempt}/{max_retries})")
                response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    raw_text = response.json()["choices"][0]["message"]["content"].strip()
                    parsed = json.loads(raw_text)
                    success = True
                    break
                else:
                    print(f"  [WARN] OpenAI API HTTP status: {response.status_code}: {response.text[:100]}")
                    time.sleep(2)
            except Exception as e:
                print(f"  [WARN] OpenAI attempt failed: {e}")
                time.sleep(2)

    # ── [2/2] Try Gemini API Fallback ─────────────────────────────────────────
    if not success and GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  >> Querying Gemini API... (Attempt {attempt}/{max_retries}) (Fallback)")
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    parsed = json.loads(raw_text)
                    success = True
                    break
                else:
                    print(f"  [WARN] Gemini API HTTP status: {response.status_code}: {response.text[:100]}")
                    time.sleep(2)
            except Exception as e:
                print(f"  [WARN] Gemini attempt failed: {e}")
                time.sleep(2)

    if not success or not parsed:
        raise RuntimeError("Failed to generate story script content from both Gemini and OpenAI APIs.")

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
