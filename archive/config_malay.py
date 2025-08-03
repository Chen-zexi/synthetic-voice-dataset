import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Followup turns
num_turns_lower_limit = 2
num_turns_upper_limit = 4
sample_limit = 25
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
max_lines = 25

# multi-turn
multi_turn_input_path = translation_output_path
multi_turn_output_path = os.path.join(base_dir, "scam_conversation_english.json")
max_conversation = 25

# multi-turn translated
multi_turn_translated_input_path = multi_turn_output_path
multi_turn_translated_output_path = os.path.join(base_dir, "scam_conversation_malay.json")
multi_turn_from_code = translation_to_code
multi_turn_to_code = "ms"

# legit-call
legit_call_output_path = os.path.join(base_dir, "legit_conversation_malay.json")
num_legit_conversation = 25
legit_call_region = "Malaysia"
legit_call_language = "Malay"
legit_call_categories = [
    # Personal & Social
    "family_checkin",
    "friend_chat",
    "relationship_talk",
    "holiday_greeting",
    "emergency_help_request",
    # Services & Appointments
    "doctor_appointment_confirmation",
    "clinic_test_results",
    "delivery_confirmation",
    "utility_service_followup",
    "repair_scheduling",
    # Government & Official
    "bank_verification_call",
    "visa_status_update",
    "tax_inquiry",
    "insurance_claim_followup",
    "civil_services_scheduling",
    # Work & Career
    "job_interview_scheduling",
    "coworker_sync",
    "project_status_update",
    "freelance_client_call",
    "work_meeting_reminder",
    # Education & School
    "school_event_reminder",
    "tutoring_session",
    "academic_advising",
    "exam_results_notification",
    "class_schedule_change",
    # Lifestyle & Others
    "restaurant_reservation",
    "hairdresser_booking",
    "hotel_booking_confirmation",
    "volunteering_coordination",
    "language_exchange_call",
    # Business & Customer Support
    "customer_support_callback",
    "subscription_renewal_notice",
    "product_feedback_survey",
    "account_security_verification",
    "appointment_cancellation_notice"
]

# voice generation
VOICE_IDS = {
    "ms": ["C1gMsiiE7sXAt59fmvYg", # Hasnan
           "BeIxObt4dYBRJLYoe1hU", # Athira
           ],
}
voice_language = multi_turn_to_code
voice_input_file_scam = multi_turn_translated_output_path
voice_output_dir_scam = "scam_audio_conversations_malay"
voice_input_file_legit = legit_call_output_path
voice_output_dir_legit = "legit_audio_conversations_malay"
voice_sample_limit = 25
voice_is_scam = False

# post processing
post_processing_scam_json_input = os.path.join(base_dir, "scam_conversation_malay.json")
post_processing_scam_json_output = os.path.join(base_dir, "scam_conversation_malay_formatted.json")
post_processing_legit_json_input = os.path.join(base_dir, "legit_conversation_malay.json")
post_processing_legit_json_output = os.path.join(base_dir, "legit_conversation_malay_formatted.json")
post_processing_region = legit_call_region
post_processing_scam_audio_dir = voice_output_dir_scam
post_processing_legit_audio_dir = voice_output_dir_legit
post_processing_scam_audio_zip_output = os.path.join(base_dir, "scam_conversation_audio.zip")
post_processing_legit_audio_zip_output = os.path.join(base_dir, "legit_conversation_audio.zip")
