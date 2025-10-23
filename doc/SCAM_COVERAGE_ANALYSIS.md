# Scam Type Coverage Analysis vs LG Specifications

**Date**: October 22, 2025  
**Purpose**: Document current scam type coverage relative to LG's required specifications

## Executive Summary

This document analyzes our current scam seed coverage against LG's specifications to identify alignment and potential gaps for future dataset development.

---

## LG Specifications Requirements

Based on the "Specifications for Training Data" document, LG requires scam data distributed across these categories:

| Category | Target % | Description | Meta Tag |
|----------|----------|-------------|----------|
| **Macau Scam** | 33.2% | Government/authority impersonation | "Macau Scam" |
| **E-commerce Fraud** | 30.0% | Delivery, online shopping, voice AI, SMS phishing, social media giveaways | Multiple tags |
| **Investment Fraud** | 15.6% | High-return investment promises | "Investment Scam" |
| **Loan Fraud** | 12.3% | Easy loan offers with upfront fees | "Loan Fraud" |
| **Other** | ~9% | Additional scam types | Various |

### E-commerce Fraud Breakdown:
- Delivery Scam: Package delivery fraud
- E-commerce Fraud: Non-existent products
- Voice Scam: AI-cloned voice impersonation
- SMS Scam: Phishing SMS with payment links
- Giveaway Scam: Social media prize scams

---

## Current Seed Inventory

### General Seed File (`data/input/seeds_and_placeholders.json`)

**Total Seeds**: 57

**Distribution by Tag**:
```
utility                       : 12 seeds (21.1%)
government                    :  9 seeds (15.8%)
bank                          :  7 seeds (12.3%)
romance                       :  6 seeds (10.5%)
business_opportunity          :  5 seeds ( 8.8%)
tech_support                  :  5 seeds ( 8.8%)
health                        :  5 seeds ( 8.8%)
education                     :  4 seeds ( 7.0%)
employment                    :  1 seeds ( 1.8%)
charity                       :  1 seeds ( 1.8%)
lottery                       :  1 seeds ( 1.8%)
sextortion                    :  1 seeds ( 1.8%)
```

**Distribution by Category**:
```
services                      : 13 seeds (22.8%)
employment_education          : 10 seeds (17.5%)
government_legal              :  9 seeds (15.8%)
relationships                 :  7 seeds (12.3%)
banking                       :  7 seeds (12.3%)
healthcare                    :  5 seeds ( 8.8%)
technology                    :  5 seeds ( 8.8%)
prizes_rewards                :  1 seeds ( 1.8%)
```

### Malaysian-Specific Seeds (`data/input/malaysian_voice_phishing_seeds_2025.json`)

**Total Seeds**: 19

**All Seeds** (each appears once, 5.3%):
```
macau_pdrm                    pos_laju_delivery
bank_negara_credit            j_and_t_parcel
tac_wrong_number              easy_loan_app
maybank_suspension            bank_personal_loan
lhdn_tax_arrears              lottery_winner_4d
love_scam_engineer            insurance_claim_aia
crypto_investment_guru        job_scam_singapore
epf_kwsp_withdrawal           astro_technician
tnb_disconnection             medical_emergency_child
mysikap_summons
```

---

## Mapping to LG Categories

### Malaysian Seeds Mapped to LG Categories:

| LG Category | Seeds Included | Count | Current % | Target % | Gap |
|-------------|---------------|-------|-----------|----------|-----|
| **Macau Scam** | macau_pdrm, bank_negara_credit, lhdn_tax_arrears, mysikap_summons, epf_kwsp_withdrawal | 5 | 26.3% | 33.2% | -6.9% |
| **E-commerce Fraud** | pos_laju_delivery, j_and_t_parcel, astro_technician | 3 | 15.8% | 30.0% | -14.2% |
| **Investment Fraud** | crypto_investment_guru, love_scam_engineer | 2 | 10.5% | 15.6% | -5.1% |
| **Loan Fraud** | easy_loan_app, bank_personal_loan | 2 | 10.5% | 12.3% | -1.8% |
| **Other** | tac_wrong_number, maybank_suspension, tnb_disconnection, lottery_winner_4d, insurance_claim_aia, job_scam_singapore, medical_emergency_child | 7 | 36.8% | ~9% | +27.8% |

### Analysis:

**Well-Covered:**
- ✅ **Macau Scam**: 26.3% (target 33.2%) - Reasonably close, could add 1-2 more authority impersonation seeds
- ✅ **Loan Fraud**: 10.5% (target 12.3%) - Very close to target

**Under-Represented:**
- ⚠️ **E-commerce Fraud**: 15.8% (target 30.0%) - Needs 3-4 more seeds
  - Missing: Voice scam (AI voice cloning), SMS phishing scam, social media giveaway scam
- ⚠️ **Investment Fraud**: 10.5% (target 15.6%) - Needs 1-2 more seeds

