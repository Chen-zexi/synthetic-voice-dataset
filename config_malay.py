import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Followup turns
num_turns_lower_limit = 2
num_turns_upper_limit = 6
sample_limit = 5
victim_awareness_levels = ["not","not","not","not","not", "tiny", "very"]

# Preprocessing
base_dir = './'
preprocessing_input_path = os.path.join(base_dir, "scam_first_line_chinese.txt")
base, _ = os.path.splitext(preprocessing_input_path)
preprocessing_output_path = base + "_mapped.txt"
preprocessing_map_path = os.path.join(base_dir, "malaysia_placeholder_map.json")

# Translation
base_dir = './'
translation_input_path = preprocessing_output_path
translation_output_path = os.path.join(base_dir, "scam_first_line_english_mapped.txt")
translation_from_code = "zh" # ScamGen originally is in Chinese
translation_to_code = "en"    # ScamGen is translated into for maximum LLM performance
translation_service = "google" # "google" or "argos", currently google works better in keeping the original meaning
max_lines = 5

# multi-turn
multi_turn_input_path = translation_output_path
multi_turn_output_path = os.path.join(base_dir, "scam_conversation_english.json")
max_conversation = 5

# multi-turn translated
multi_turn_translated_input_path = multi_turn_output_path
multi_turn_translated_output_path = os.path.join(base_dir, "scam_conversation_malay.json")
multi_turn_from_code = translation_to_code
multi_turn_to_code = "ms"

# voice generation
VOICE_IDS = {
    "ms": ["C1gMsiiE7sXAt59fmvYg", # Hasnan
           "BeIxObt4dYBRJLYoe1hU", # Athira
           ],
}
voice_language = multi_turn_to_code
voice_input_file = multi_turn_translated_output_path
voice_output_dir = "audio_conversations_malay"
voice_sample_limit = 1
