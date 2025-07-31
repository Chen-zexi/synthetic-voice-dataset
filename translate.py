# Translate the Chinese lines in scamGen_combined_first_20k.txt into English and save to scamGen_combined_first_20k_en.txt
import os
from contextlib import contextmanager
import numpy as np
from tqdm import tqdm
import argostranslate.package
import argostranslate.translate
base_dir = './'
input_path = os.path.join(base_dir, "scamGen_combined_first_20k.txt")
output_path = os.path.join(base_dir, "translation.txt")
from_code = "zh"
to_code = "en"

# Initialize Argos Translate
def setup_argos_translate():
    """Setup Argos Translate with Chinese to English translation"""

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
    """Translate a single text"""
    try:
        # argo translation needs to convert the space into 。
        text = text.replace(" ", "。")
        translated_text = argostranslate.translate.translate(text, from_code, to_code)
        return translated_text
    except Exception as e:
        return f"[Translation Error]: {text}"

def post_process_text_from_ch(text):
    """Post-process the translated text, using the argotranslate package it cause below artifacts which needs to be removed"""
    
    import re
    # Remove trailing "One.", "Two.", "Three.", "Four." (with or without leading space)
    text = re.sub(r'\s*(One\.|Two\.|Three\.|Four\.)\s*$', '', text)
    # Remove trailing "CC BY-NC-ND 2.0" (with or without leading space)
    text = re.sub(r'\s*CC BY-NC-ND 2\.0\s*$', '', text)
    return text

# Count total lines to process
max_lines = 1000

# Read all lines from input file
with open(input_path, "r", encoding="utf-8") as infile:
    all_lines = infile.readlines()

# Get texts to translate
texts_to_translate = [line.strip() for line in all_lines[:min(max_lines, len(all_lines))] if line.strip()]

print(f"Processing {len(texts_to_translate)} texts")

translated_lines = []

# Process each text individually
for i, text in enumerate(tqdm(texts_to_translate, desc="Translating")):
    translated_text = translate_text(text)
    if from_code == "zh": # When translate from Chinese, it has some artifacts that needs to be removed
        translated_text = post_process_text_from_ch(translated_text)
    translated_lines.append(translated_text + "\n")

# Save final results
with open(output_path, "w", encoding="utf-8") as outfile:
    outfile.writelines(translated_lines)

print(f"Translation completed. Total lines translated: {len(translated_lines)}")
