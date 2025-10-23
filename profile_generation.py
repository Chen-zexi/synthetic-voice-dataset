#!/usr/bin/env python3
"""
Performance profiling tool for conversation generation.
Identifies bottlenecks in the generation pipeline.
"""

import sys
import os
import time
import asyncio
import cProfile
import pstats
import io
from datetime import datetime

# Add src to Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from src.config.config_loader import ConfigLoader
from src.conversation.scam_generator import ScamGenerator


class PerformanceProfiler:
    """Profile conversation generation performance."""
    
    def __init__(self):
        self.timings = {}
        self.start_times = {}
    
    def start(self, label):
        """Start timing a section."""
        self.start_times[label] = time.time()
    
    def end(self, label):
        """End timing a section."""
        if label in self.start_times:
            elapsed = time.time() - self.start_times[label]
            self.timings[label] = elapsed
            return elapsed
        return 0
    
    def print_report(self):
        """Print timing report."""
        print("\n" + "="*80)
        print("PERFORMANCE PROFILE REPORT")
        print("="*80)
        
        total = sum(self.timings.values())
        
        for label, elapsed in sorted(self.timings.items(), key=lambda x: x[1], reverse=True):
            percentage = (elapsed / total * 100) if total > 0 else 0
            print(f"{label:.<50} {elapsed:>8.2f}s ({percentage:>5.1f}%)")
        
        print("-"*80)
        print(f"{'TOTAL':.<50} {total:>8.2f}s")
        print("="*80)


async def profile_generation():
    """Profile a small batch of conversation generation."""
    
    profiler = PerformanceProfiler()
    
    print("\n" + "="*80)
    print("CONVERSATION GENERATION PROFILER")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Generating 3 scam conversations for Malaysian locale...")
    print("="*80 + "\n")
    
    # 1. Configuration Loading
    profiler.start("1. Configuration Loading")
    try:
        config_loader = ConfigLoader(
            config_dir="./configs",
            output_dir="./output",
            use_timestamp=True
        )
        config = config_loader.load_localization("ms-my")
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return
    profiler.end("1. Configuration Loading")
    
    # 2. Generator Initialization
    profiler.start("2. Generator Initialization")
    try:
        # Override config for small test
        config.total_limit = 3
        config.scam_sample_limit = 3
        
        generator = ScamGenerator(config)
        print("✓ Generator initialized")
        print(f"  - LLM Provider: {generator.llm_provider}")
        print(f"  - LLM Model: {generator.llm_model}")
        print(f"  - Max Concurrent: {getattr(config, 'max_concurrent_requests', 10)}")
        print(f"  - Post-processor: {'Enabled' if generator.postprocessor else 'Disabled'}")
        print(f"  - Character Manager: {'Enabled' if generator.character_manager else 'Disabled'}")
    except Exception as e:
        print(f"✗ Generator initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    profiler.end("2. Generator Initialization")
    
    # 3. Conversation Generation (This is where we expect the bottleneck)
    print("\n" + "-"*80)
    print("Starting conversation generation...")
    print("-"*80)
    
    profiler.start("3. TOTAL Conversation Generation")
    
    # Detailed timing of first conversation
    print("\nDetailed timing for FIRST conversation:")
    start_first = time.time()
    
    try:
        # Monkey-patch to track LLM call timing
        original_generate_single = generator._generate_single_conversation
        llm_call_times = []
        
        async def timed_generate_single(conv_id, seed, scenario):
            llm_start = time.time()
            result = await original_generate_single(conv_id, seed, scenario)
            llm_elapsed = time.time() - llm_start
            llm_call_times.append((conv_id, llm_elapsed))
            print(f"  └─ Conversation {conv_id}: {llm_elapsed:.2f}s")
            return result
        
        generator._generate_single_conversation = timed_generate_single
        
        conversations = await generator.generate_conversations()
        
        elapsed_first = time.time() - start_first
        print(f"\nFirst conversation: {llm_call_times[0][1]:.2f}s" if llm_call_times else "No timing data")
        
        print(f"\n✓ Generated {len(conversations)} conversations")
        print(f"  Average time per conversation: {elapsed_first/len(conversations) if conversations else 0:.2f}s")
        
        # Show LLM call breakdown
        if llm_call_times:
            print("\nPer-conversation LLM timings:")
            for conv_id, elapsed in llm_call_times:
                print(f"  Conversation {conv_id}: {elapsed:.2f}s")
        
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    profiler.end("3. TOTAL Conversation Generation")
    
    # Print summary
    profiler.print_report()
    
    # Additional diagnostics
    print("\n" + "="*80)
    print("DIAGNOSTIC INFORMATION")
    print("="*80)
    
    # Check for reasoning model
    if "o1" in generator.llm_model or "o3" in generator.llm_model:
        print("⚠️  WARNING: Using reasoning model (o1/o3)")
        print("   Reasoning models are 10-20x slower than standard models")
        print("   Recommendation: Use gpt-4o or gpt-4o-mini for faster generation")
    
    # Check model configuration
    print(f"\nModel Configuration:")
    print(f"  Provider: {generator.llm_provider}")
    print(f"  Model: {generator.llm_model}")
    if hasattr(config, 'llm_reasoning_effort'):
        print(f"  Reasoning Effort: {config.llm_reasoning_effort}")
    if hasattr(config, 'llm_temperature'):
        print(f"  Temperature: {config.llm_temperature}")
    
    # Check prompt caching
    print(f"\nPrompt Optimization:")
    print(f"  Locale static prompt: {len(generator.locale_static_prompt)} chars")
    print(f"  (Longer prompts = more tokens = slower generation)")
    
    print("\n" + "="*80)


def run_cprofile():
    """Run with Python's cProfile for detailed function-level profiling."""
    
    print("\n" + "="*80)
    print("DETAILED FUNCTION-LEVEL PROFILING (cProfile)")
    print("="*80)
    print("This will show which specific functions consume the most time...")
    print("="*80 + "\n")
    
    # Create profiler
    pr = cProfile.Profile()
    pr.enable()
    
    # Run the async function
    asyncio.run(profile_generation())
    
    pr.disable()
    
    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.strip_dirs()
    ps.sort_stats('cumulative')
    
    print("\n" + "="*80)
    print("TOP 30 SLOWEST FUNCTIONS (by cumulative time)")
    print("="*80)
    ps.print_stats(30)
    print(s.getvalue())
    
    # Also sort by total time
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.strip_dirs()
    ps.sort_stats('tottime')
    
    print("\n" + "="*80)
    print("TOP 30 FUNCTIONS BY TOTAL TIME (excluding subcalls)")
    print("="*80)
    ps.print_stats(30)
    print(s.getvalue())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Profile conversation generation performance")
    parser.add_argument('--detailed', action='store_true', 
                       help='Run detailed cProfile analysis (slower but more thorough)')
    
    args = parser.parse_args()
    
    if args.detailed:
        run_cprofile()
    else:
        asyncio.run(profile_generation())
    
    print("\n" + "="*80)
    print("PROFILING COMPLETE")
    print("="*80)
    print("\nIf you see the bottleneck is in conversation generation:")
    print("  - Check if you're using a reasoning model (o1/o3) - these are very slow")
    print("  - Check model configuration in configs/common.json")
    print("  - Run with --detailed flag for function-level analysis")
    print("\nTo save output to file:")
    print("  python profile_generation.py > profile_output.txt 2>&1")
    print("="*80 + "\n")

