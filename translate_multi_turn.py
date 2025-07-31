# Translate the English conversations in generated_conversations.json into Malay and save to generated_conversations_malay.json
import os
import json
from contextlib import contextmanager
import numpy as np
from tqdm import tqdm
import argostranslate.package
import argostranslate.translate

base_dir = './'
input_path = os.path.join(base_dir, "generated_conversations.json")
output_path = os.path.join(base_dir, "generated_conversations_malay.json")
from_code = "en"
to_code = "ms"  # Malay language code

# Initialize Argos Translate
def setup_argos_translate():
    """Setup Argos Translate with English to Malay translation"""
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

setup_argos_translate()

def translate_text(text):
    """Translate a single text from English to Malay"""
    try:
        translated_text = argostranslate.translate.translate(text, from_code, to_code)
        return translated_text
    except Exception as e:
        return f"[Translation Error]: {text}"

def translate_conversation(conversation):
    """Translate a single conversation object"""
    translated_conversation = conversation.copy()
    
    # Translate first_turn
    if "first_turn" in translated_conversation:
        translated_conversation["first_turn"] = translate_text(conversation["first_turn"])
    
    # Translate dialogue turns
    if "dialogue" in translated_conversation:
        for turn in translated_conversation["dialogue"]:
            turn["text"] = translate_text(turn["text"])
    
    return translated_conversation

# Load the conversations from JSON file
with open(input_path, "r", encoding="utf-8") as infile:
    conversations = json.load(infile)

print(f"Processing {len(conversations)} conversations")

translated_conversations = []

# Process each conversation individually
for i, conversation in enumerate(tqdm(conversations, desc="Translating conversations")):
    translated_conversation = translate_conversation(conversation)
    translated_conversations.append(translated_conversation)

# Save final results
with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(translated_conversations, outfile, ensure_ascii=False, indent=2)

print(f"Translation completed. Total conversations translated: {len(translated_conversations)}")
print(f"Output saved to: {output_path}") 