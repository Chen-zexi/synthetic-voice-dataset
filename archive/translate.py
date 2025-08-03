# Translate the Chinese lines in scamGen_combined_first_20k.txt into English and save to scamGen_combined_first_20k_en.txt
import os
from contextlib import contextmanager
import numpy as np
from tqdm import tqdm
import argostranslate.package
import argostranslate.translate
from googletrans import Translator

from config_malay import translation_input_path, translation_output_path, translation_from_code, translation_to_code, translation_service, max_lines

import asyncio

async def google_translate_text(text, src, dest):
    async with Translator() as translator:
        result = await translator.translate(text, src=src, dest=dest)
        return result.text

# Initialize Argos Translate
def setup_argos_translate():
    """Setup Argos Translate with Chinese to English translation"""

    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        filter(
            lambda x: x.from_code == translation_from_code and x.to_code == translation_to_code, available_packages
        )
    )
    argostranslate.package.install_from_path(package_to_install.download())

def translate_text(text, from_code, to_code):
    """Translate a single text"""
    try:
        if translation_service == "google":
            return asyncio.run(google_translate_text(text, from_code, to_code))
        elif translation_service == "argos":
            if from_code == "zh":
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

if __name__ == "__main__":
    if translation_service == "argos":
        setup_argos_translate()

    # Read all lines from input file
    with open(translation_input_path, "r", encoding="utf-8") as infile:
        all_lines = infile.readlines()

    # Get texts to translate
    texts_to_translate = [line.strip() for line in all_lines[:min(max_lines, len(all_lines))] if line.strip()]

    print(f"Processing {len(texts_to_translate)} texts")

    translated_lines = []

    # Process each text individually
    for i, text in enumerate(tqdm(texts_to_translate, desc="Translating")):
        translated_text = translate_text(text, translation_from_code, translation_to_code)
        translated_text = post_process_text_from_ch(translated_text)
        translated_lines.append(translated_text + "\n")

    # Save final results
    with open(translation_output_path, "w", encoding="utf-8") as outfile:
        outfile.writelines(translated_lines)

    print(f"Translation completed. Total lines translated: {len(translated_lines)}")
