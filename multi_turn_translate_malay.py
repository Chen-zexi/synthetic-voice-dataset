# Translate the English conversations in generated_conversations.json into Malay and save to generated_conversations_malay.json
import os
import json
from contextlib import contextmanager
import numpy as np
from tqdm import tqdm
from translate import translate_text
from config_malay import multi_turn_translated_input_path, multi_turn_translated_output_path, multi_turn_from_code, multi_turn_to_code, preprocessing_map_path
import re
import random

def fill_placeholders(text, map_path, substitution_cache):
    """Replace {code} placeholders in `text` using consistent substitutions from the JSON map at `map_path`."""
    # Load the mapping JSON
    with open(map_path, 'r', encoding='utf-8') as mf:
        code_map = json.load(mf)

    # Replacement function
    def repl(m):
        key = m.group(0)
        if key not in substitution_cache:
            entry = code_map.get(key)
            subs = entry.get('substitutions') if entry else None
            substitution_cache[key] = random.choice(subs) if subs else key
        return substitution_cache[key]

    # Substitute all {00001}-style codes consistently
    return re.sub(r'\{\d{5}\}', repl, text)

def translate_conversation(conversation):
    """Translate a single conversation object"""
    translated_conversation = conversation.copy()

    substitution_cache = {}

    # Translate dialogue turns
    if "dialogue" in translated_conversation:
        for turn in translated_conversation["dialogue"]:
            turn["text"] = fill_placeholders(translate_text(turn["text"], multi_turn_from_code, multi_turn_to_code), preprocessing_map_path, substitution_cache)

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
