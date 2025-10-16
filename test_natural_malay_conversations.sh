#!/bin/bash
# Test improved natural Malay conversation generation
# Using GPT-5 with medium reasoning and colloquial instructions

echo "=========================================="
echo "Testing Natural Malay Conversation Generation"
echo "=========================================="
echo ""
echo "Model: GPT-5 (full model)"
echo "Reasoning Effort: Medium"
echo "Temperature: 1.1"
echo "Frequency Penalty: 0.3"
echo ""
echo "Generating 5 scam + 5 legit conversations with:"
echo "  - Colloquial Malay instructions"
echo "  - Natural speech patterns (lah, kan, je, etc.)"
echo "  - Code-switching examples"
echo "  - 20-24 turns per conversation"
echo ""
echo "=========================================="

# Generate small test batch
python main.py --locale ms-my \
  --steps conversation legit \
  --scam-limit 5 \
  --legit-limit 5 \
  --force

echo ""
echo "=========================================="
echo "Generation complete!"
echo "=========================================="
echo ""
echo "Output location: output/ms-my/[timestamp]/conversations/"
echo ""
echo "Quality Checklist - Review for:"
echo "✓ Turn counts (20-24)"
echo "✓ Natural Malay particles: lah, kan, je, tak, dah, nak"
echo "✓ Casual greetings: Hai, Eh, instead of formal Selamat pagi"
echo "✓ Code-switching with English words"
echo "✓ Incomplete sentences and natural pauses"
echo "✓ Less formal pronouns: awak instead of anda, saya but also aku"
echo "✓ Reduced usage of: sila, terima kasih, adakah"
echo "✓ Natural fillers: hmm, eh, macam, betul ke"
echo ""
echo "Compare with previous formal output to see improvements!"

