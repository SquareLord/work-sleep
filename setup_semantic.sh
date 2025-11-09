#!/bin/bash

# Quick Setup Script for Semantic Task Matching

echo "🤖 Semantic Task Matching Setup"
echo "================================"
echo ""

# Check if HUGGINGFACE_API_KEY is set
if [ -z "$HUGGINGFACE_API_KEY" ]; then
    echo "⚠️  HUGGINGFACE_API_KEY not found!"
    echo ""
    echo "To enable AI-powered semantic matching:"
    echo ""
    echo "1. Get a FREE API key from https://huggingface.co/settings/tokens"
    echo "2. Run this command:"
    echo ""
    echo "   export HUGGINGFACE_API_KEY='hf_your_token_here'"
    echo ""
    echo "3. Or add to ~/.bashrc for permanent setup:"
    echo ""
    echo "   echo \"export HUGGINGFACE_API_KEY='hf_your_token_here'\" >> ~/.bashrc"
    echo "   source ~/.bashrc"
    echo ""
    echo "The app will work without it, but will use basic keyword matching."
else
    echo "✅ HUGGINGFACE_API_KEY is set!"
    echo ""
    echo "Running test to verify API connection..."
    echo ""
    /home/abhiramk/Documents/hack-princeton/.venv/bin/python test_semantic_matching.py
fi

echo ""
echo "📚 For more info, see: SEMANTIC_MATCHING.md"
