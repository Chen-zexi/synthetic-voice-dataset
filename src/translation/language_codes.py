"""
Language code mappings for different translation services.
"""

# Language code mappings for each translation service
LANGUAGE_CODE_MAPPINGS = {
    "google": {
        # Google Translate (via deep-translator) uses specific codes
        "zh": "zh-CN",          # Chinese simplified
        "zh-CN": "zh-CN",       # Already correct
        "zh-TW": "zh-TW",       # Chinese traditional
        "en": "en",             # English
        "ar": "ar",             # Arabic
        "ms": "ms",             # Malay
        "es": "es",             # Spanish
        "fr": "fr",             # French
        "de": "de",             # German
        "ja": "ja",             # Japanese
        "ko": "ko",             # Korean
        "hi": "hi",             # Hindi
        "id": "id",             # Indonesian
        "th": "th",             # Thai
        "vi": "vi",             # Vietnamese
        "tr": "tr",             # Turkish
        "ru": "ru",             # Russian
        "pt": "pt",             # Portuguese
        "it": "it",             # Italian
        "nl": "nl",             # Dutch
        "pl": "pl",             # Polish
    },
    "argos": {
        # Argos Translate uses ISO 639-1 codes
        "zh": "zh",             # Chinese
        "zh-CN": "zh",          # Map to generic Chinese
        "zh-TW": "zh",          # Map to generic Chinese
        "en": "en",             # English
        "ar": "ar",             # Arabic
        "ms": "ms",             # Malay
        "es": "es",             # Spanish
        "fr": "fr",             # French
        "de": "de",             # German
        "ja": "ja",             # Japanese
        "ko": "ko",             # Korean
        "hi": "hi",             # Hindi
        "id": "id",             # Indonesian
        "th": "th",             # Thai
        "vi": "vi",             # Vietnamese
        "tr": "tr",             # Turkish
        "ru": "ru",             # Russian
        "pt": "pt",             # Portuguese
        "it": "it",             # Italian
        "nl": "nl",             # Dutch
        "pl": "pl",             # Polish
    },
    "qwen": {
        # Qwen-MT uses language names, not ISO codes
        "zh": "Chinese",        # Chinese (auto-detect variant)
        "zh-CN": "Chinese",     # Chinese simplified
        "zh-TW": "Chinese",     # Chinese traditional
        "en": "English",        # English
        "ar": "Arabic",         # Arabic
        "ms": "Malay",          # Malay
        "es": "Spanish",        # Spanish
        "fr": "French",         # French
        "de": "German",         # German
        "ja": "Japanese",       # Japanese
        "ko": "Korean",         # Korean
        "hi": "Hindi",          # Hindi
        "id": "Indonesian",     # Indonesian
        "th": "Thai",           # Thai
        "vi": "Vietnamese",     # Vietnamese
        "tr": "Turkish",        # Turkish
        "ru": "Russian",        # Russian
        "pt": "Portuguese",     # Portuguese
        "it": "Italian",        # Italian
        "nl": "Dutch",          # Dutch
        "pl": "Polish",         # Polish
        "uk": "Ukrainian",      # Ukrainian
        "cs": "Czech",          # Czech
        "sv": "Swedish",        # Swedish
        "da": "Danish",         # Danish
        "fi": "Finnish",        # Finnish
        "no": "Norwegian",      # Norwegian
        "el": "Greek",          # Greek
        "he": "Hebrew",         # Hebrew
        "hu": "Hungarian",      # Hungarian
        "ro": "Romanian",       # Romanian
        "sk": "Slovak",         # Slovak
        "bg": "Bulgarian",      # Bulgarian
        "hr": "Croatian",       # Croatian
        "lt": "Lithuanian",     # Lithuanian
        "lv": "Latvian",        # Latvian
        "et": "Estonian",       # Estonian
        "sl": "Slovenian",      # Slovenian
        "ca": "Catalan",        # Catalan
        "eu": "Basque",         # Basque
        "gl": "Galician",       # Galician
        "sq": "Albanian",       # Albanian
        "mk": "Macedonian",     # Macedonian
        "sr": "Serbian",        # Serbian
        "bs": "Bosnian",        # Bosnian
        "is": "Icelandic",      # Icelandic
        "ga": "Irish",          # Irish
        "cy": "Welsh",          # Welsh
        "mt": "Maltese",        # Maltese
        "lb": "Luxembourgish",  # Luxembourgish
        "af": "Afrikaans",      # Afrikaans
        "sw": "Swahili",        # Swahili
        "am": "Amharic",        # Amharic
        "ha": "Hausa",          # Hausa
        "yo": "Yoruba",         # Yoruba
        "ig": "Igbo",           # Igbo
        "zu": "Zulu",           # Zulu
        "xh": "Xhosa",          # Xhosa
        "sn": "Shona",          # Shona
        "rw": "Kinyarwanda",    # Kinyarwanda
        "so": "Somali",         # Somali
        "ta": "Tamil",          # Tamil
        "te": "Telugu",         # Telugu
        "kn": "Kannada",        # Kannada
        "ml": "Malayalam",      # Malayalam
        "mr": "Marathi",        # Marathi
        "gu": "Gujarati",       # Gujarati
        "bn": "Bengali",        # Bengali
        "pa": "Punjabi",        # Punjabi
        "or": "Odia",           # Odia
        "as": "Assamese",       # Assamese
        "ne": "Nepali",         # Nepali
        "si": "Sinhala",        # Sinhala
        "my": "Burmese",        # Burmese
        "km": "Khmer",          # Khmer
        "lo": "Lao",            # Lao
        "ka": "Georgian",       # Georgian
        "hy": "Armenian",       # Armenian
        "az": "Azerbaijani",    # Azerbaijani
        "kk": "Kazakh",         # Kazakh
        "ky": "Kyrgyz",         # Kyrgyz
        "uz": "Uzbek",          # Uzbek
        "tg": "Tajik",          # Tajik
        "tk": "Turkmen",        # Turkmen
        "mn": "Mongolian",      # Mongolian
        "ur": "Urdu",           # Urdu
        "ps": "Pashto",         # Pashto
        "fa": "Persian",        # Persian
        "ku": "Kurdish",        # Kurdish
        "ckb": "Central Kurdish", # Central Kurdish
        "sd": "Sindhi",         # Sindhi
        "be": "Belarusian",     # Belarusian
        "eo": "Esperanto",      # Esperanto
        "la": "Latin",          # Latin
    },
    # Add more translation services as needed
    "deepl": {
        # DeepL uses its own codes
        "zh": "ZH",             # Chinese
        "zh-CN": "ZH",          # Map to generic Chinese
        "zh-TW": "ZH",          # Map to generic Chinese
        "en": "EN",             # English
        "ar": "AR",             # Arabic (if supported)
        "ms": "MS",             # Malay (if supported)
        "es": "ES",             # Spanish
        "fr": "FR",             # French
        "de": "DE",             # German
        "ja": "JA",             # Japanese
        "ko": "KO",             # Korean
        "pt": "PT",             # Portuguese
        "it": "IT",             # Italian
        "nl": "NL",             # Dutch
        "pl": "PL",             # Polish
        "ru": "RU",             # Russian
    }
}


