"""
SMS link behavior manager for injecting SMS link tactics into scam conversations.
"""

import json
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SMSLinkTemplate(BaseModel):
    """Template for SMS link behavior in a specific locale."""
    link_type: str
    scammer_phrases: List[str]
    victim_responses: List[str]
    link_descriptions: List[str]
    urgency_phrases: List[str]


class SMSLinkManager:
    """
    Manages SMS link behavior injection into scam conversations.
    """
    
    def __init__(self, config_dir: Path = Path("configs")):
        """
        Initialize the SMS link manager.
        
        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = config_dir
        self.templates: Dict[str, Dict[str, SMSLinkTemplate]] = {}  # locale -> link_type -> template
        self._load_templates()
    
    def _load_templates(self):
        """Load SMS link templates for all locales."""
        localizations_dir = self.config_dir / "localizations"
        
        if not localizations_dir.exists():
            logger.debug(f"Localizations directory not found: {localizations_dir}")
            return
        
        for locale_dir in localizations_dir.iterdir():
            if not locale_dir.is_dir():
                continue
            
            locale_id = locale_dir.name
            templates_file = locale_dir / "sms_link_templates.json"
            
            if templates_file.exists():
                try:
                    with open(templates_file, 'r', encoding='utf-8') as f:
                        templates_data = json.load(f)
                    
                    self.templates[locale_id] = {}
                    for link_type, template_data in templates_data.items():
                        self.templates[locale_id][link_type] = SMSLinkTemplate(
                            link_type=link_type,
                            **template_data
                        )
                    
                    logger.debug(f"Loaded SMS link templates for {locale_id}")
                except Exception as e:
                    logger.error(f"Failed to load SMS templates for {locale_id}: {e}")
            else:
                logger.debug(f"No SMS templates found for {locale_id}")
    
    def should_inject_sms_link(self, scenario: Dict, probability: float = 0.45) -> bool:
        """
        Determine if SMS link behavior should be injected into a conversation.
        
        Args:
            scenario: The conversation scenario
            probability: Probability of injection (0.0 to 1.0)
            
        Returns:
            True if SMS link should be injected
        """
        # Check if scenario is suitable for SMS links
        if not self._is_scenario_suitable(scenario):
            return False
        
        # Apply probability check
        return random.random() < probability
    
    def _is_scenario_suitable(self, scenario: Dict) -> bool:
        """
        Check if a scenario is suitable for SMS link injection.
        
        Args:
            scenario: The conversation scenario
            
        Returns:
            True if scenario is suitable for SMS links
        """
        # Scenarios that are good for SMS links
        suitable_categories = [
            "account_security", "tech_support", "prize_scams", 
            "delivery_scams", "phishing", "verification"
        ]
        
        # Check if scenario mentions SMS, links, or verification
        scenario_text = scenario.get("conversation_seed", "").lower()
        sms_indicators = ["sms", "text", "link", "click", "verify", "message", "sent"]
        
        has_sms_indicators = any(indicator in scenario_text for indicator in sms_indicators)
        
        # Check category
        category = scenario.get("scam_category", "").lower()
        suitable_category = any(cat in category for cat in suitable_categories)
        
        return has_sms_indicators or suitable_category
    
    def get_sms_link_template(self, link_type: str, locale: str) -> Optional[SMSLinkTemplate]:
        """
        Get SMS link template for a specific link type and locale.
        
        Args:
            link_type: Type of link (verification, payment, etc.)
            locale: Target locale
            
        Returns:
            SMS link template or None if not found
        """
        if locale not in self.templates:
            logger.debug(f"No SMS templates found for locale: {locale}")
            return None
        
        if link_type not in self.templates[locale]:
            logger.debug(f"No template found for link type {link_type} in locale {locale}")
            return None
        
        return self.templates[locale][link_type]
    
    def select_link_type(self, locale: str, available_types: List[str] = None) -> str:
        """
        Select a random link type for the given locale.
        
        Args:
            locale: Target locale
            available_types: List of available link types to choose from
            
        Returns:
            Selected link type
        """
        if available_types is None:
            available_types = ["verification", "payment", "security_check", "document_download", "prize_claim"]
        
        # Filter to only types available for this locale
        if locale in self.templates:
            available_for_locale = [t for t in available_types if t in self.templates[locale]]
            if available_for_locale:
                return random.choice(available_for_locale)
        
        # Fallback to random selection from available types
        return random.choice(available_types)
    
    def inject_sms_behavior(self, stage_prompt: str, link_type: str, locale: str, 
                           stage_name: str) -> str:
        """
        Inject SMS link behavior into a stage prompt.
        
        Args:
            stage_prompt: The original stage prompt
            link_type: Type of SMS link to inject
            locale: Target locale
            stage_name: Name of the conversation stage
            
        Returns:
            Modified prompt with SMS link behavior
        """
        template = self.get_sms_link_template(link_type, locale)
        if not template:
            logger.warning(f"No template found for {link_type} in {locale}, using fallback")
            return self._add_fallback_sms_behavior(stage_prompt, link_type)
        
        # Add SMS link instructions based on stage
        sms_instructions = self._generate_sms_instructions(template, stage_name)
        
        # Inject into the prompt
        enhanced_prompt = f"{stage_prompt}\n\n### SMS Link Behavior Instructions\n{sms_instructions}"
        
        return enhanced_prompt
    
    def _generate_sms_instructions(self, template: SMSLinkTemplate, stage_name: str) -> str:
        """
        Generate SMS link instructions for a specific stage.
        
        Args:
            template: SMS link template
            stage_name: Name of the conversation stage
            
        Returns:
            SMS link instructions
        """
        if stage_name == "creating_urgency":
            return f"""
