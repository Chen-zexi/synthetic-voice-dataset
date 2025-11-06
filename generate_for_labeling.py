#!/usr/bin/env python3
"""
Generate conversations for human labeling.

This script generates Malaysian (ms-my) scam or legitimate conversations and saves them in two formats:
1. Default comprehensive JSON with all metadata in output/ms-my/{timestamp}/conversations/
2. Individual conversation JSON files in scam_labeling/ or legit_labeling/ directories

**NOTE: This is the preferred method for generating Malay (ms-my) conversations.**
This script is specifically streamlined for Malay conversation generation with proper configuration
loading, seed diversity management, and output formatting for labeling workflows.

Usage:
    python generate_for_labeling.py --type scam --count 250
    python generate_for_labeling.py --type legit --count 250
"""

import argparse
import asyncio
import json
import math
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from src.config.config_loader import ConfigLoader
from src.conversation.scam_generator import ScamGenerator
from src.conversation.legit_generator import LegitGenerator


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate conversations for human labeling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --type scam --count 250    # Generate 250 scam conversations
  %(prog)s --type legit --count 250   # Generate 250 legitimate conversations
        """
    )
    
    parser.add_argument(
        '--type',
        required=True,
        choices=['scam', 'legit'],
        help='Type of conversations to generate (scam or legit)'
    )
    
    parser.add_argument(
        '--count',
        type=int,
        required=True,
        help='Number of conversations to generate'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


def create_labeling_directories(conversation_type: str) -> Path:
    """
    Create labeling directory at project root.
    
    Args:
        conversation_type: 'scam' or 'legit'
        
    Returns:
        Path to the labeling directory
    """
    project_root = Path(__file__).parent
    labeling_dir = project_root / f"{conversation_type}_labeling"
    labeling_dir.mkdir(exist_ok=True)
    return labeling_dir


def save_individual_conversations(conversations: list, conversation_type: str, labeling_dir: Path):
    """
    Save each conversation as a separate JSON file.
    
    Args:
        conversations: List of conversation dictionaries
        conversation_type: 'scam' or 'legit'
        labeling_dir: Directory to save individual files
    """
    print(f"\nSaving individual conversation files to {labeling_dir}/")
    
    for conversation in conversations:
        # Use the conversation_id from the conversation object
        conv_id = conversation.get('conversation_id', 0)
        filename = f"{conversation_type}-{conv_id}.json"
        filepath = labeling_dir / filename
        
        # Save the entire conversation object (includes all metadata + dialogue)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved {len(conversations)} individual conversation files")


async def generate_scam_conversations(config, count: int):
    """
    Generate scam conversations with maximum seed diversity.
    
    Distributes conversations across available seeds for variety:
    - Dynamically counts available high-quality seeds
    - Calculates optimal scenarios_per_seed to use all available seeds
    - Each seed generates multiple conversations for target count
    - Higher counts automatically get more diversity
    
    Example: 250 conversations with 28 seeds = ~9 conversations per seed
    
    Args:
        config: Configuration object
        count: Number of conversations to generate
        
    Returns:
        Tuple of (conversations list, output JSON path)
    """
    print(f"Generating {count} scam conversations for ms-my locale...")
    
    # Load seed file to get actual count
    import json
    seed_file_path = config.base_dir / "data" / "input" / "malaysian_voice_phishing_seeds_2025.json"
    with open(seed_file_path, 'r') as f:
        all_seeds = json.load(f)
    
    # Filter by quality
    min_quality = getattr(config, 'generation_min_seed_quality', 70)
    available_seeds = len([s for s in all_seeds if int(s.get('quality_score', 0)) >= min_quality])
    
    # Calculate scenarios per seed to distribute conversations across all seeds
    # For 250 conversations with 28 seeds: ceil(250/28) = 9 per seed = 252 total (capped at 250)
    # For 2 conversations: ceil(2/28) = 1 per seed, but only 2 seeds will be used
    scenarios_per_seed = max(1, math.ceil(count / available_seeds))
    
    # Use conversation-based control mode for exact count with absolute cap
    config.generation_control_mode = "conversations"
    config.total_conversation_limit = count  # Target conversation count
    config.total_limit = count  # Absolute cap (stops at exactly this number)
    config.scenarios_per_seed = scenarios_per_seed
    
    # Calculate actual seeds that will be used
    seeds_used = min(available_seeds, math.ceil(count / scenarios_per_seed))
    
    print(f"Diversity strategy:")
    print(f"  - Target: {count} conversations (exact)")
    print(f"  - Available seeds: {available_seeds} (quality >= {min_quality})")
    print(f"  - Scenarios per seed: {scenarios_per_seed}")
    print(f"  - Seeds to use: ~{seeds_used}")
    print(f"  - Diversity: {seeds_used} different scam types")
    
    # Generate conversations
    generator = ScamGenerator(config)
    conversations = await generator.generate_conversations()
    
    # Get the output path from config
    output_path = config.multi_turn_output_path
    
    return conversations, output_path


async def generate_legit_conversations(config, count: int):
    """
    Generate legitimate conversations.
    
    Args:
        config: Configuration object
        count: Number of conversations to generate
        
    Returns:
        Tuple of (conversations list, output JSON path)
    """
    print(f"Generating {count} legitimate conversations for ms-my locale...")
    
    # Override limits in config
    config.legit_sample_limit = count
    config.total_limit = count
    
    # Generate conversations
    generator = LegitGenerator(config)
    conversations = await generator.generate_conversations()
    
    # Get the output path from config
    output_path = config.legit_call_output_path
    
    return conversations, output_path


def main():
    """Main execution function."""
    args = parse_arguments()
    
    print("=" * 80)
    print("CONVERSATION GENERATION FOR HUMAN LABELING")
    print("=" * 80)
    print(f"Type: {args.type.upper()}")
    print(f"Count: {args.count}")
    print(f"Locale: ms-my (Malaysian Malay)")
    print("=" * 80)
    
    # Load configuration for ms-my locale
    config_dir = Path(__file__).parent / "configs"
    output_dir = Path(__file__).parent / "output"
    
    config_loader = ConfigLoader(
        config_dir=str(config_dir),
        output_dir=str(output_dir),
        use_timestamp=True  # Use timestamp to avoid overwriting
    )
    
    # Load ms-my configuration
    config = config_loader.load_language(
        language='ms-my'
    )
    config.verbose = args.verbose
    
    # Create labeling directory
    labeling_dir = create_labeling_directories(args.type)
    
    # Generate conversations based on type
    if args.type == 'scam':
        conversations, output_path = asyncio.run(
            generate_scam_conversations(config, args.count)
        )
    else:
        conversations, output_path = asyncio.run(
            generate_legit_conversations(config, args.count)
        )
    
    # Load the generated JSON to get all conversations
    # (The generators save the full JSON automatically)
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            generated_data = json.load(f)
        
        # Extract conversations array
        conversations_list = generated_data.get('conversations', [])
        
        if conversations_list:
            # Save individual conversation files
            save_individual_conversations(conversations_list, args.type, labeling_dir)
            
            print("\n" + "=" * 80)
            print("GENERATION COMPLETE")
            print("=" * 80)
            print(f"✓ Default JSON saved to: {output_path}")
            print(f"✓ Individual files saved to: {labeling_dir}/")
            print(f"✓ Total conversations generated: {len(conversations_list)}")
            
            # Show token usage if available
            if 'estimated_cost' in generated_data:
                cost_info = generated_data['estimated_cost']
                print(f"\nEstimated Cost: ${cost_info.get('total_cost', 0):.4f}")
            
            print("=" * 80)
        else:
            print("\nWarning: No conversations found in generated JSON")
            sys.exit(1)
    else:
        print(f"\nError: Expected output file not found at {output_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()

