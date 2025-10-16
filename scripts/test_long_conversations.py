#!/usr/bin/env python3
"""
Test script for long conversation generation with SMS link behavior.
"""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Ensure project root and src are on sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.config.config_loader import Config
from src.conversation.scam_generator import ScamGenerator
from src.conversation.sms_link_manager import SMSLinkManager
from src.conversation.context_manager import ConversationContextManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LongConversationTester:
    """
    Test suite for long conversation generation with SMS link behavior.
    """
    
    def __init__(self, config_dir: str = "configs", output_dir: str = "output"):
        """
        Initialize the tester.
        
        Args:
            config_dir: Path to configuration directory
            output_dir: Path to output directory
        """
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "total_conversations": 0,
            "successful_conversations": 0,
            "failed_conversations": 0,
            "turn_count_stats": {},
            "sms_injection_stats": {},
            "quality_metrics": {},
            "errors": []
        }
    
    async def run_tests(self, locale: str = "ar-sa", num_conversations: int = 20):
        """
        Run comprehensive tests for long conversation generation.
        
        Args:
            locale: Target locale for testing
            num_conversations: Number of conversations to generate
        """
        logger.info(f"Starting long conversation tests for locale: {locale}")
        logger.info(f"Target: {num_conversations} conversations")
        
        try:
            # Load configuration
            config = Config(locale, self.config_dir)
            logger.info(f"Loaded configuration for {locale}")
            
            # Initialize generator
            generator = ScamGenerator(config)
            logger.info("Initialized scam generator")
            
            # Test conversation generation
            await self._test_conversation_generation(generator, num_conversations)
            
            # Test SMS link behavior
            await self._test_sms_link_behavior(generator, num_conversations)
            
            # Test conversation quality
            await self._test_conversation_quality()
            
            # Generate test report
            self._generate_test_report()
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            self.test_results["errors"].append(f"Test execution failed: {str(e)}")
    
    async def _test_conversation_generation(self, generator: ScamGenerator, num_conversations: int):
        """Test conversation generation with new turn limits."""
        logger.info("Testing conversation generation...")
        
        try:
            # Generate conversations
            conversations = await generator.generate_conversations()
            
            self.test_results["total_conversations"] = len(conversations)
            self.test_results["successful_conversations"] = len([c for c in conversations if c is not None])
            self.test_results["failed_conversations"] = len([c for c in conversations if c is None])
            
            # Analyze turn counts
            turn_counts = []
            for conv in conversations:
                if conv and "num_turns" in conv:
                    turn_counts.append(conv["num_turns"])
            
            if turn_counts:
                self.test_results["turn_count_stats"] = {
                    "min": min(turn_counts),
                    "max": max(turn_counts),
                    "average": sum(turn_counts) / len(turn_counts),
                    "target_range": "25-40",
                    "in_range": len([t for t in turn_counts if 25 <= t <= 40])
                }
                
                logger.info(f"Turn count analysis:")
                logger.info(f"  Min: {min(turn_counts)}")
                logger.info(f"  Max: {max(turn_counts)}")
                logger.info(f"  Average: {sum(turn_counts) / len(turn_counts):.1f}")
                logger.info(f"  In target range (25-40): {len([t for t in turn_counts if 25 <= t <= 40])}/{len(turn_counts)}")
            
        except Exception as e:
            logger.error(f"Conversation generation test failed: {e}")
            self.test_results["errors"].append(f"Conversation generation failed: {str(e)}")
    
    async def _test_sms_link_behavior(self, generator: ScamGenerator, num_conversations: int):
        """Test SMS link injection behavior."""
        logger.info("Testing SMS link behavior...")
        
        try:
            # Initialize SMS link manager
            sms_manager = SMSLinkManager(self.config_dir)
            
            # Test SMS link injection logic
            test_scenarios = [
                {"scam_category": "account_security", "conversation_seed": "SMS verification required"},
                {"scam_category": "tech_support", "conversation_seed": "Click the link to verify"},
                {"scam_category": "prize_scams", "conversation_seed": "No SMS mentioned"}
            ]
            
            injection_results = []
            for scenario in test_scenarios:
                should_inject = sms_manager.should_inject_sms_link(scenario, 0.45)
                injection_results.append(should_inject)
                logger.info(f"Scenario '{scenario['scam_category']}': SMS injection = {should_inject}")
            
            # Test link type selection
            available_types = sms_manager.get_available_link_types("ar-sa")
            if not available_types:
                # Create default templates for testing
                default_templates = sms_manager.create_default_templates("ar-sa")
                logger.info(f"Created {len(default_templates)} default SMS templates")
            
            self.test_results["sms_injection_stats"] = {
                "test_scenarios": len(test_scenarios),
                "injection_rate": sum(injection_results) / len(injection_results),
                "target_rate": 0.45,
                "available_link_types": len(available_types) if available_types else len(default_templates)
            }
            
            logger.info(f"SMS injection rate: {sum(injection_results) / len(injection_results):.2f}")
            
        except Exception as e:
            logger.error(f"SMS link behavior test failed: {e}")
            self.test_results["errors"].append(f"SMS link behavior test failed: {str(e)}")
    
    async def _test_conversation_quality(self):
        """Test conversation quality and coherence."""
        logger.info("Testing conversation quality...")
        
        try:
            # Initialize context manager
            context_manager = ConversationContextManager()
            
            # Test with sample conversation
            sample_conversation = [
                {"text": "Hello, this is John from the bank.", "role": "caller"},
                {"text": "Hi, how can I help you?", "role": "callee"},
                {"text": "We need to verify your account immediately.", "role": "caller"},
                {"text": "What do you need from me?", "role": "callee"}
            ]
            
            # Test context summarization
            context_summary = context_manager.summarize_stage_context(sample_conversation, "opening")
            logger.info(f"Context summary: {context_summary}")
            
            # Test coherence validation
            is_coherent, issues = context_manager.validate_conversation_coherence(sample_conversation)
            logger.info(f"Conversation coherence: {is_coherent}")
            if issues:
                logger.info(f"Coherence issues: {', '.join(issues)}")
            
            # Test conversation summary
            full_summary = context_manager.get_conversation_summary(sample_conversation)
            logger.info(f"Full conversation summary: {full_summary}")
            
            self.test_results["quality_metrics"] = {
                "context_summarization": bool(context_summary),
                "coherence_validation": is_coherent,
                "coherence_issues": len(issues),
                "summary_generation": bool(full_summary)
            }
            
        except Exception as e:
            logger.error(f"Conversation quality test failed: {e}")
            self.test_results["errors"].append(f"Conversation quality test failed: {str(e)}")
    
    def _generate_test_report(self):
        """Generate comprehensive test report."""
        logger.info("Generating test report...")
        
        # Calculate success rates
        total = self.test_results["total_conversations"]
        successful = self.test_results["successful_conversations"]
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # Check if turn counts are in target range
        turn_stats = self.test_results.get("turn_count_stats", {})
        in_range = turn_stats.get("in_range", 0)
        turn_success_rate = (in_range / total * 100) if total > 0 else 0
        
        # Check SMS injection rate
        sms_stats = self.test_results.get("sms_injection_stats", {})
        injection_rate = sms_stats.get("injection_rate", 0)
        target_rate = sms_stats.get("target_rate", 0.45)
        sms_success = abs(injection_rate - target_rate) < 0.1  # Within 10% of target
        
        # Generate report
        report = {
            "test_summary": {
                "timestamp": self.test_results["timestamp"],
                "total_conversations": total,
                "success_rate": f"{success_rate:.1f}%",
                "turn_count_success_rate": f"{turn_success_rate:.1f}%",
                "sms_injection_success": sms_success,
                "errors": len(self.test_results["errors"])
            },
            "detailed_results": self.test_results
        }
        
        # Save report
        report_path = self.output_dir / f"long_conversation_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("LONG CONVERSATION TEST RESULTS")
        print("="*60)
        print(f"Total conversations: {total}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Turn count success rate: {turn_success_rate:.1f}%")
        print(f"SMS injection success: {sms_success}")
        print(f"Errors: {len(self.test_results['errors'])}")
        
        if turn_stats:
            print(f"\nTurn Count Statistics:")
            print(f"  Min: {turn_stats.get('min', 'N/A')}")
            print(f"  Max: {turn_stats.get('max', 'N/A')}")
            print(f"  Average: {turn_stats.get('average', 0):.1f}")
            print(f"  In range (25-40): {in_range}/{total}")
        
        if sms_stats:
            print(f"\nSMS Link Statistics:")
            print(f"  Injection rate: {injection_rate:.2f}")
            print(f"  Target rate: {target_rate:.2f}")
            print(f"  Available link types: {sms_stats.get('available_link_types', 0)}")
        
        if self.test_results["errors"]:
            print(f"\nErrors:")
            for error in self.test_results["errors"][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        print(f"\nDetailed report saved to: {report_path}")
        print("="*60)
        
        return report


async def main():
    """Main test execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test long conversation generation")
    parser.add_argument("--locale", default="ar-sa", help="Target locale for testing")
    parser.add_argument("--num-conversations", type=int, default=20, help="Number of conversations to generate")
    parser.add_argument("--config-dir", default="configs", help="Configuration directory")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    
    args = parser.parse_args()
    
    # Create tester
    tester = LongConversationTester(args.config_dir, args.output_dir)
    
    # Run tests
    await tester.run_tests(args.locale, args.num_conversations)


if __name__ == "__main__":
    asyncio.run(main())