**SMS Link Urgency Phase:**
- Use phrases like: {', '.join(template.urgency_phrases[:3])}
- Create time pressure around the SMS link
- Emphasize immediate action required
- Scammer should mention sending SMS: {random.choice(template.scammer_phrases)}
- Victim should respond: {random.choice(template.victim_responses)}
"""
        elif stage_name == "action_request":
            return f"""
**SMS Link Action Phase:**
- Scammer provides step-by-step SMS link instructions
- Use phrases like: {', '.join(template.scammer_phrases[:3])}
- Describe the link as: {random.choice(template.link_descriptions)}
- Guide victim through clicking the link
- Victim should show some hesitation but ultimately comply
"""
        else:
            return f"""
**SMS Link Integration:**
- Scammer mentions sending SMS: {random.choice(template.scammer_phrases)}
- Victim responds: {random.choice(template.victim_responses)}
- Link described as: {random.choice(template.link_descriptions)}
"""
    
    def _add_fallback_sms_behavior(self, stage_prompt: str, link_type: str) -> str:
        """
        Add fallback SMS behavior when no template is available.
        
        Args:
            stage_prompt: Original stage prompt
            link_type: Type of link
            
        Returns:
            Enhanced prompt with fallback SMS behavior
        """
        fallback_instructions = f"""
**SMS Link Behavior (Fallback):**
- Scammer should mention sending an SMS with a {link_type} link
- Create urgency around clicking the link
- Victim should acknowledge receiving the message
- Include step-by-step instructions for the victim
"""
        
        return f"{stage_prompt}\n\n{fallback_instructions}"
    
    def get_available_link_types(self, locale: str) -> List[str]:
        """
        Get available link types for a locale.
        
        Args:
            locale: Target locale
            
        Returns:
            List of available link types
        """
        if locale not in self.templates:
            return []
        
        return list(self.templates[locale].keys())
    
    def create_default_templates(self, locale: str) -> Dict[str, Dict]:
        """
        Create default SMS link templates for a locale.
        
        Args:
            locale: Target locale
            
        Returns:
            Dictionary of default templates
        """
        return {
            "verification": {
                "scammer_phrases": [
                    "I'll send you a verification link via SMS",
                    "Check the text message I just sent",
                    "Click the link in the SMS to verify your account"
                ],
                "victim_responses": [
                    "I received the message",
                    "What should I click?",
                    "I see the link"
                ],
                "link_descriptions": [
                    "secure verification portal",
                    "account confirmation page",
                    "identity verification system"
                ],
                "urgency_phrases": [
                    "This must be done immediately",
                    "Time is running out",
                    "Your account will be locked if you don't act now"
                ]
            },
            "payment": {
                "scammer_phrases": [
                    "I'll send you a secure payment link",
                    "Check your SMS for the payment portal",
                    "Click the link to complete your payment"
                ],
                "victim_responses": [
                    "I got the payment link",
                    "Should I enter my card details?",
                    "Is this secure?"
                ],
                "link_descriptions": [
                    "secure payment gateway",
                    "encrypted payment portal",
                    "bank-verified payment system"
                ],
                "urgency_phrases": [
                    "Payment must be completed within 10 minutes",
                    "Your account will be suspended without payment",
                    "This is your final opportunity"
                ]
            },
            "security_check": {
                "scammer_phrases": [
                    "I'm sending you a security verification link",
                    "Check the SMS for your security check",
                    "Click the link to verify your identity"
                ],
                "victim_responses": [
                    "I received the security link",
                    "What information do I need to provide?",
                    "Is this really necessary?"
                ],
                "link_descriptions": [
                    "security verification system",
                    "identity confirmation portal",
                    "account security check"
                ],
                "urgency_phrases": [
                    "Security breach detected - immediate action required",
                    "Your account is at risk",
                    "This security check cannot be delayed"
                ]
            }
        }
