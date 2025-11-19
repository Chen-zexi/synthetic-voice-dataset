# Malaysian Conversation Generation Improvements

**Date**: Latest Session  
**Locale**: ms-my (Malay - Malaysia)  
**Focus**: Quality improvements, diversity measurement, and length/turn target optimization

## Overview

This document summarizes the latest improvements made to the Malaysian (ms-my) conversation generation pipeline, focusing on qualitative enhancements based on human labeler feedback, diversity measurement capabilities, and optimization of conversation length and turn counts.

## Key Changes Summary

### 1. Syllable Target Updates
- **Previous Target**: 1,400-1,650 syllables
- **New Target**: 1,500-1,750 syllables
- **Sweet Spot**: 1,625 syllables
- **Applied To**: Both scam and legitimate conversations
- **Files Modified**:
  - `src/conversation/scam_generator.py`
  - `src/conversation/legit_generator.py`

### 2. Turn Count Configuration
- **Previous**: Not explicitly configured in common.json
- **New**: 38-45 turns (lower limit: 38, upper limit: 45)
- **File Modified**: `configs/common.json`
- **Impact**: Ensures conversations have sufficient length to meet syllable targets

### 3. Diversity Measurement System
- **New Script**: `scripts/measure_diversity.py`
- **Purpose**: Measure diversity of names, institutions, and conversation types
- **Metrics**:
  - Unique count and percentage
  - Shannon entropy (diversity score)
  - Distribution statistics
  - Most common entities (top 10)

**Usage**:
```bash
python scripts/measure_diversity.py /path/to/scam_labeling
python scripts/measure_diversity.py /path/to/legit_labeling
python scripts/measure_diversity.py /path/to/scam_labeling /path/to/legit_labeling --json
```

### 4. Enhanced Prompt Engineering

#### Scam Generator Improvements (`src/conversation/scam_generator.py`)

**Added Sections**:

1. **Naming Conventions (CRITICAL - Malaysian Context)**
   - Clarifies correct use of honorifics with surnames/given names
   - Examples: "Encik Ahmad" (not "Encik Ahmad bin Hassan" in casual contexts)
   - Proper use of "Puan", "Cik", "Tuan" based on context

2. **Code-Switching Fluency (Natural Transitions)**
   - Guidelines for natural mixing of Malay and English
   - Emphasis on context-appropriate code-switching
   - Avoids forced or awkward language mixing

