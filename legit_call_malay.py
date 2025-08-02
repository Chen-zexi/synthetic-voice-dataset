import random
import json
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
from config_malay import OPENAI_API_KEY, num_turns_lower_limit, \
    num_turns_upper_limit, num_legit_conversation, legit_call_output_path, \
    legit_call_categories, legit_call_region, legit_call_language
from followup_turns import parse_json_response

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


def generate_legit_calls(num_turns, category, region, language):
    """
    Call the OpenAI API to generate legitimate messages
    return format [(text, label), ...]
    """

    # print(" Generating English samples...")

    legit_call_prompt = f"""Generate realistic {language} phone call dialogue between a caller and a callee from {region}.
    The call content is about {category}.
    The total number of turns must be exactly {num_turns} individual turns (i.e., lines), alternating between caller and callee.

    🗣️ Avoid overly generic or repetitive phrasing — the dialogue should feel natural and realistic.
    
    🛑 To protect privacy, do not use real personal data. Instead, generate synthetic but plausible realistic-looking values.

    🛑Shorter sentences are preferred.
    
    📄 Output format (must be valid JSON):
    - Output must be a JSON array only — no comments or additional explanations.
    - Each object should have:
      - "sent_id": starting at 1 and incrementing by 1.
      - "text": the dialogue line.
      - "role": alternating exactly between "caller" and "callee", starting with "caller".

    Example format:
    [
        {{
            "sent_id": 1,
            "text": "...",
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

    legit_call_text = query(legit_call_prompt)
    return legit_call_text


if __name__ == "__main__":
    all_conversations = []

    for idx in tqdm(range(num_legit_conversation), desc="Generating conversations"):
        num_turns = random.randint(num_turns_lower_limit, num_turns_upper_limit)
        category = random.choice(legit_call_categories)
        conversation = generate_legit_calls(num_turns, category, legit_call_region, legit_call_language)
        conversation_data = parse_json_response(conversation)
        if conversation_data:
            # Add metadata to the conversation
            conversation_with_metadata = {
                "conversation_id": idx + 1,
                "region": legit_call_region,
                "category": category,
                "num_turns": num_turns,
                "dialogue": conversation_data
            }
            all_conversations.append(conversation_with_metadata)
        else:
            print(f"Failed to parse conversation {idx + 1}")

    # Save all conversations to a JSON file
    output_file = legit_call_output_path
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(all_conversations, outfile, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(all_conversations)} conversations to {output_file}")
