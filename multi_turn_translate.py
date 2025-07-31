# Translate the English conversations in generated_conversations.json into Malay and save to generated_conversations_malay.json
import os
import json
from contextlib import contextmanager
import numpy as np
from tqdm import tqdm
from translate import translate_text
from config import multi_turn_translated_input_path, multi_turn_translated_output_path, multi_turn_from_code, multi_turn_to_code


def translate_conversation(conversation):
    """Translate a single conversation object"""
    translated_conversation = conversation.copy()
    
    # Translate dialogue turns
    if "dialogue" in translated_conversation:
        for turn in translated_conversation["dialogue"]:
            turn["text"] = translate_text(turn["text"], multi_turn_from_code, multi_turn_to_code)
    
    # then assign the translated first_turn to the translated_conversation
    translated_conversation["first_turn"] = translated_conversation['dialogue'][0]['text']
    
    return translated_conversation

# Load the conversations from JSON file
with open(multi_turn_translated_input_path, "r", encoding="utf-8") as infile:
    conversations = json.load(infile)

print(f"Processing {len(conversations)} conversations")

translated_conversations = []

# Process each conversation individually
for i, conversation in enumerate(tqdm(conversations, desc="Translating conversations")):
    translated_conversation = translate_conversation(conversation)
    translated_conversations.append(translated_conversation)

# Save final results
with open(multi_turn_translated_output_path, "w", encoding="utf-8") as outfile:
    json.dump(translated_conversations, outfile, ensure_ascii=False, indent=2)

print(f"Translation completed. Total conversations translated: {len(translated_conversations)}")
print(f"Output saved to: {multi_turn_translated_output_path}") 