3. **Malaysian Institution/Department Validation (CRITICAL)**
   - Enforces correct department-agency pairings:
     - KWSP issues → KWSP (not LHDN)
     - Tax issues → LHDN (not KWSP)
     - Traffic summonses → Jabatan Siasatan Dan Penguatkuasaan Trafik
   - Full official department names required
   - Realistic communication methods (no WhatsApp for official government matters)
   - No aggressive utility company calls (TNB doesn't chase fees aggressively)

4. **Malaysian Realism Validation - CRITICAL REQUIREMENTS**
   - Scam execution must match seed summary
   - Realistic communication methods
   - Correct department-agency pairings
   - Natural family call openings

5. **Victim Behavior Guidance**
   - Strengthened guidance for "tiny aware" victims
   - Must maintain skepticism and show independent thinking
   - Should attempt verification
   - Explicitly states they are "NOT easily convinced"

**Enhanced Methods**:
- `_sample_org_values`: Now includes Malaysian-specific department mappings for KWSP, LHDN, MySikap/Traffic, and TNB

#### Legit Generator Improvements (`src/conversation/legit_generator.py`)

**Major Additions**:

1. **Placeholder Loading and Tracking**
   - Added `_load_placeholder_mappings()` method
   - Loads `placeholders.json` for the current locale
   - Enables proper name/institution tracking

2. **Organization Value Sampling**
   - Added `_sample_org_values_for_category()` method
   - Maps legit categories to relevant placeholder keys:
     - Bank categories → `bank_name_local`
     - Clinic/hospital → `health_services_provider_name`, `health_insurance_provider_name`
     - School/education → `university_or_school_name`, `bursar_or_student_finance_office_name`
     - Telecom → `telecom_provider_name_local`
     - Utility → `local_utility_provider_name`
     - Government → `housing_authority_name`, `public_health_agency_name`
     - Immigration → `passport_authority_name_local`
     - Technical support → `company_it_department_name`
     - And more...

3. **Naming Conventions (CRITICAL - Malaysian Context)**
   - Same improvements as scam generator
   - Proper honorific usage
   - Context-appropriate naming

4. **Code-Switching Fluency**
   - Natural language mixing guidelines
   - Context-appropriate transitions

5. **Malaysian Institution/Department Validation**
   - Correct use of "Jabatan" for government offices
   - Full official department names
   - Realistic communication methods
   - Correct department-agency pairings

6. **Malaysian Realism Validation**
   - Specifically for "Family Call Openings"
   - Natural greetings and clear relationship context
   - Avoids awkward introductions like "Hi, I am XXX, your brother"

7. **Structured Conversation Phases (Flexible)**
   - Replaced rigid "Conversation Progression" with flexible framework
   - 6 phases: Opening, Purpose, Detailed Discussion, Problem-Solving, Confirmation, Closure
   - Adapts based on complexity:
     - **COMPLEX**: Full 6-phase structure (appointments, verifications, consultations)
     - **MODERATE**: Condensed phases 3-4, shorter phases 5-6
     - **SIMPLE**: Condensed phases 3-4 into single "Main Discussion", shorter closure
   - Guidelines for adapting turn counts and depth

8. **Category-Specific Complexity Guidelines**
   - Explicit classification: COMPLEX, MODERATE, or SIMPLE
   - Examples of how to adapt structured phases
   - Expansion strategies for different conversation types

**Fixed Issues**:
- Missing `Path` import (added `from pathlib import Path`)
- Placeholder tracking now works correctly for legit conversations
- Institution diversity tracking functional

### 5. Legit Category Management

**Category Expansion and Validation**:
- Expanded from 35 to 42 categories
- Added categories with real Malaysian institutions:
  - `government_permit_inquiry`
  - `immigration_document_followup`
  - `billing_dispute_resolution`
  - `technical_support_call`
  - And more...

**Validation Process**:
- Reviewed `placeholders.json` to ensure all categories have corresponding real Malaysian institutions
- Reverted categories that lacked strong institutional mappings
- Final count: 42 categories, all with real institution support

**Current Categories** (42 total):
```json
[
  "family_checkin", "friend_chat", "relationship_talk", "holiday_greeting",
  "emergency_help_request", "doctor_appointment_confirmation", "clinic_test_results",
  "delivery_confirmation", "utility_service_followup", "repair_scheduling",
  "bank_verification_call", "visa_status_update", "tax_inquiry",
  "insurance_claim_followup", "civil_services_scheduling", "job_interview_scheduling",
  "coworker_sync", "project_status_update", "freelance_client_call",
  "work_meeting_reminder", "school_event_reminder", "tutoring_session",
  "academic_advising", "exam_results_notification", "class_schedule_change",
  "restaurant_reservation", "hairdresser_booking", "hotel_booking_confirmation",
  "volunteering_coordination", "language_exchange_call", "customer_support_callback",
  "subscription_renewal_notice", "product_feedback_survey", "account_security_verification",
  "appointment_cancellation_notice", "internet_service_inquiry", "mobile_plan_upgrade",
  "insurance_policy_review", "government_permit_inquiry", "immigration_document_followup",
  "billing_dispute_resolution", "technical_support_call"
]
```

## Human Labeler Feedback Addressed

### Issues Identified and Fixed

1. **"Callee is easily convinced, lack of independent thinking"**
   - **Fix**: Strengthened victim behavior guidance for "tiny aware" victims
   - **Location**: `scam_generator.py` prompt

2. **"Grammar errors, code-switching not fluent enough"**
   - **Fix**: Added "Code-Switching Fluency" section with natural transition guidelines
   - **Location**: Both `scam_generator.py` and `legit_generator.py`

3. **"Illogical family call openings"**
   - **Fix**: Added "Malaysian Realism Validation" with specific family call opening guidelines
   - **Location**: `legit_generator.py`

4. **"Incorrect use of 'Jabatan' for government offices"**
   - **Fix**: Added "Malaysian Institution/Department Validation" section
   - **Location**: Both generators

5. **"Wrong department handling issues (e.g., KWSP handled by LHDN)"**
   - **Fix**: Enhanced `_sample_org_values` with Malaysian-specific department mappings
   - **Location**: `scam_generator.py`

6. **"TNB chasing electric fees over phone (unrealistic)"**
   - **Fix**: Added validation against aggressive utility company calls
   - **Location**: `scam_generator.py`

7. **"Government offices using WhatsApp (unrealistic)"**
   - **Fix**: Added validation for realistic communication methods
   - **Location**: Both generators

8. **"Naming conventions incorrect (e.g., 'Encik Wen Jie' should be 'Encik surname')"**
   - **Fix**: Added comprehensive "Naming Conventions" section
   - **Location**: Both generators

## Current Performance Metrics

### From 10k Legit Conversations Analysis

**Name Diversity**:
- Unique Names: 180
- Total Name Occurrences: 20,000
- Unique Percentage: 1.8% (excellent distribution)
- Shannon Entropy: 7.492 (max: 7.492)
- Diversity Score: 1.000 (perfect)

**Institution Diversity**:
- Unique Institutions: 41
- Total Institution Occurrences: 1,942 (~19.4% of conversations)
- Unique Percentage: 0.4%
- Shannon Entropy: 5.031 (max: 5.358)
- Diversity Score: 0.939 (excellent)

**Conversation Type Diversity**:
- Unique Types: 42 (all categories represented)
- Perfect distribution (2.5-2.6% per category)
- Shannon Entropy: 5.390 (max: 5.392)
- Diversity Score: 1.000 (perfect)

**Length Metrics**:
- Average Syllables: 1,373 (target: 1,500-1,750)
- % Meeting >=1,500: 34.7% (needs improvement)
- Average Turns: 28.2 (target: 38-45)
- % Meeting >=20: 86.1%

### Known Issues

1. **Syllable Count**: Still below target (average 1,373 vs target 1,500-1,750)
   - Only 34.7% of conversations meet >=1,500 threshold
   - **Root Cause**: Turn count too low (28.2 vs target 38-45)
   - **Status**: Prompts updated, but LLM compliance needs improvement

2. **Turn Count**: Below target range (28.2 vs 38-45)
   - 13.9% of conversations have <20 turns
   - **Root Cause**: LLM ending conversations too early despite prompt instructions
   - **Status**: Requires further prompt strengthening or post-generation validation

## Files Modified

### Core Generation Files
1. `src/conversation/scam_generator.py`
   - Updated syllable targets (1,500-1,750)
   - Added naming conventions section
   - Added code-switching fluency guidelines
   - Added Malaysian institution/department validation
   - Added Malaysian realism validation
   - Enhanced victim behavior guidance
   - Enhanced `_sample_org_values` with Malaysian department mappings

2. `src/conversation/legit_generator.py`
   - Updated syllable targets (1,500-1,750)
   - Added `_load_placeholder_mappings()` method
   - Added `_sample_org_values_for_category()` method
   - Integrated placeholder tracking in `_generate_single_conversation`
   - Added naming conventions section
   - Added code-switching fluency guidelines
   - Added Malaysian institution/department validation
   - Added Malaysian realism validation
   - Replaced rigid conversation progression with flexible structured phases
   - Added category-specific complexity guidelines
   - Fixed missing `Path` import

### Configuration Files
3. `configs/common.json`
   - Updated `followup_turns.num_turns_lower_limit`: 38
   - Updated `followup_turns.num_turns_upper_limit`: 45

4. `configs/localizations/ms-my/config.json`
   - Expanded `legit_categories` from 35 to 42
   - Validated all categories have real Malaysian institution support

### New Scripts
5. `scripts/measure_diversity.py` (NEW)
   - Comprehensive diversity measurement tool
   - Calculates Shannon entropy, unique percentages, distribution stats
   - Supports both scam and legit conversations
   - Outputs human-readable reports and optional JSON

### Documentation
6. `README.md`
   - Added "Quality Assessment & Analysis Tools" section
   - Documented diversity measurement script
   - Documented batch audit script
   - Updated project structure to include scripts directory

## Usage Examples

### Generating Conversations with New Targets

```bash
# Generate scam conversations (will use 1,500-1,750 syllable target)
python generate_for_labeling.py --type scam --count 250

# Generate legit conversations (will use 1,500-1,750 syllable target, 38-45 turns)
python generate_for_labeling.py --type legit --count 250
```

### Analyzing Diversity

```bash
# Analyze scam conversation diversity
python scripts/measure_diversity.py scam_labeling/

# Analyze legit conversation diversity
python scripts/measure_diversity.py legit_labeling/

# Analyze both and output JSON report
python scripts/measure_diversity.py scam_labeling/ legit_labeling/ --json
```

### Auditing Batches

```bash
# Quick audit of generated conversations
python scripts/audit_ms_my_batch.py legit_labeling/
python scripts/audit_ms_my_batch.py scam_labeling/
```

## Next Steps / Recommendations

### Immediate Improvements Needed

1. **Strengthen Turn Count Enforcement**
   - Current: LLM not consistently following 38-45 turn requirement
   - Solution: Add more explicit examples, stronger rejection language, or post-generation validation

2. **Improve Syllable Count Compliance**
   - Current: Only 34.7% meet >=1,500 threshold
   - Solution: Strengthen per-turn syllable guidance, add more examples of longer turns

3. **Post-Generation Validation**
   - Consider adding validation step that rejects conversations below thresholds
   - Regenerate conversations that don't meet requirements

### Future Enhancements

1. **Category Complexity Auto-Classification**
   - Automatically classify categories as COMPLEX/MODERATE/SIMPLE
   - Adjust phase structure accordingly

2. **Real-Time Diversity Monitoring**
   - Track diversity metrics during generation
   - Adjust sampling to improve diversity in real-time

3. **Institution Mapping Validation**
   - Automated check that all categories have corresponding institutions
   - Prevent adding categories without institution support

## Technical Notes

### Placeholder Tracking

The legit generator now properly tracks names and institutions through:
- `placeholders_used` dictionary in conversation metadata
- Keys tracked: `caller_name`, `callee_name`, and all `ORG_KEYS` from `measure_diversity.py`

### Diversity Metrics

The diversity measurement script uses:
- **Shannon Entropy**: Measures distribution evenness (higher = more diverse)
- **Diversity Score**: Normalized entropy (0-1 scale, 1 = perfect diversity)
- **Unique Percentage**: Percentage of unique items out of total occurrences

### Prompt Structure

Both generators now use a hierarchical prompt structure:
1. Core task and requirements
2. Length requirements (syllable targets)
3. Quality guidelines
4. Cultural/contextual validations
5. Structured phase guidelines (legit only)
6. Examples and verification steps

## Related Documentation

- `QUALITY_IMPROVEMENTS_SUMMARY.md`: Previous quality improvements
- `LABELING_GENERATION_README.md`: Human labeling workflow
- `LOCALE_IMPLEMENTATION_GUIDE.md`: Locale implementation details
- `README.md`: Main project documentation

## Conclusion

These improvements significantly enhance the quality and realism of Malaysian conversation generation, addressing specific feedback from human labelers while maintaining the flexibility and diversity of the generation system. The addition of diversity measurement tools provides quantitative insights into conversation quality, enabling data-driven improvements.

**Key Achievements**:
- ✅ Enhanced cultural realism (naming, institutions, communication methods)
- ✅ Improved code-switching fluency
- ✅ Better victim behavior modeling
- ✅ Comprehensive diversity measurement
- ✅ Flexible conversation structure for legit conversations
- ✅ Proper placeholder tracking for legit conversations

**Areas for Continued Improvement**:
- ⚠️ Turn count compliance (28.2 vs 38-45 target)
- ⚠️ Syllable count compliance (34.7% meeting >=1,500 threshold)
- ⚠️ LLM prompt adherence (may require stronger enforcement or validation)