**Over-Represented:**
- ⚠️ **Other Category**: 36.8% (target ~9%) - Many miscellaneous scams that don't fit LG's main categories

---

## Specific LG Subcategory Coverage

### Current Status:

| LG Subcategory | Current Coverage | Status |
|----------------|------------------|--------|
| **Macau Scam** | ✅ Yes | PDRM, Bank Negara, LHDN, MySikap |
| **Delivery Scam** | ✅ Yes | Pos Laju, J&T |
| **E-commerce Fraud** | ⚠️ Limited | Need more online shopping scams |
| **Voice Scam (AI)** | ❌ No | Need AI voice cloning scenario |
| **SMS Scam** | ❌ No | Need phishing SMS with links |
| **Giveaway Scam** | ❌ No | Need social media prize scam |
| **Investment Scam** | ✅ Yes | Crypto, romance investment |
| **Loan Fraud** | ✅ Yes | Easy loan app, personal loan |

---

## Recommendations for Future Development

### Priority 1: Fill E-commerce Gaps (High Priority)
To reach 30% target from current 15.8%:

1. **Voice Scam with AI Cloning** (2 seeds)
   - Boss impersonation with AI-cloned voice
   - Family member emergency with cloned voice

2. **SMS Phishing Scam** (2 seeds)
   - Bank SMS with phishing link
   - Government agency SMS (LHDN, MySikap) with fake link

3. **Social Media Giveaway Scam** (1 seed)
   - Facebook/Instagram prize winner requiring payment

4. **E-commerce Shopping Fraud** (1 seed)
   - Too-good-to-be-true online product sale

### Priority 2: Expand Investment Fraud (Medium Priority)
To reach 15.6% target from current 10.5%:

1. **Stock Investment Scam** (1 seed)
   - Guaranteed profit stock trading platform

### Priority 3: Expand Macau Scam (Low Priority)
To reach 33.2% target from current 26.3%:

1. **Immigration Scam** (1 seed)
   - Imigresen Malaysia threatening deportation

2. **Customs Scam** (1 seed)
   - Royal Malaysian Customs - package contraband

### Priority 4: Rebalance "Other" Category
Consider reclassifying some existing "Other" seeds into main categories where applicable.

---

## Current Pipeline Functionality

### Seed Distribution Control

Our pipeline supports controlled seed distribution through:

1. **Seed-based mode**: Use specific number of seeds
   ```bash
   --seed-limit 10 --scenarios-per-seed 3
   ```

2. **Conversation-based mode**: Target specific conversation count
   ```bash
   --conversation-count 100
   ```

3. **Quality filtering**: Filter seeds by quality score
   ```yaml
   generation_min_seed_quality: 70
   ```

### Achieving LG Distribution

To achieve LG's target distribution in a 10,000 conversation batch:

```bash
# Macau Scam: 3,320 conversations (33.2%)
python main.py --locale ms-my --scam --seed-filter macau --conversation-count 3320

# E-commerce: 3,000 conversations (30.0%)
python main.py --locale ms-my --scam --seed-filter ecommerce --conversation-count 3000

# Investment: 1,560 conversations (15.6%)
python main.py --locale ms-my --scam --seed-filter investment --conversation-count 1560

# Loan: 1,230 conversations (12.3%)
python main.py --locale ms-my --scam --seed-filter loan --conversation-count 1230

# Other: 890 conversations (8.9%)
python main.py --locale ms-my --scam --seed-filter other --conversation-count 890
```

*Note: `--seed-filter` functionality would need to be implemented if precise category control is required*

---

## Conclusion

### Current Status: **Good Foundation with Identified Gaps**

**Strengths:**
- Strong coverage of Macau Scam (government authority impersonation)
- Good foundation in Loan Fraud
- Well-structured Malaysian-specific seeds with local entities
- Flexible generation pipeline supporting various distribution strategies

**Gaps to Address:**
- E-commerce fraud subcategories (Voice AI, SMS, Giveaway) need expansion
- Investment fraud could use 1-2 more seeds
- "Other" category is over-represented relative to LG specifications

**Action Items:**
1. Create 6-8 new seeds for E-commerce subcategories (Voice, SMS, Giveaway)
2. Create 1-2 additional investment fraud seeds
3. Consider rebalancing existing "Other" seeds into main categories where applicable
4. Maintain current quality and diversity while expanding coverage

**Assessment**: Our pipeline is functionally sound and produces quality conversations. The main improvement area is seed inventory expansion to match LG's specific subcategory requirements, particularly in the E-commerce fraud category.

---

## Appendix: Seed File Locations

- **General Seeds**: `data/input/seeds_and_placeholders.json` (57 seeds)
- **Malaysian Seeds**: `data/input/malaysian_voice_phishing_seeds_2025.json` (19 seeds)
- **Configuration**: `configs/scenario_assignments_malaysia.json`
- **Generation Control Guide**: `GENERATION_CONTROL_GUIDE.md`


