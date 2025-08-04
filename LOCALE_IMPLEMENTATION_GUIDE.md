# Locale Implementation Guide

This guide provides step-by-step instructions for adding new locales to the voice scam dataset generation pipeline.

## User critical instructions
**make sure you do your research (use web search to get the accurate subisitue)**
- checkout the locale you are working on first on @locale_road_map.md i.e mark the status as in progress at the very beginning so that other people know you are working on it.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Placeholder Reference](#placeholder-reference)
5. [Cultural Considerations](#cultural-considerations)
6. [Voice Selection](#voice-selection)
7. [Testing Checklist](#testing-checklist)
8. [Troubleshooting](#troubleshooting)

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

Edit `configs/localizations/[locale-code]/config.json`:

1. **Update locale information:**
   ```json
   {
     "locale_code": "ko-kr",
     "locale_name": "Korean - South Korea",
     "language_code": "ko",
     "language_name": "Korean",
     "region": "South Korea"
   }
   ```

2. **Set translation paths:**
   ```json
   "translation": {
     "from_code": "zh",      // Source (Chinese)
     "to_code": "ko",        // Target language
     "intermediate_code": "en" // English as intermediate
   }
   ```

3. **Add ElevenLabs voice IDs:**
   ```json
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
   }
   ```

4. **Update output paths:**
   ```json
   "output_paths": {
     "scam_conversation": "scam_conversation_ko-kr.json",
     "legit_conversation": "legit_conversation_ko-kr.json",
     // ... update all paths with locale code
   }
   ```

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
- [ ] All 53 placeholders have substitutions
- [ ] Translations are accurate and culturally appropriate
- [ ] Voice IDs are valid and tested
- [ ] Config paths use correct locale code
- [ ] Currency amounts are realistic

### Pipeline Testing
1. **Run preprocessing**:
   ```bash
   python main.py --language [locale-code] --steps preprocess
   ```

2. **Check translations**:
   ```bash
   python main.py --language [locale-code] --steps translate
   ```

3. **Generate sample conversations**:
   ```bash
   python main.py --language [locale-code] --steps conversation --limit 5
   ```

4. **Test TTS generation**:
   ```bash
   python main.py --language [locale-code] --steps tts --limit 2
   ```

### Quality Checks
- [ ] Placeholder substitutions appear natural
- [ ] Conversations sound culturally authentic
- [ ] Audio quality is clear
- [ ] Phone effects applied correctly
- [ ] JSON output properly formatted

## Troubleshooting

### Common Issues

1. **Missing placeholders error**:
   - Ensure all {00001} through {00053} are defined
   - Check for typos in placeholder codes

2. **Translation failures**:
   - Verify language codes are correct
   - Check Google Translate API limits
   - Consider using Argos for offline translation

3. **Voice synthesis errors**:
   - Confirm ElevenLabs API key is valid
   - Verify voice IDs exist
   - Check API quota limits

4. **Cultural inappropriateness**:
   - Review with native speakers
   - Adjust formality levels
   - Update placeholder substitutions

### Debug Commands

```bash
# Validate configuration
python main.py --validate-config [locale-code]

# Test single step with verbose output
python main.py --language [locale-code] --steps preprocess --verbose

# Generate small test batch
python main.py --language [locale-code] --limit 5
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