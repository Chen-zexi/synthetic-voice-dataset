#!/usr/bin/env python3
"""
Stage 2: Process GPT-5 Comparison Outputs

This script processes previously generated conversations through TTS and postprocessing.
It reads the manifest created by compare_gpt5_models.py and processes each configuration.

Usage:
  python process_gpt5_outputs.py --manifest gpt5_comparison_*/manifest.json
  python process_gpt5_outputs.py --manifest path/to/manifest.json --configs "gpt-5_minimal,gpt-5_low"
"""

import argparse
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import time


class OutputProcessor:
    """Handles Stage 2 processing of generated conversations."""
    
    def __init__(self, manifest_path: Path, steps: List[str], verbose: bool = False):
        """
        Initialize the processor.
        
        Args:
            manifest_path: Path to manifest.json from Stage 1
            steps: Processing steps to run (tts, postprocess)
            verbose: Enable verbose output
        """
        self.manifest_path = manifest_path
        self.steps = steps
        self.verbose = verbose
        self.manifest = self.load_manifest()
        self.results = []
        
    def load_manifest(self) -> Dict:
        """
        Load the manifest file from Stage 1.
        
        Returns:
            Manifest dictionary
        """
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"Loaded manifest with {len(manifest.get('configurations', []))} configurations")
        print(f"Locale: {manifest.get('locale')}")
        print(f"Generation Date: {manifest.get('generation_date')}")
        
        return manifest
    
    def process_configuration(self, config: Dict) -> Dict:
        """
        Process a single configuration through TTS and postprocessing.
        
        Args:
            config: Configuration dictionary from manifest
            
        Returns:
            Processing result
        """
        config_id = config["config_id"]
        timestamp = config["timestamp"]
        locale = self.manifest["locale"]
        
        print(f"\n{'='*80}")
        print(f"Processing: {config_id}")
        print(f"  Model: {config['model']}")
        print(f"  Reasoning Effort: {config['reasoning_effort']}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Steps: {', '.join(self.steps)}")
        print(f"{'='*80}")
        
        # Build command
        cmd = [
            "python", "main.py",
            "--locale", locale,
            "--use-timestamp", timestamp,  # Use existing timestamp
            "--steps"
        ] + self.steps
        
        if self.verbose:
            cmd.append("--verbose")
        
        start_time = time.time()
        
        try:
            # Run the processing
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = time.time() - start_time
            
            # Check for successful completion
            success = "Pipeline completed successfully" in result.stdout or result.returncode == 0
            
            return {
                "success": success,
                "config_id": config_id,
                "model": config["model"],
                "reasoning_effort": config["reasoning_effort"],
                "timestamp": timestamp,
                "duration": duration,
                "steps_processed": self.steps,
                "output": result.stdout if self.verbose else None
            }
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "config_id": config_id,
                "model": config["model"],
                "reasoning_effort": config["reasoning_effort"],
                "timestamp": timestamp,
                "duration": duration,
                "error": str(e),
                "stderr": e.stderr if e.stderr else ""
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "config_id": config_id,
                "model": config["model"],
                "reasoning_effort": config["reasoning_effort"],
                "timestamp": timestamp,
                "duration": duration,
                "error": str(e)
            }
    
    def process_all(self, config_filter: Set[str] = None):
        """
        Process all configurations or filtered subset.
        
        Args:
            config_filter: Set of config_ids to process (None for all)
        """
        configurations = self.manifest.get("configurations", [])
        
        # Filter configurations if specified
        if config_filter:
            configurations = [c for c in configurations if c["config_id"] in config_filter]
            print(f"\nProcessing {len(configurations)} filtered configurations")
        else:
            print(f"\nProcessing all {len(configurations)} configurations")
        
        if not configurations:
            print("No configurations to process!")
            return
        
        # Process each configuration
        for i, config in enumerate(configurations, 1):
            print(f"\n[{i}/{len(configurations)}] Processing {config['config_id']}...")
            
            result = self.process_configuration(config)
            self.results.append(result)
            
            if result["success"]:
                print(f"✓ Completed in {result['duration']:.2f}s")
            else:
                print(f"✗ Failed: {result.get('error', 'Unknown error')}")
    
    def verify_outputs(self) -> Dict:
        """
        Verify that expected output files exist after processing.
        
        Returns:
            Verification results
        """
        verification = {
            "configurations": [],
            "all_verified": True
        }
        
        locale = self.manifest["locale"]
        
        for config in self.manifest.get("configurations", []):
            timestamp = config["timestamp"]
            config_id = config["config_id"]
            base_path = Path(f"output/{locale}/{timestamp}")
            
            files_to_check = {}
            
            # Check for TTS outputs if processed
            if "tts" in self.steps:
                files_to_check["audio_dir"] = base_path / "audio" / "scam"
                files_to_check["has_audio"] = len(list(files_to_check["audio_dir"].glob("*.mp3"))) > 0 if files_to_check["audio_dir"].exists() else False
            
            # Check for postprocessing outputs if processed
            if "postprocess" in self.steps:
                files_to_check["final_json"] = base_path / "final" / "scam_dataset.json"
                files_to_check["audio_zip"] = base_path / "audio" / "scam" / "scam_audio.zip"
            
            config_verification = {
                "config_id": config_id,
                "timestamp": timestamp,
                "verified": True
            }
            
            # Check each expected file
            for key, path in files_to_check.items():
                if isinstance(path, Path):
                    exists = path.exists()
                    config_verification[key] = exists
                    if not exists:
                        config_verification["verified"] = False
                        verification["all_verified"] = False
                elif key == "has_audio":
                    config_verification[key] = path
                    if not path:
                        config_verification["verified"] = False
                        verification["all_verified"] = False
            
            verification["configurations"].append(config_verification)
        
        return verification
    
    def print_summary(self):
        """Print processing summary."""
        print("\n" + "="*80)
        print("PROCESSING SUMMARY")
        print("="*80)
        
        successful = sum(1 for r in self.results if r.get("success"))
        failed = sum(1 for r in self.results if not r.get("success"))
        
        print(f"\nResults:")
        print(f"  Total Processed: {len(self.results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        
        if self.results:
            print(f"\n{'Config ID':<25} {'Status':<10} {'Duration':<10}")
            print("-"*80)
            
            for result in self.results:
                config_id = result["config_id"]
                status = "✓ Success" if result.get("success") else "✗ Failed"
                duration = f"{result['duration']:.2f}s"
                print(f"{config_id:<25} {status:<10} {duration:<10}")
        
        # Verify outputs
        print("\n" + "-"*80)
        print("Output Verification:")
        print("-"*80)
        
        verification = self.verify_outputs()
        
        for config in verification["configurations"]:
            config_id = config["config_id"]
            status = "✓ All files present" if config["verified"] else "✗ Missing files"
            print(f"{config_id:<25} {status}")
            
            if not config["verified"]:
                # Show what's missing
                for key, value in config.items():
                    if key not in ["config_id", "timestamp", "verified"] and value is False:
                        print(f"  - Missing: {key}")
        
        if verification["all_verified"]:
            print("\n✓ All expected outputs verified successfully!")
        else:
            print("\n⚠ Some outputs are missing. Check the details above.")
    
    def save_processing_report(self):
        """Save processing report."""
        report = {
            "processing_date": datetime.now().isoformat(),
            "manifest_path": str(self.manifest_path),
            "steps_processed": self.steps,
            "results": self.results,
            "verification": self.verify_outputs()
        }
        
        report_path = self.manifest_path.parent / "processing_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nProcessing report saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Process GPT-5 comparison outputs through TTS and postprocessing (Stage 2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This is Stage 2 of the comparison process. It processes conversations
generated by compare_gpt5_models.py through TTS and postprocessing.

Examples:
  # Process all configurations
  %(prog)s --manifest gpt5_comparison_20240101_120000/manifest.json
  
  # Process with specific steps
  %(prog)s --manifest path/to/manifest.json --steps tts
  %(prog)s --manifest path/to/manifest.json --steps postprocess
  %(prog)s --manifest path/to/manifest.json --steps tts postprocess
  
  # Process specific configurations only
  %(prog)s --manifest path/to/manifest.json --configs "gpt-5_minimal,gpt-5_low"
  
  # Verbose mode for debugging
  %(prog)s --manifest path/to/manifest.json --verbose
        """
    )
    
    parser.add_argument(
        '--manifest',
        type=str,
        required=True,
        help='Path to manifest.json from Stage 1 (compare_gpt5_models.py)'
    )
    
    parser.add_argument(
        '--steps',
        type=str,
        nargs='+',
        default=['tts', 'postprocess'],
        choices=['tts', 'postprocess'],
        help='Processing steps to run (default: tts postprocess)'
    )
    
    parser.add_argument(
        '--configs',
        type=str,
        help='Comma-separated list of config_ids to process (e.g., "gpt-5_minimal,gpt-5_low")'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse manifest path
    manifest_path = Path(args.manifest)
    if manifest_path.name != "manifest.json":
        # User might have provided directory instead of file
        if manifest_path.is_dir():
            manifest_path = manifest_path / "manifest.json"
    
    # Parse config filter if provided
    config_filter = None
    if args.configs:
        config_filter = set(c.strip() for c in args.configs.split(','))
        print(f"Filtering to configurations: {', '.join(config_filter)}")
    
    print(f"\n{'='*80}")
    print("STAGE 2: PROCESSING GPT-5 COMPARISON OUTPUTS")
    print(f"{'='*80}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Manifest: {manifest_path}")
    print(f"Steps: {', '.join(args.steps)}")
    
    try:
        # Initialize processor
        processor = OutputProcessor(
            manifest_path=manifest_path,
            steps=args.steps,
            verbose=args.verbose
        )
        
        # Process configurations
        processor.process_all(config_filter)
        
        # Print summary
        processor.print_summary()
        
        # Save report
        processor.save_processing_report()
        
        print(f"\n{'='*80}")
        print("PROCESSING COMPLETE")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Make sure you run compare_gpt5_models.py first to generate the manifest.")
        return 1
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nError during processing: {e}")
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