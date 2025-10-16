#!/bin/bash
# Quick test for natural Malay conversation generation
# 2 scam + 2 legit conversations with GPT-5 medium reasoning

echo "=========================================="
echo "Quick Natural Malay Test (2+2)"
echo "=========================================="
echo ""
echo "Model: GPT-5"
echo "Reasoning: Medium"
echo "Temperature: 1.1"
echo "Turns per conversation: 20-24"
echo ""
echo "Generating 1 scam + 1 legit conversations..."
echo "Expected time: ~6-8 minutes total"
echo ""

python main.py --locale ms-my \
  --steps conversation legit \
  --scam-limit 1 \
  --legit-limit 1 \
  --force

echo ""
echo "=========================================="
echo "✓ Generation Complete!"
echo "=========================================="
echo ""
echo "Output: output/ms-my/[timestamp]/conversations/"
echo ""
echo "Check for natural Malay features:"
echo "  ✓ Particles: lah, kan, je, tak, dah, nak"
echo "  ✓ Casual greetings: Hai, Eh (not Selamat pagi)"
echo "  ✓ Code-switching with English"
echo "  ✓ Informal pronouns: awak > anda"
echo "  ✓ Natural fillers: hmm, eh, macam"
echo "  ✓ Less formal: reduce sila, terima kasih, adakah"
echo ""

