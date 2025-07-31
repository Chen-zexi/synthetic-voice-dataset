import os
import random
import json
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
from config import OPENAI_API_KEY, num_turns_lower_limit, num_turns_upper_limit, sample_limit, victim_awareness_levels, scamGen_output_path, multi_turn_output_path
load_dotenv()

client = OpenAI(api_key=OPENAI_API_KEY)

def query(prompt, max_tokens=3000):
    """
    Generate text using OpenAI GPT
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
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

    scam_prompt = f"""Follow up the conversation to finish this scam phone call dialogues with {num_turns} turns between the caller and callee.  
    Simulate the conversation where the caller is a scammer and the callee is a victim and the victim is {victim_aware} aware of the scam. 
    - For names of any person and company, use placeholders like <human_name>, <bank_name>, <company_name>, <authority_name>.
    - The dialogues are formatted in json format as follows: 
    [
        {{
            "sent_id": 1,
            "text":  {first_turn}, 
            "role": "caller",
        }},
        {{
            "sent_id": 2,
            "text": ..., 
            "role": "callee",
        }},
        ...,
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
    with open(scamGen_output_path, "r", encoding="utf-8") as infile:
        lines = [line.strip() for line in infile if line.strip()]

    all_conversations = []
    

    for idx, first_turn in enumerate(tqdm(lines[:sample_limit], desc="Generating conversations")):
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
        