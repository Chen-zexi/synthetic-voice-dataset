#!/usr/bin/env python3
"""
Test script for validating the new character profiles and scenario-based generation features.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add src to Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from config.config_loader import ConfigLoader
from conversation.seed_manager import SeedManager
from conversation.character_manager import CharacterManager
from conversation.placeholder_processor import DynamicPlaceholderProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_seed_manager():
    """Test the SeedManager functionality."""
    print("\n" + "="*50)
    print("TESTING SEED MANAGER")
    print("="*50)
    
    seeds_file = Path("scam_samples.json")
    if not seeds_file.exists():
        print("❌ scam_samples.json not found - skipping seed manager test")
        return False
    
    try:
        seed_manager = SeedManager(seeds_file)
        stats = seed_manager.get_stats()
        
        print(f"✅ Loaded {stats['total_seeds']} seeds across {stats['categories']} categories")
        print(f"Quality score range: {stats['quality_stats']['min']}-{stats['quality_stats']['max']}")
        print(f"Average quality: {stats['quality_stats']['avg']:.1f}")
        
        # Test high quality seeds
        high_quality = seed_manager.get_high_quality_seeds(80)
        print(f"High quality seeds (80+): {len(high_quality)}")
        
        # Test specific seed retrieval
        all_seeds = seed_manager.get_all_seeds()
        if all_seeds:
            sample_seed = all_seeds[0]
            print(f"Sample seed: {sample_seed.scam_tag} - {sample_seed.scam_summary[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Seed manager test failed: {e}")
        return False


def test_character_manager():
    """Test the CharacterManager functionality."""
    print("\n" + "="*50)
    print("TESTING CHARACTER MANAGER")
    print("="*50)
    
    try:
        # Test with default profiles
        char_manager = CharacterManager()
        stats = char_manager.get_stats()
        
        print(f"✅ Loaded {stats['total_profiles']} character profiles")
        print(f"Role distribution: {stats['role_distribution']}")
        print(f"Gender distribution: {stats['gender_distribution']}")
        
        # Test profile selection
        scammer = char_manager.select_random_profile("scammer", "ar-sa")
        victim = char_manager.select_random_profile("victim", "ar-sa")
        
        if scammer and victim:
            print(f"Sample scammer: {scammer.name} ({scammer.profile_id})")
            print(f"Sample victim: {victim.name} ({victim.profile_id})")
            
            # Test scenario creation
            scenario = char_manager.create_scenario("account_security", "ar-sa")
            if scenario:
                print(f"✅ Created scenario: {scenario.scenario_id}")
            else:
                print("❌ Failed to create scenario")
                return False
        else:
            print("❌ Failed to select character profiles")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Character manager test failed: {e}")
        return False


def test_placeholder_processor():
    """Test the DynamicPlaceholderProcessor functionality."""
    print("\n" + "="*50)
    print("TESTING DYNAMIC PLACEHOLDER PROCESSOR")
    print("="*50)
    
    # Test with Arabic placeholders
    placeholders_file = Path("configs/localizations/ar-sa/placeholders.json")
    if not placeholders_file.exists():
        print("❌ Arabic placeholders file not found - skipping test")
        return False
    
    try:
        processor = DynamicPlaceholderProcessor(placeholders_file)
        stats = processor.get_statistics()
        
        print(f"✅ Loaded {stats['total_placeholders']} placeholders")
        print(f"Dynamic: {stats['dynamic_placeholders']}, Static: {stats['static_placeholders']}")
        
        # Test text processing
        test_text = "مرحباً {00001}، نحن من {00002} وحاجة إلى تحديث معلوماتك"
        
        # Process multiple times to test randomization
        for i in range(3):
            processed = processor.process_text(test_text, f"test_conversation_{i}")
            print(f"Test {i+1}: {processed}")
            processor.reset_selections(f"test_conversation_{i}")
        
        # Test consistency within conversation
        conv_id = "consistency_test"
        processed1 = processor.process_text(test_text, conv_id)
        processed2 = processor.process_text(test_text, conv_id)
        
        if processed1 == processed2:
            print("✅ Placeholder consistency within conversation maintained")
        else:
            print("❌ Placeholder consistency test failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Placeholder processor test failed: {e}")
        return False


def test_config_integration():
    """Test the configuration integration."""
    print("\n" + "="*50)
    print("TESTING CONFIGURATION INTEGRATION")
    print("="*50)
    
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_localization("ar-sa")
        
        print(f"✅ Loaded configuration for locale: {config.locale}")
        print(f"Generation mode: {config.generation_source_type}")
        print(f"Character profiles enabled: {config.generation_enable_character_profiles}")
        print(f"Dynamic placeholders enabled: {config.generation_enable_dynamic_placeholders}")
        print(f"Scenarios per seed: {config.generation_scenarios_per_seed}")
        print(f"Minimum seed quality: {config.generation_min_seed_quality}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        return False


def test_full_integration():
    """Test full integration of all components."""
    print("\n" + "="*50)
    print("TESTING FULL INTEGRATION")
    print("="*50)
    
    try:
        # Load config
        config_loader = ConfigLoader()
        config = config_loader.load_localization("ar-sa")
        
        # Initialize managers
        seeds_file = Path("scam_samples.json")
        if not seeds_file.exists():
            print("❌ Cannot test integration without scam_samples.json")
            return False
            
        seed_manager = SeedManager(seeds_file)
        char_manager = CharacterManager()
        
        # Create scenarios
        high_quality_seeds = seed_manager.get_high_quality_seeds(80)
        selected_seeds = [seed.scam_tag for seed in high_quality_seeds[:5]]
        
        scenarios = char_manager.create_multiple_scenarios(
            seed_tags=selected_seeds,
            locale="ar-sa",
            scenarios_per_seed=2
        )
        
        print(f"✅ Created {len(scenarios)} scenarios from {len(selected_seeds)} seeds")
        
        # Display sample scenario
        if scenarios:
            sample = scenarios[0]
            seed = seed_manager.get_seed(sample.seed_tag)
            print(f"\nSample scenario:")
            print(f"  Seed: {sample.seed_tag}")
            print(f"  Scammer: {sample.scammer_profile.name}")
            print(f"  Victim: {sample.victim_profile.name}")
            print(f"  Conversation seed: {seed.conversation_seed[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Full integration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("SYNTHETIC VOICE DATASET - NEW FEATURES TEST")
    print("="*60)
    
    tests = [
        ("Seed Manager", test_seed_manager),
        ("Character Manager", test_character_manager),
        ("Placeholder Processor", test_placeholder_processor),
        ("Configuration Integration", test_config_integration),
        ("Full Integration", test_full_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! New features are ready to use.")
        print("\nTo use the new features:")
        print("1. Ensure common.json has 'source_type': 'seeds'")
        print("2. Run: uv run main.py --locale ar-sa --sample-limit 3")
        print("3. Check the generated conversations for character profiles and enhanced metadata")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
