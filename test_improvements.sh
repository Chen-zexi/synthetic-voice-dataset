#!/bin/bash
# Test script for improvements: length requirements and organization diversity
# This script generates test conversations and audits them

set -e  # Exit on error

echo "=========================================="
echo "TESTING IMPROVEMENTS"
echo "=========================================="
echo ""
echo "This will:"
echo "1. Generate 50 scam conversations (test batch)"
echo "2. Generate 25 legit conversations (test batch)"
echo "3. Run audit on both batches"
echo "4. Display results"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "STEP 1: Generating 50 scam conversations"
echo "=========================================="
uv run python generate_for_labeling.py --type scam --count 50

echo ""
echo "=========================================="
echo "STEP 2: Generating 25 legit conversations"
echo "=========================================="
uv run python generate_for_labeling.py --type legit --count 25

echo ""
echo "=========================================="
echo "STEP 3: Auditing scam conversations"
echo "=========================================="
uv run python scripts/audit_ms_my_batch.py scam_labeling/

echo ""
echo "=========================================="
echo "STEP 4: Auditing legit conversations"
echo "=========================================="
uv run python scripts/audit_ms_my_batch.py legit_labeling/

echo ""
echo "=========================================="
echo "TESTING COMPLETE"
echo "=========================================="
echo ""
echo "Review the audit results above to check:"
echo "  ✓ Average syllable count (target: >=1500)"
echo "  ✓ Percentage meeting 1500+ syllable requirement (target: 100%)"
echo "  ✓ Name diversity (fewer repetitions = better)"
echo "  ✓ Organization diversity (fewer repetitions = better)"
echo "  ✓ Average conversation length in minutes (target: <5 min)"
echo ""
echo "Next steps:"
echo "  - If results look good, generate larger batches"
echo "  - If syllable counts are still low, we may need to adjust prompts further"
echo "  - If name/org repetition is high, we may need to expand placeholders more"
echo ""

