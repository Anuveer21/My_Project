import requests
import json
import os
import re
import logging
import random
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ===== CONFIG =====
API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3-8b-instruct"
MEMORY_FILE = "memory.json"
MAX_HISTORY = 10

# ===== FUN FEATURES =====
FUN_FACTS = [
    "Octopuses have three hearts.",
    "Bananas are berries, but strawberries are not.",
    "Sharks existed before trees.",
    "A day on Venus is longer than a year on Venus.",
    "Honey never spoils."
]

TOPIC_SUGGESTIONS = [
    "If you could live in any video game world, which would it be?",
    "What skill would you master instantly if you could?",
    "Do you think AI will ever fully replace human creativity?",
    "What’s the most interesting place you’ve ever been?",
    "Would you rather explore space or the deep ocean?"
]

# ===== DEFAULT STATE =====
def default_state():
    return {
        "name": None,
        "likes": [],
        "dislikes": [],
        "notes": [],
        "history": [],
        "last_reply": ""
    }

# ===== STATE MANAGEMENT =====
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return default_state()
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            base = default_state()
            base.update(data)
            return base
    except Exception as e:
        logging.error(f"Memory corruption: {e}")
        return default_state()

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

state = load_memory()

# ===== MEMORY EXTRACTION =====
def update_memory_facts(text):
    global state
    text_lower = text.lower()

    # Name extraction
    name_match = re.search(r"my name is ([\w\s]+)", text_lower)
    if name_match:
        state["name"] = name_match.group(1).strip().title()

    # Likes / dislikes
    for pattern, key in [
        (r"i like ([\w\s]+)", "likes"),
        (r"i love ([\w\s]+)", "likes"),
        (r"i hate ([\w\s]+)", "dislikes")
    ]:
        match = re.search(pattern, text_lower)
        if match:
            item = match.group(1).strip()
            if item and item not in state[key]:
                state[key].append(item)

# ===== SYSTEM PROMPT =====
def build_system_prompt():
    prompt = "You are a helpful, conversational AI assistant."

    if state.get("name"):
        prompt += f" The user's name is {state['name']}."

    if state.get("likes"):
        prompt += f" The user likes {', '.join(state['likes'])}."

    if state.get("dislikes"):
        prompt += f" The user dislikes {', '.join(state['dislikes'])}."

    if state.get("notes"):
        prompt += f" Important notes: {', '.join(state['notes'])}."

    prompt += " Use this information naturally when relevant. Do NOT repeat it unnecessarily."

    return prompt

# ===== ROUTES =====

@app.route("/chat", methods=["POST"])
def chat():
    global state

    data = request.json
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    logging.info(f"User: {user_input}")
    text_lower = user_input.lower()

    # 🎲 Fun Fact Feature
    if any(x in text_lower for x in ["fun fact", "something interesting", "random fact"]):
        fact = random.choice(FUN_FACTS)
        return jsonify({"reply": f"Here's a fun fact: {fact}"})

    # 💬 Topic Suggestion Feature
    if any(x in text_lower for x in ["suggest a topic", "conversation starter", "what should we talk about"]):
        topic = random.choice(TOPIC_SUGGESTIONS)
        return jsonify({"reply": f"Try this: {topic}"})

    # Update memory
    update_memory_facts(user_input)

    # Build messages
    system_msg = {"role": "system", "content": build_system_prompt()}
    history = state.get("history", [])[-6:]  # keep context tight

    messages = [system_msg] + history

    messages.append({
        "role": "user",
        "content": f"""
User message: {user_input}

Respond naturally. Use past context only if relevant. Avoid repeating previous responses.
"""
    })

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 300
            },
            timeout=20
        )

        data = response.json()

        if "choices" not in data:
            logging.error(f"API error: {data}")
            return jsonify({"error": "API failed"}), 500

        reply = data["choices"][0]["message"]["content"].strip()

        # Anti-repetition
        if reply == state.get("last_reply", ""):
            reply += " (let me rephrase that better)"

        state["last_reply"] = reply

        # Update history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        state["history"] = history[-MAX_HISTORY:]
        save_memory(state)

        logging.info(f"State: {state}")

        return jsonify({"reply": reply})

    except Exception as e:
        logging.error(f"Request failed: {e}")
        return jsonify({"error": "Assistant is unavailable"}), 500


@app.route("/memory", methods=["GET"])
def memory():
    return jsonify(state)


@app.route("/reset", methods=["POST"])
def reset():
    global state
    state = default_state()
    save_memory(state)
    return jsonify({"message": "Memory cleared"})


# ===== RUN =====
if __name__ == "__main__":
    if not API_KEY:
        print("CRITICAL ERROR: Set OPENROUTER_API_KEY environment variable.")
    else:
        app.run(host="127.0.0.1", port=5000)