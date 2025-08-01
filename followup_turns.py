import os
import random
import json
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
from config_arabic import OPENAI_API_KEY, num_turns_lower_limit, num_turns_upper_limit, sample_limit, victim_awareness_levels, multi_turn_input_path, multi_turn_output_path, max_conversation
load_dotenv()

client = OpenAI(api_key=OPENAI_API_KEY)

def query(prompt, max_tokens=3000):
    """
    Generate text using OpenAI GPT
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=max_tokens,
            top_p=0.95,
            n=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f" OpenAI generation failed:\n\n{e}\n")
        return ""


def generate_followup_turns(first_turn, num_turns,victim_aware ):
    """
    Call the OpenAI API to generate phishing messages and legitimate messages
    return format [(text, label), ...]
    """

    # print(" Generating English samples...")

    scam_prompt = f"""Continue the scam phone call dialogue between the caller (scammer) and callee (victim). The victim is {victim_aware} aware of the scam.

    The total number of turns must be exactly {num_turns} individual turns (i.e., lines), alternating between caller and callee.

    🛑 **STRICT RULE - FIRST SENTENCE**: 
    The conversation must begin with the **exact first sentence below**, without **any changes, paraphrasing, or modifications** — including punctuation, spacing, and special codes.
    💬 First sentence to use: "{first_turn}"

    🛑 **STRICT RULE - SPECIAL CODE**: 
    📌 Special codes (e.g., {{00001}}, {{00002}}, etc.) represent fixed values (e.g., names, organizations, or amounts).
    If the first sentence includes special codes, you **must reuse** the exact same codes from the first sentence throughout the dialogue - but only in the same types of places where they were originally used, and they must appear in those places. 
    If the first sentence does not include special codes, that's okay. Do **not** use any codes in this case.
    Do **not** invent or introduce any new codes under any circumstances.
    
    
    📄 Output format (must be valid JSON):
    A list of {num_turns} objects, where:
    - The first object must have `"text"` identical to the first sentence above.
    - The `"role"` alternates between `"caller"` and `"callee"`.
    - The `"sent_id"` starts at 1 and increments by 1.

    Example format:
    [
        {{
            "sent_id": 1,
            "text": "{first_turn}",
            "role": "caller"
        }},
        {{
            "sent_id": 2,
            "text": "...",
            "role": "callee"
        }},
        ...
    ]
    """

    scam_text = query(scam_prompt)
    return scam_text

def parse_json_response(response_text):
    """Parse the JSON response from OpenAI"""
    try:
        # Find JSON array in the response
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']') + 1
        if start_idx != -1 and end_idx != 0:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            print(f"Could not find JSON array in response: {response_text[:200]}...")
            return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response: {response_text[:200]}...")
        return None

if __name__ == "__main__":
    with open(multi_turn_input_path, "r", encoding="utf-8") as infile:
        lines = [line.strip() for line in infile if line.strip()]

    all_conversations = []


    for idx, first_turn in enumerate(tqdm(lines[:sample_limit], desc="Generating conversations")):
        if idx >= max_conversation:
            break
        num_turns = random.randint(num_turns_lower_limit, num_turns_upper_limit)
        victim_aware = random.choice(victim_awareness_levels)
        followup_turns = generate_followup_turns(first_turn, num_turns, victim_aware)

        # Parse the JSON response
        conversation_data = parse_json_response(followup_turns)

        if conversation_data:
            # Add metadata to the conversation
            conversation_with_metadata = {
                "conversation_id": idx + 1,
                "first_turn": first_turn,
                "num_turns": num_turns,
                "victim_awareness": victim_aware,
                "dialogue": conversation_data
            }
            all_conversations.append(conversation_with_metadata)
        else:
            print(f"Failed to parse conversation {idx+1}")
    # Save all conversations to a JSON file
    output_file = multi_turn_output_path
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(all_conversations, outfile, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(all_conversations)} conversations to {output_file}")
