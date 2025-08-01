import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Followup turns
num_turns_lower_limit = 1
num_turns_upper_limit = 5
sample_limit = 5
victim_awareness_levels = ["not","not","not","not","not", "tiny", "very"]

# Translation
base_dir = './'
scamGen_input_path = os.path.join(base_dir, "scamGen_combined_first_20k.txt")
scamGen_output_path = os.path.join(base_dir, "english_base_scanGen.txt")
scamGen_from_code = "zh" # ScamGen originally is in Chinese
scamGento_code = "en"    # ScamGen is translated into for maximum LLM performance
translation_service = "google" # "google" or "argos", currently google works better in keeping the original meaning
max_lines = 10

# multi-turn 
multi_turn_input_path = scamGen_output_path
multi_turn_output_path = os.path.join(base_dir, "generated_conversations.json")

# multi-turn translated
multi_turn_translated_input_path = multi_turn_output_path
multi_turn_translated_output_path = os.path.join(base_dir, "generated_conversations_malay.json")
multi_turn_from_code = scamGento_code 
multi_turn_to_code = "ms"  # Malay language code

# voice generation

# List of voice IDs to choose from (you can add more or modify these)
VOICE_IDS = {
    "ms": ["BeIxObt4dYBRJLYoe1hU","NpVSXJvYSdIbjOaMbShj", "Wc6X61hTD7yucJMheuLN", "UcqZLa941Kkt8ZhEEybf", "C1gMsiiE7sXAt59fmvYg"],
}
voice_language = multi_turn_to_code
voice_input_file = multi_turn_translated_output_path
voice_output_dir = "audio_conversations"
voice_sample_limit = 1
