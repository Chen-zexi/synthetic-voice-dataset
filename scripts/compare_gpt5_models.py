#!/usr/bin/env python3
"""
GPT-5 Family Model Comparison Script

This script systematically tests all GPT-5 family models (gpt-5, gpt-5-mini, gpt-5-nano)
with all reasoning effort levels (minimal, low, medium, high) using controlled seed-based generation.

Total configurations tested: 12 (3 models × 4 reasoning efforts)
"""

import argparse
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import time


class ModelComparator:
    """Handles model comparison for GPT-5 family."""
    
    GPT5_MODELS = ['gpt-5', 'gpt-5-mini', 'gpt-5-nano']
    REASONING_EFFORTS = ['minimal', 'low', 'medium', 'high']
    
    def __init__(self, locale: str, random_seed: int, seed_limit: int, verbose: bool = False):
        """
        Initialize the comparator.
        
        Args:
            locale: Locale to generate for
            random_seed: Fixed random seed for reproducibility
            seed_limit: Number of seeds to use (conversations to generate)
            verbose: Enable verbose output
        """
        self.locale = locale
        self.random_seed = random_seed
        self.seed_limit = seed_limit
        self.verbose = verbose
        self.results = []
        self.start_time = datetime.now()
        
    def run_generation(self, model: str, reasoning_effort: str) -> Dict:
        """
        Run generation with specific model and reasoning effort.
        
        Args:
            model: GPT-5 model variant
            reasoning_effort: Reasoning effort level
            
        Returns:
            Dictionary with generation results
        """
        # Build command using new generation control flags
        cmd = [
            "python", "main.py",
            "--locale", self.locale,
            "--model", model,
            "--reasoning-effort", reasoning_effort,
            "--random-seed", str(self.random_seed),
            "--generation-mode", "seeds",
            "--seed-limit", str(self.seed_limit),
            "--steps", "conversation"
        ]
        
        if self.verbose:
            cmd.append("--verbose")
        
        # Display progress
        config_name = f"{model} ({reasoning_effort})"
        print(f"\n{'='*80}")
        print(f"Testing: {config_name}")
        print(f"  Model: {model}")
        print(f"  Reasoning Effort: {reasoning_effort}")
        print(f"  Random Seed: {self.random_seed}")
        print(f"  Seed Limit: {self.seed_limit}")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = time.time() - start_time
            
            # Extract timestamp from output
            timestamp = None
            for line in result.stdout.split('\n'):
                if "Generation timestamp:" in line:
                    timestamp = line.split("Generation timestamp:")[1].strip()
                    break
            
            if not timestamp:
                # Try to find the latest timestamp if not in output
                locale_dir = Path(f"output/{self.locale}")
                if locale_dir.exists():
                    import re
                    timestamp_pattern = re.compile(r'^(\d{4}_\d{4})(?:_(\d+))?$')
                    timestamps = []
                    for d in locale_dir.iterdir():
                        if d.is_dir():
                            match = timestamp_pattern.match(d.name)
                            if match:
                                timestamps.append(d.name)
                    if timestamps:
                        timestamps.sort()
                        timestamp = timestamps[-1]
            
            # Load generated conversations
            if timestamp:
                output_file = Path(f"output/{self.locale}/{timestamp}/conversations/scam_conversations.json")
                if output_file.exists():
                    with open(output_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract relevant metrics
                    conversations = data.get("conversations", [])
                    metadata = data.get("generation_metadata", {})
                    generation_control = metadata.get("generation_control", {})
                    
                    return {
                        "success": True,
                        "model": model,
                        "reasoning_effort": reasoning_effort,
                        "timestamp": timestamp,
                        "duration": duration,
                        "conversations": conversations,
                        "num_conversations": len(conversations),
                        "seeds_used": generation_control.get("seeds_used", 0),
                        "conversations_generated": generation_control.get("conversations_generated", 0),
                        "metadata": metadata,
                        "token_usage": data.get("token_usage", {}),
                        "estimated_cost": data.get("estimated_cost", {})
                    }
            
            return {
                "success": False,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "error": "Could not find output file or timestamp",
                "duration": duration
            }
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "error": str(e),
                "stderr": e.stderr if e.stderr else "",
                "duration": duration
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "error": str(e),
                "duration": duration
            }
    
    def run_all_comparisons(self) -> List[Dict]:
        """
        Run all model and reasoning effort combinations.
        
        Returns:
            List of all results
        """
        total_configs = len(self.GPT5_MODELS) * len(self.REASONING_EFFORTS)
        print(f"\nStarting GPT-5 family comparison")
        print(f"Total configurations to test: {total_configs}")
        print(f"Models: {', '.join(self.GPT5_MODELS)}")
        print(f"Reasoning Efforts: {', '.join(self.REASONING_EFFORTS)}")
        print(f"Locale: {self.locale}")
        print(f"Seeds per configuration: {self.seed_limit}")
        
        config_num = 0
        for model in self.GPT5_MODELS:
            for reasoning_effort in self.REASONING_EFFORTS:
                config_num += 1
                print(f"\n[{config_num}/{total_configs}] Processing {model} with {reasoning_effort} effort...")
                
                result = self.run_generation(model, reasoning_effort)
                self.results.append(result)
                
                # Brief status update
                if result["success"]:
                    print(f"✓ Completed in {result['duration']:.2f}s")
                    print(f"  Generated: {result['num_conversations']} conversations")
                    if result.get("estimated_cost"):
                        cost = result["estimated_cost"].get("total_cost", 0)
                        print(f"  Cost: ${cost:.4f}")
                else:
                    print(f"✗ Failed: {result.get('error', 'Unknown error')}")
        
        return self.results
    
    def analyze_results(self) -> Dict:
        """
        Analyze and compare all results.
        
        Returns:
            Comprehensive analysis dictionary
        """
        analysis = {
            "summary": {
                "total_configurations": len(self.results),
                "successful": sum(1 for r in self.results if r.get("success")),
                "failed": sum(1 for r in self.results if not r.get("success")),
                "locale": self.locale,
                "random_seed": self.random_seed,
                "seed_limit": self.seed_limit,
                "test_duration": str(datetime.now() - self.start_time)
            },
            "configurations": [],
            "cost_analysis": {},
            "performance_analysis": {},
            "quality_metrics": {}
        }
        
        # Process each configuration
        for result in self.results:
            config_summary = {
                "model": result["model"],
                "reasoning_effort": result["reasoning_effort"],
                "success": result.get("success", False)
            }
            
            if result.get("success"):
                config_summary.update({
                    "timestamp": result["timestamp"],
                    "duration": f"{result['duration']:.2f}s",
                    "conversations_generated": result["num_conversations"],
                    "seeds_used": result.get("seeds_used", 0),
                    "total_tokens": result.get("token_usage", {}).get("total_tokens", 0),
                    "total_cost": result.get("estimated_cost", {}).get("total_cost", 0)
                })
                
                # Calculate quality metrics
                if result["conversations"]:
                    turns_list = [len(c.get("dialogue", [])) for c in result["conversations"]]
                    config_summary["quality_metrics"] = {
                        "avg_turns": sum(turns_list) / len(turns_list) if turns_list else 0,
                        "min_turns": min(turns_list) if turns_list else 0,
                        "max_turns": max(turns_list) if turns_list else 0,
                        "total_dialogue_items": sum(turns_list)
                    }
            else:
                config_summary["error"] = result.get("error", "Unknown error")
            
            analysis["configurations"].append(config_summary)
        
        # Cost analysis
        successful_configs = [c for c in analysis["configurations"] if c.get("success")]
        if successful_configs:
            costs_by_model = {}
            for config in successful_configs:
                model = config["model"]
                if model not in costs_by_model:
                    costs_by_model[model] = []
                costs_by_model[model].append({
                    "reasoning_effort": config["reasoning_effort"],
                    "cost": config.get("total_cost", 0)
                })
            
            analysis["cost_analysis"] = {
                "by_model": costs_by_model,
                "cheapest": min(successful_configs, key=lambda x: x.get("total_cost", float('inf'))),
                "most_expensive": max(successful_configs, key=lambda x: x.get("total_cost", 0))
            }
            
            # Performance analysis
            analysis["performance_analysis"] = {
                "fastest": min(successful_configs, key=lambda x: float(x["duration"].rstrip('s'))),
                "slowest": max(successful_configs, key=lambda x: float(x["duration"].rstrip('s')))
            }
        
        return analysis
    
    def print_report(self, analysis: Dict):
        """
        Print a formatted comparison report.
        
        Args:
            analysis: Analysis dictionary
        """
        print("\n" + "="*80)
        print("GPT-5 FAMILY COMPARISON REPORT")
        print("="*80)
        
        # Summary
        summary = analysis["summary"]
        print(f"\nTest Summary:")
        print(f"  Configurations Tested: {summary['total_configurations']}")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Test Duration: {summary['test_duration']}")
        
        # Detailed results table
        print("\n" + "-"*80)
        print("Detailed Results:")
        print("-"*80)
        print(f"{'Model':<15} {'Effort':<10} {'Status':<10} {'Time':<10} {'Convos':<10} {'Cost':<10}")
        print("-"*80)
        
        for config in analysis["configurations"]:
            model = config["model"]
            effort = config["reasoning_effort"]
            status = "✓ Success" if config.get("success") else "✗ Failed"
            duration = config.get("duration", "N/A")
            convos = str(config.get("conversations_generated", 0))
            cost = f"${config.get('total_cost', 0):.4f}" if config.get("success") else "N/A"
            
            print(f"{model:<15} {effort:<10} {status:<10} {duration:<10} {convos:<10} {cost:<10}")
        
        # Cost comparison
        if analysis.get("cost_analysis") and analysis["cost_analysis"].get("by_model"):
            print("\n" + "-"*80)
            print("Cost Analysis:")
            print("-"*80)
            
            for model, costs in analysis["cost_analysis"]["by_model"].items():
                print(f"\n{model}:")
                for cost_item in sorted(costs, key=lambda x: x["cost"]):
                    print(f"  {cost_item['reasoning_effort']:<10} ${cost_item['cost']:.4f}")
            
            if analysis["cost_analysis"].get("cheapest"):
                cheapest = analysis["cost_analysis"]["cheapest"]
                print(f"\nCheapest: {cheapest['model']} ({cheapest['reasoning_effort']}) - ${cheapest.get('total_cost', 0):.4f}")
            
            if analysis["cost_analysis"].get("most_expensive"):
                expensive = analysis["cost_analysis"]["most_expensive"]
                print(f"Most Expensive: {expensive['model']} ({expensive['reasoning_effort']}) - ${expensive.get('total_cost', 0):.4f}")
        
        # Quality metrics
        print("\n" + "-"*80)
        print("Quality Metrics:")
        print("-"*80)
        
        for config in analysis["configurations"]:
            if config.get("success") and config.get("quality_metrics"):
                metrics = config["quality_metrics"]
                print(f"\n{config['model']} ({config['reasoning_effort']}):")
                print(f"  Average Turns: {metrics['avg_turns']:.1f}")
                print(f"  Turn Range: {metrics['min_turns']}-{metrics['max_turns']}")
                print(f"  Total Dialogue Items: {metrics['total_dialogue_items']}")
    
    def save_report(self, analysis: Dict, output_dir: Path):
        """
        Save the analysis report and all conversations.
        
        Args:
            analysis: Analysis dictionary
            output_dir: Directory to save reports
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main analysis report
        report_file = output_dir / "comparison_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to: {report_file}")
        
        # Save all conversations for manual review
        conversations_dir = output_dir / "conversations"
        conversations_dir.mkdir(exist_ok=True)
        
        for result in self.results:
            if result.get("success") and result.get("conversations"):
                filename = f"{result['model']}_{result['reasoning_effort']}.json"
                conv_file = conversations_dir / filename
                
                conv_data = {
                    "model": result["model"],
                    "reasoning_effort": result["reasoning_effort"],
                    "timestamp": result["timestamp"],
                    "conversations": result["conversations"],
                    "metadata": result.get("metadata", {})
                }
                
                with open(conv_file, 'w', encoding='utf-8') as f:
                    json.dump(conv_data, f, indent=2, ensure_ascii=False)
        
        print(f"Conversations saved to: {conversations_dir}")
        
        # Save manifest for Stage 2 processing
        manifest = {
            "generation_date": datetime.now().isoformat(),
            "locale": self.locale,
            "random_seed": self.random_seed,
            "seed_limit": self.seed_limit,
            "configurations": []
        }
        
        for result in self.results:
            if result.get("success"):
                manifest["configurations"].append({
                    "model": result["model"],
                    "reasoning_effort": result["reasoning_effort"],
                    "timestamp": result["timestamp"],
                    "config_id": f"{result['model']}_{result['reasoning_effort']}",
                    "output_path": f"output/{self.locale}/{result['timestamp']}"
                })
        
        manifest_file = output_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"Manifest saved to: {manifest_file} (for Stage 2 processing)")


def main():
    parser = argparse.ArgumentParser(
        description='Compare GPT-5 family models with different reasoning efforts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script tests all GPT-5 family models (gpt-5, gpt-5-mini, gpt-5-nano)
with all reasoning effort levels (minimal, low, medium, high).

Total configurations: 12 (3 models × 4 efforts)

Example:
  %(prog)s --locale ms-my --seed 42 --seed-limit 5
  %(prog)s --locale ar-sa --seed 123 --seed-limit 10 --verbose
        """
    )
    
    parser.add_argument(
        '--locale',
        type=str,
        required=True,
        help='Locale to generate conversations for (e.g., ms-my, ar-sa)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Fixed random seed for reproducible generation (default: 42)'
    )
    
    parser.add_argument(
        '--seed-limit',
        type=int,
        default=5,
        help='Number of different seeds to use (conversations to generate) (default: 5)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for reports (default: gpt5_comparison_TIMESTAMP)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output during generation'
    )
    
    args = parser.parse_args()
    
    # Set up output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"gpt5_comparison_{timestamp}")
    
    print(f"\n{'='*80}")
    print("GPT-5 FAMILY MODEL COMPARISON")
    print(f"{'='*80}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output Directory: {output_dir}")
    
    # Initialize comparator
    comparator = ModelComparator(
        locale=args.locale,
        random_seed=args.seed,
        seed_limit=args.seed_limit,
        verbose=args.verbose
    )
    
    # Run all comparisons
    try:
        comparator.run_all_comparisons()
        
        # Analyze results
        analysis = comparator.analyze_results()
        
        # Print report
        comparator.print_report(analysis)
        
        # Save report and conversations
        comparator.save_report(analysis, output_dir)
        
        print(f"\n{'='*80}")
        print("COMPARISON COMPLETE")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"All results saved to: {output_dir}")
        print(f"{'='*80}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nComparison interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nError during comparison: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Change to project root directory
    script_path = Path(__file__)
    if script_path.parent.name == "scripts":
        os.chdir(script_path.parent.parent)
    elif script_path.parent.name == "voice_scam_dataset_gen":
        os.chdir(script_path.parent)
    
    sys.exit(main())