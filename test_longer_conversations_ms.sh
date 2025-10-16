#!/bin/bash
# Test longer conversation generation with Malaysian locale

echo "Testing longer conversations with Malaysian locale (ms-my)"
echo "Generating 10 scam and 10 legit conversations with 20-24 turns"

# Generate small test batch
python main.py --locale ms-my \
  --steps conversation legit \
  --scam-limit 10 \
  --legit-limit 10 \
  --force

echo ""
echo "Generation complete. Check output/ms-my/[timestamp]/conversations/"
echo ""
echo "Review for:"
echo "  - Turn counts (should be 20-24)"
echo "  - Conversation quality and coherence"
echo "  - Natural flow without repetition"
echo "  - Appropriate conversation length and depth"

