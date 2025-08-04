# Locale Implementation Guide

This guide provides step-by-step instructions for adding new locales to the voice scam dataset generation pipeline.

## User critical instructions
**make sure you do your research (use web search to get the accurate substitutes)**
- checkout the locale you are working on first on @locale_road_map.md i.e mark the status as in progress at the very beginning so that other people know you are working on it.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Configuration Structure](#configuration-structure)
5. [Placeholder Reference](#placeholder-reference)
6. [Cultural Considerations](#cultural-considerations)
7. [Voice Selection](#voice-selection)
8. [Testing Checklist](#testing-checklist)
9. [Troubleshooting](#troubleshooting)

## Overview

The locale system uses a two-letter language code followed by a two-letter country code (e.g., `ar-sa` for Arabic-Saudi Arabia, `ms-my` for Malay-Malaysia).

### Directory Structure
```
configs/
└── localizations/
    ├── template/           # Template files for new locales
    │   ├── config.json    # Base configuration
    │   └── placeholders.json # Placeholder mappings
    ├── ar-sa/             # Arabic - Saudi Arabia
    ├── ar-ae/             # Arabic - UAE
    ├── ms-my/             # Malay - Malaysia
    └── [new-locale]/      # Your new locale
```

## Prerequisites

1. **Research the target locale:**
   - Common names and their romanization
   - Currency and typical amounts
   - Major cities and regions
   - Government agencies and services
   - Popular brands and companies
   - Cultural communication patterns

2. **Obtain ElevenLabs voice IDs:**
   - Select 3-5 voices with appropriate accents
   - Mix of male/female voices
   - Different age ranges if possible

## Step-by-Step Implementation

### Step 1: Create Locale Directory
```bash
mkdir -p configs/localizations/[locale-code]
```

### Step 2: Copy Template Files
```bash
cp configs/localizations/template/* configs/localizations/[locale-code]/
```

### Step 3: Configure config.json

Edit `configs/localizations/[locale-code]/config.json` using the **new standardized structure**:

## Configuration Structure

The configuration file must follow this **exact structure**:

```json
{
  "locale": {
    "id": "ko-kr",
    "language_code": "ko",
    "country_code": "KR",
    "language_name": "Korean",
    "region_name": "South Korea",
    "currency": "KRW",
    "currency_symbol": "₩"
  },
  "translation": {
    "from_code": "zh-CN",
    "to_code": "ko",
    "intermediate_code": "en"
  },
  "voices": {
    "ids": [
      "voice_id_1",
      "voice_id_2",
      "voice_id_3"
    ],
    "names": [
      "Junho (Male/Young)",
      "Minji (Female/Middle-aged)",
      "Sangho (Male/Elderly)"
    ]
  },
  "conversation": {
    "legit_categories": [
      "family_checkin",
      "friend_chat",
      "relationship_talk",
      "holiday_greeting",
      "emergency_help_request",
      "doctor_appointment_confirmation",
      "clinic_test_results",
      "delivery_confirmation",
      "utility_service_followup",
      "repair_scheduling",
      "bank_verification_call",
      "visa_status_update",
      "tax_inquiry",
      "insurance_claim_followup",
      "civil_services_scheduling",
      "job_interview_scheduling",
      "coworker_sync",
      "project_status_update",
      "freelance_client_call",
      "work_meeting_reminder",
      "school_event_reminder",
      "tutoring_session",
      "academic_advising",
      "exam_results_notification",
      "class_schedule_change",
      "restaurant_reservation",
      "hairdresser_booking",
      "hotel_booking_confirmation",
      "volunteering_coordination",
      "language_exchange_call",
      "customer_support_callback",
      "subscription_renewal_notice",
      "product_feedback_survey",
      "account_security_verification",
      "appointment_cancellation_notice"
    ]
  },
  "output": {
    "scam_conversation": "scam_conversation.json",
    "legit_conversation": "legit_conversation.json",
    "scam_audio_dir": "scam",
    "legit_audio_dir": "legit",
    "scam_formatted": "scam_conversation_formatted.json",
    "legit_formatted": "legit_conversation_formatted.json"
  },
  "cultural_notes": {
    "phone_greeting": "여보세요 (yeoboseyo) - Hello (phone greeting)",
    "formality_level": "Formal/Hierarchical - Korean uses different speech levels",
    "common_scam_themes": [
      "Voice phishing (보이스피싱) impersonating prosecutors or police",
      "Loan scams targeting those with poor credit",
      "Investment scams promising high returns"
    ]
  }
}
```

### Required Configuration Sections

#### 1. Locale Section (REQUIRED)
```json
"locale": {
  "id": "[locale-code]",           // e.g., "ko-kr", "fr-ca"
  "language_code": "[lang]",       // ISO 639-1 code (e.g., "ko", "fr")
  "country_code": "[country]",     // ISO 3166-1 code (e.g., "KR", "CA")
  "language_name": "[Language]",   // English name (e.g., "Korean")
  "region_name": "[Region]",       // English region (e.g., "South Korea")
  "currency": "[CODE]",           // Currency code (e.g., "KRW", "CAD")
  "currency_symbol": "[symbol]"   // Currency symbol (e.g., "₩", "C$")
}
```

#### 2. Translation Section (REQUIRED)
```json
"translation": {
  "from_code": "zh-CN",          // Always Chinese source
  "to_code": "[target-lang]",    // Target language code (must be Google Translate supported)
  "intermediate_code": "en"      // Always English intermediate
}
```

**Important**: The `to_code` must use Google Translate supported language codes:
- For Traditional Chinese regions (Hong Kong, Taiwan): use `"zh-TW"`
- For Simplified Chinese regions (Singapore, Mainland): use `"zh-CN"`
- For other languages: use ISO 639-1 codes (e.g., `"ja"`, `"ko"`, `"ms"`, `"ar"`)

#### 3. Voices Section (REQUIRED)
```json
"voices": {
  "ids": ["voice_id_1", "voice_id_2", "voice_id_3"],
  "names": ["Name (Gender/Age)", "Name (Gender/Age)", "Name (Gender/Age)"]
}
```

#### 4. Conversation Section (REQUIRED)
```json
"conversation": {
  "legit_categories": [
    // List of legitimate call categories
    "family_checkin",
    "friend_chat",
    // ... (see full list above)
  ]
}
```

#### 5. Output Section (REQUIRED)
```json
"output": {
  "scam_conversation": "scam_conversation.json",
  "legit_conversation": "legit_conversation.json",
  "scam_audio_dir": "scam",
  "legit_audio_dir": "legit",
  "scam_formatted": "scam_conversation_formatted.json",
  "legit_formatted": "legit_conversation_formatted.json"
}
```

#### 6. Cultural Notes Section (OPTIONAL)
```json
"cultural_notes": {
  "phone_greeting": "Local phone greeting",
  "formality_level": "Description of formality patterns",
  "common_scam_themes": [
    "Region-specific scam types"
  ]
}
```

### Currency Reference for Major Locales
| Region | Currency Code | Symbol | Example |
|--------|---------------|--------|---------|
| United States | USD | $ | $100 |
| European Union | EUR | € | €100 |
| United Kingdom | GBP | £ | £100 |
| Japan | JPY | ¥ | ¥10,000 |
| South Korea | KRW | ₩ | ₩100,000 |
| China | CNY | ¥ | ¥100 |
| India | INR | ₹ | ₹1,000 |
| Canada | CAD | C$ | C$100 |
| Australia | AUD | A$ | A$100 |
| Singapore | SGD | S$ | S$100 |
| Hong Kong | HKD | HK$ | HK$100 |
| Taiwan | TWD | NT$ | NT$1,000 |
| Philippines | PHP | ₱ | ₱1,000 |
| Vietnam | VND | ₫ | ₫100,000 |
| Thailand | THB | ฿ | ฿1,000 |
| Malaysia | MYR | RM | RM100 |
| Indonesia | IDR | Rp | Rp100,000 |
| Saudi Arabia | SAR | ﷼ | ﷼100 |
| UAE | AED | د.إ | د.إ100 |

### Step 4: Populate placeholders.json

For each placeholder ({00001} through {00053}), provide culturally appropriate substitutions:

```json
"{00001}": {
  "tag": "<person_name>",
  "substitutions": [
    "김민수",
    "이지은",
    "박준호",
    "최서연"
  ],
  "translations": [
    "Kim Minsoo",
    "Lee Jieun",
    "Park Junho",
    "Choi Seoyeon"
  ]
}
```

### Step 5: Complete All 53 Placeholders

Ensure all placeholders are populated with relevant local data:
- Personal names (common given names and surnames)
- Cities (major metropolitan areas)
- Money amounts (in local currency)
- Government agencies (actual agency names)
- Companies (locally operating businesses)
- Social media platforms (popular in the region)
- And all other categories...

## Placeholder Reference

### Personal & Geographic (00001-00010)
| Code | Tag | Description | Example |
|------|-----|-------------|---------|
| {00001} | `<person_name>` | Common personal names | John, Mary, Ahmad, Wei |
| {00002} | `<city_name>` | Major cities | London, Tokyo, Dubai |
| {00003} | `<money_amount_medium>` | $200-$1000 equivalent | 500 GBP, 100,000 JPY |
| {00004} | `<tutoring_center>` | Education centers | Kumon, Sylvan Learning |
| {00005} | `<credit_card_agency>` | Credit card companies | Visa, MasterCard |
| {00006} | `<money_amount_small>` | $20-$100 equivalent | 50 EUR, 5,000 JPY |
| {00007} | `<credit_union>` | Banks | HSBC, Bank of America |
| {00008} | `<airport_name>` | Major airports | Heathrow, Narita |
| {00009} | `<credit_union_card>` | Bank cards | Barclays card, Chase card |
| {00010} | `<gov_housing_agency>` | Housing departments | HUD, Council Housing |

### Government & Services (00011-00020)
| Code | Tag | Description | Example |
|------|-----|-------------|---------|
| {00011} | `<housing_purchase_benefit>` | Housing programs | First-time buyer scheme |
| {00012} | `<telecom_regulator>` | Telecom authority | FCC, Ofcom |
| {00013} | `<courier_service>` | Delivery companies | DHL, FedEx, local post |
| {00014} | `<social_media>` | Social platforms | WhatsApp, WeChat, Line |
| {00015} | `<gov_health_agency>` | Health departments | NHS, CDC |
| {00016} | `<marketplace>` | Shopping venues | Amazon, Tesco, Carrefour |
| {00017} | `<money_amount_very_small>` | $5-$20 equivalent | 10 USD, 1,000 JPY |
| {00018} | `<brokerage_firm>` | Investment firms | Charles Schwab, E*TRADE |
| {00019} | `<real_estate_company>` | Property developers | RE/MAX, Century 21 |
| {00020} | `<singer_name>` | Popular artists | Local celebrities |

### Business & Finance (00021-00033)
| Code | Tag | Description | Example |
|------|-----|-------------|---------|
| {00021} | `<important_contact>` | Titles of respect | Boss, Sir, Sensei |
| {00022} | `<bank_name>` | Major banks | Citibank, Barclays |
| {00023} | `<telecom_service_provider>` | Mobile carriers | Verizon, Vodafone |
| {00024} | `<telecom_authority>` | Same as {00012} | Use same values |
| {00025} | `<cosmetic_brand>` | Beauty brands | L'Oréal, Shiseido |
| {00026} | `<consumer_protection_agency>` | Consumer agencies | FTC, Trading Standards |
| {00027} | `<payment_app>` | Digital wallets | PayPal, Alipay |
| {00028} | `<card_network_loyalty>` | Rewards programs | Miles&More, Nectar |
| {00029} | `<motor_vehicle_authority>` | DMV equivalent | DVLA, RTA |
| {00030} | `<car_brand>` | Car manufacturers | Toyota, Ford, BMW |
| {00031} | `<dairy_store>` | Dairy brands | Danone, Yakult |
| {00032} | `<student_loan_office>` | Education loans | Student Finance, FAFSA |
| {00033} | `<internet_service_provider>` | ISPs | Comcast, BT, NTT |

### Additional Categories (00034-00053)
| Code | Tag | Description | Example |
|------|-----|-------------|---------|
| {00034} | `<state_name>` | States/provinces | California, Ontario |
| {00035} | `<region_name>` | Broader regions | Southeast Asia, EU |
| {00036} | `<country_name>` | Country variations | USA, United States |
| {00037} | `<police>` | Police force | NYPD, Met Police |
| {00038} | `<criminal_investigation_department>` | CID units | FBI, Scotland Yard |
| {00039} | `<police_station>` | Station names | Central Station |
| {00040} | `<police_station_name>` | More stations | District stations |
| {00041} | `<education_institution>` | Universities | Harvard, Oxford |
| {00042} | `<education_agency>` | Education ministry | Dept of Education |
| {00043} | `<loan_department>` | Loan offices | Personal Loans Dept |
| {00044} | `<telecom_tv_provider>` | TV services | Sky, Comcast |
| {00045} | `<telecom_tv_service>` | TV packages | Basic cable, Premium |
| {00046} | `<ISP_name>` | ISP names | AT&T, Virgin Media |
| {00047} | `<ecommerce_platform_name>` | Online stores | eBay, Alibaba |
| {00048} | `<product_name>` | Products | iPhone, Galaxy |
| {00049} | `<fruit>` | Local fruits | Apples, mangoes |
| {00050} | `<gov_agency_housing>` | Housing dept variant | Same as {00010} |
| {00051} | `<vehicle_department>` | Vehicle registration | DMV, DVLA |
| {00052} | `<rigion_name>` | Region (typo) | Same as {00035} |
| {00053} | `<police_station>` | Police station (dup) | Special stations |

## Cultural Considerations

### Language Style
- **Formality Level**: Consider whether the culture uses formal/informal speech
- **Honorifics**: Include appropriate titles and honorifics
- **Phone Greetings**: Use culturally appropriate phone greetings

### Scam Patterns
- Research common scam types in the region
- Adapt scenarios to local context
- Consider local regulatory agencies

### Currency and Amounts
- Use realistic amounts for the local economy
- Consider purchasing power parity
- Include currency symbols correctly

## Voice Selection

### ElevenLabs Voice Selection Criteria
1. **Native Accent**: Voices should have authentic regional accents
2. **Age Diversity**: Include young, middle-aged, and elderly voices
3. **Gender Balance**: Mix of male and female voices
4. **Voice Quality**: Clear pronunciation suitable for phone calls

### Finding Voice IDs
1. Log into ElevenLabs dashboard
2. Browse voice library
3. Filter by language and accent
4. Test voices with sample text
5. Note the voice_id for each selected voice

## Testing Checklist

### Pre-Pipeline Testing
- [ ] Configuration follows the **new standardized structure**
- [ ] All required sections are present: `locale`, `translation`, `voices`, `conversation`, `output`
- [ ] All 53 placeholders have substitutions
- [ ] Translations are accurate and culturally appropriate
- [ ] Voice IDs are valid and tested
- [ ] Currency codes and symbols are correct

### Pipeline Testing
1. **Run preprocessing**:
   ```bash
   python main.py --locale [locale-code] --steps preprocess
   ```

2. **Check translations**:
   ```bash
   python main.py --locale [locale-code] --steps translate
   ```

3. **Generate sample conversations**:
   ```bash
   python main.py --locale [locale-code] --steps conversation --sample-limit 5
   ```

4. **Test TTS generation**:
   ```bash
   python main.py --locale [locale-code] --steps tts --sample-limit 2
   ```

### Quality Checks
- [ ] Placeholder substitutions appear natural
- [ ] Conversations sound culturally authentic
- [ ] Audio quality is clear
- [ ] Phone effects applied correctly
- [ ] JSON output properly formatted

## Troubleshooting

### Common Issues

1. **"'locale' KeyError"**:
   - **Cause**: Configuration file uses old format
   - **Solution**: Update to new standardized structure with `"locale"` section
   - **Fix**: Follow the Configuration Structure section above exactly

2. **Missing placeholders error**:
   - Ensure all {00001} through {00053} are defined
   - Check for typos in placeholder codes

3. **Translation failures**:
   - **"No support for the provided language"**: Use correct Google Translate codes
     - Hong Kong/Taiwan: `"zh-TW"` (not `"zh-HK"`)
     - Singapore/Mainland China: `"zh-CN"` (not `"zh"`)
     - Other languages: Use standard ISO codes
   - Verify language codes are correct
   - Check Google Translate API limits
   - Consider using Argos for offline translation

4. **Voice synthesis errors**:
   - Confirm ElevenLabs API key is valid
   - Verify voice IDs exist
   - Check API quota limits

5. **Cultural inappropriateness**:
   - Review with native speakers
   - Adjust formality levels
   - Update placeholder substitutions

### Debug Commands

```bash
# Validate configuration
python main.py --validate-config [locale-code]

# Test single step with verbose output
python main.py --locale [locale-code] --steps preprocess --verbose

# Generate small test batch
python main.py --locale [locale-code] --sample-limit 5
```

## Adding to locale_road_map.md

Once implemented, update the roadmap with:
- Status: ✅ Completed
- Implementation date
- Any special notes
- Placeholder coverage (53/53)

## Support

For questions or issues:
- Check existing locale implementations for examples
- Review error logs in `logs/` directory
- Consult the main README.md
- Open an issue in the repository