def get_language_code(service: str, code: str) -> str:
    """
    Get the appropriate language code for a specific translation service.
    
    Args:
        service: Translation service name (google, argos, deepl, etc.)
        code: Generic language code
        
    Returns:
        Service-specific language code
    """
    service_lower = service.lower()
    
    # Check if we have mappings for this service
    if service_lower not in LANGUAGE_CODE_MAPPINGS:
        # Return original code if service not found
        return code
    
    # Get the mapping for this service
    service_mappings = LANGUAGE_CODE_MAPPINGS[service_lower]
    
    # Return mapped code or original if not found
    return service_mappings.get(code, code)


def is_language_supported(service: str, code: str) -> bool:
    """
    Check if a language is supported by a translation service.
    
    Args:
        service: Translation service name
        code: Language code to check
        
    Returns:
        True if supported, False otherwise
    """
    service_lower = service.lower()
    
    if service_lower not in LANGUAGE_CODE_MAPPINGS:
        # Unknown service, assume supported
        return True
    
    # Check if code or its mapping exists
    service_mappings = LANGUAGE_CODE_MAPPINGS[service_lower]
    return code in service_mappings or code in service_mappings.values()


def get_supported_languages(service: str) -> list:
    """
    Get list of supported language codes for a service.
    
    Args:
        service: Translation service name
        
    Returns:
        List of supported language codes
    """
    service_lower = service.lower()
    
    if service_lower not in LANGUAGE_CODE_MAPPINGS:
        return []
    
    return list(LANGUAGE_CODE_MAPPINGS[service_lower].keys())