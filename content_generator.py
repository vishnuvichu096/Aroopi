import random
import json
import time
import os
import requests
import re

STATE_FILE = "story_state.json"

TOPICS = [
    # Kerala Folklore & Horror
    "A cursed ancestral house (tharavadu) in Kadamattom where a yakshi resides",
    "A mysterious black magician (Odiyan) who can shape-shift into animals at night in a Palakkad village",
    
    # Crime & Detective Thriller
    "A brilliant CID officer in Kochi trying to solve a series of murders linked to an ancient temple",
    "A missing fisherman in the Alappuzha backwaters who returns 5 years later without aging a day",
    
    # Emotional Drama & Romance
    "A bittersweet romance between two classical dancers who meet at the Kerala Kalamandalam",
    "A heartwarming story of an elderly man running a small tea shop in Munnar waiting for his lost son",
    
    # Sci-Fi / Cyberpunk Kerala
    "A futuristic Kochi city in 2077 where AI monorails control the daily lives of citizens",
    "A fisherman in Vizhinjam catches a glowing, mechanical fish that holds a message from the future",
    
    # Historical / Mythological Epic
    "A brave warrior of the Zamorin's naval fleet fighting against foreign invaders in 16th century Calicut",
    "A secret hidden within the underground vaults of the Padmanabhaswamy Temple",
    
    # Mystery & Suspense
    "A traveler stranded in a foggy, deserted tea estate of Vagamon who meets a mysterious old man",
    "A mysterious train that stops at an abandoned station in Shoranur only on full moon nights"
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
            f"Write Part 1 of a 10-part captivating viral story series about: {state['topic']}. "
            f"Start with a highly engaging hook. Establish the setting and introduce the core narrative or mystery."
        )
    else:
        narrative_instruction = (
            f"Write Part {state['current_part']} of the 10-part viral story series '{state['story_name']}'. "
            f"The overall topic is: {state['topic']}. "
            f"In the previous part: '{state['previous_summary']}'. "
            f"Continue the narrative directly from that ending, building up the suspense and emotion further."
        )

    # Instructions for ending of script segment
    if state["current_part"] == 10:
        outro_instruction = "This is the final Part 10. Bring the story to a dramatic, definitive climax in Malayalam."
    else:
        outro_instruction = "The final segment of the script MUST end with the hook: 'അടുത്ത ഭാഗത്തിനായി ഇപ്പോൾ തന്നെ ഫോളോ ചെയ്യൂ.'"

    prompt = f"""You are an expert storyteller for a highly engaging YouTube Shorts channel called "Aroopi" based in Kerala, India.
{narrative_instruction}

CRITICAL INSTRUCTIONS:
1. MALAYALAM SCRIPT SEGMENTS: Write exactly 5 script segments (sentences/phrases) in chronological order that tell this part of the story. The script segments MUST be written in the MALAYALAM language (using Malayalam script).
   - Word Count: Total spoken word count should be around 115-130 Malayalam words.
   - Character names and settings: Use common Kerala names and specify locations in Kerala.
   - Vocabulary: Use simple, standard, and highly engaging Malayalam words that are easy for any native speaker to understand. Do not use complex, obscure, or overly formal words.
   - SEGMENT 1 (First 5 seconds): This MUST start with an immediate, jaw-dropping cliffhanger or captivating hook in Malayalam that instantly grabs the viewer's attention.
   - SEGMENTS 2-4: Build the setting, details, and rising plot/suspense in Malayalam.
   - SEGMENT 5: Delivers a final suspense builder/hook in Malayalam.
2. NO LEAKED DIRECTIONS: The script segments must contain ONLY the spoken Malayalam words. Do NOT include '[image]', 'visual:', 'Narrator:', or similar.
3. OUTRO: {outro_instruction}
4. ENGLISH IMAGE PROMPTS: Write exactly 5 image prompts matching each script segment.
   - Language: The image prompts MUST be written in ENGLISH (as the image generation models only understand English).
   - Kerala Aesthetic: Each image prompt must specify a realistic Kerala aesthetic matching the genre (e.g. traditional Kerala ancestral houses, modern Kochi cityscapes, Alappuzha backwaters, local South Indian facial features, and tropical foliage).
   - Format: Portrait composition (9:16 aspect ratio), cinematic lighting, dramatic mood.
5. STORY TITLE: Generate a catchy, viral title for the entire 10-part story in MALAYALAM (if Part 1) or reuse the title '{state['story_name']}' (if Part > 1).
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

    # ── [1/3] Try Gemini API (Primary) ────────────────────────────────────────
    if GEMINI_API_KEY:
        model_name = "gemini-2.5-flash"
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            try:
                print(f"  >> Querying Gemini API... ({model_name}, Attempt {attempt}/{max_attempts})")
                response = requests.post(url, json=payload, timeout=45)
                if response.status_code == 200:
                    raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    try:
                        parsed = json.loads(raw_text)
                    except json.JSONDecodeError:
                        start = raw_text.find('{')
                        end = raw_text.rfind('}') + 1
                        if start != -1 and end != 0:
                            cleaned = re.sub(r',\s*([\]}])', r'\1', raw_text[start:end])
                            parsed = json.loads(cleaned)
                        else:
                            raise ValueError("No JSON object found")
                    success = True
                    break
                elif response.status_code == 429:
                    print(f"  [WARN] Gemini 429 Quota/Rate Limit. Switching to gemini-flash-latest and retrying...")
                    model_name = "gemini-flash-latest"
                    time.sleep(3)
                else:
                    print(f"  [WARN] Gemini API HTTP status: {response.status_code}: {response.text[:100]}")
                    time.sleep(3)
            except requests.exceptions.Timeout:
                print(f"  [WARN] Gemini request timed out on attempt {attempt}. Retrying...")
                time.sleep(3)
            except Exception as e:
                print(f"  [WARN] Gemini attempt failed: {e}")
                time.sleep(3)

    # ── [2/3] Try OpenAI API Fallback ─────────────────────────────────────────
    if not success and OPENAI_API_KEY:
        print("  >> [Fallback] Querying OpenAI API (gpt-4o-mini)...")
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

    # ── [3/3] Try Groq API Fallback ───────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    if not success and GROQ_API_KEY:
        print("  >> [Fallback] Querying Groq API (Llama-3-8b)...")
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a creative horror writer that outputs JSON matching the exact schema requested."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                raw_text = resp.json()["choices"][0]["message"]["content"].strip()
                try:
                    parsed = json.loads(raw_text)
                    success = True
                except json.JSONDecodeError:
                    start = raw_text.find('{')
                    end = raw_text.rfind('}') + 1
                    if start != -1 and end != 0:
                        cleaned = re.sub(r',\s*([\]}])', r'\1', raw_text[start:end])
                        parsed = json.loads(cleaned)
                        success = True
            else:
                print(f"  [WARN] Groq API HTTP status: {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  [WARN] Groq attempt failed: {e}")

    if not success or not parsed:
        raise RuntimeError("Failed to generate story script content from Gemini, OpenAI, and Groq APIs.")

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
