"""
Audio tags for ElevenLabs v3 TTS model to add emotional context and expressiveness.
"""

from typing import Dict, List, Optional
import random


class AudioTagManager:
    """
    Manages audio tags for ElevenLabs v3 model to enhance speech expressiveness.
    """
    
    # Emotional tags for different conversation contexts
    EMOTIONAL_TAGS = {
        "scam": {
            "opener": ["urgent", "concerned", "official", "serious"],
            "building_trust": ["friendly", "understanding", "reassuring", "professional"],
            "creating_urgency": ["worried", "urgent", "alarmed", "pressing"],
            "extracting_info": ["insistent", "persuasive", "authoritative"],
            "closing": ["urgent", "pressing", "final_chance"]
        },
        "legit": {
            "greeting": ["friendly", "warm", "polite", "cheerful"],
            "informing": ["clear", "informative", "helpful", "professional"],
            "requesting": ["polite", "courteous", "respectful"],
            "confirming": ["reassuring", "confident", "clear"],
            "closing": ["grateful", "polite", "warm"]
        }
    }
    
    # Voice modulation tags
    VOICE_MODULATION_TAGS = {
        "whispers": ["whispers"],
        "speaks_slowly": ["speaks slowly", "deliberately"],
        "speaks_quickly": ["speaks quickly", "hurriedly"],
        "emphasizes": ["emphasizes", "stresses"],
        "pauses": ["pauses", "hesitates"],
        "excited": ["excited", "enthusiastic"],
        "concerned": ["concerned", "worried"],
        "confident": ["confident", "assured"]
    }
    
    # Conversational tags for natural dialogue
    CONVERSATIONAL_TAGS = {
        "reactions": ["sighs", "chuckles", "laughs softly", "gasps", "hmm"],
        "thinking": ["pauses thoughtfully", "considers", "thinks"],
        "interrupting": ["interrupts", "cuts in", "breaks in"],
        "agreeing": ["agrees warmly", "nods", "affirms"],
        "disagreeing": ["objects politely", "disputes", "questions"]
    }
    
    def __init__(self):
        """Initialize the audio tag manager."""
        pass
    
    def get_contextual_tags(self, 
                          conversation_type: str,
                          turn_position: str,
                          role: str,
                          text_content: str) -> List[str]:
        """
        Get appropriate audio tags based on conversation context.
        
        Args:
            conversation_type: "scam" or "legit"
            turn_position: "opening", "middle", "closing"
            role: "caller" or "callee"
            text_content: The actual text being spoken
            
        Returns:
            List of appropriate audio tags
        """
        tags = []
        
        # Get emotional context tags
        if conversation_type in self.EMOTIONAL_TAGS:
            emotional_categories = self.EMOTIONAL_TAGS[conversation_type]
            
            if turn_position == "opening" and "opener" in emotional_categories:
                tags.extend(random.sample(emotional_categories["opener"], 1))
            elif turn_position == "middle":
                # Choose based on content analysis
                if any(word in text_content.lower() for word in ["urgent", "important", "immediately", "now"]):
                    if "creating_urgency" in emotional_categories:
                        tags.extend(random.sample(emotional_categories["creating_urgency"], 1))
                elif any(word in text_content.lower() for word in ["understand", "help", "support"]):
                    if "building_trust" in emotional_categories:
                        tags.extend(random.sample(emotional_categories["building_trust"], 1))
                elif any(word in text_content.lower() for word in ["tell", "give", "provide", "confirm"]):
                    if "extracting_info" in emotional_categories:
                        tags.extend(random.sample(emotional_categories["extracting_info"], 1))
                else:
                    # Default middle conversation tags
                    available_tags = []
                    for category in ["building_trust", "informing", "requesting"]:
                        if category in emotional_categories:
                            available_tags.extend(emotional_categories[category])
                    if available_tags:
                        tags.extend(random.sample(available_tags, 1))
            elif turn_position == "closing" and "closing" in emotional_categories:
                tags.extend(random.sample(emotional_categories["closing"], 1))
        
        # Add voice modulation based on content
        if "?" in text_content:
            # Questions get inquisitive tags
            tags.extend(random.sample(["curious", "questioning"], 1))
        
        if "!" in text_content:
            # Exclamations get excited or urgent tags
            tags.extend(random.sample(["excited", "emphatic"], 1))
        
        # Add conversational reactions occasionally (10% chance)
        if random.random() < 0.1:
            reaction_tags = random.sample(self.CONVERSATIONAL_TAGS["reactions"], 1)
            tags.extend(reaction_tags)
        
        return tags[:2]  # Limit to 2 tags maximum for best results
    
    def format_text_with_tags(self, text: str, tags: List[str]) -> str:
        """
        Format text with audio tags for ElevenLabs v3.
        
        Args:
            text: Original text
            tags: List of audio tags to apply
            
        Returns:
            Text formatted with audio tags
        """
        if not tags:
            return text
        
        # Format tags according to ElevenLabs v3 specification
        formatted_tags = []
        for tag in tags:
            if tag and tag.strip():
                formatted_tags.append(f"[{tag.lower()}]")
        
        if not formatted_tags:
            return text
        
        # Apply tags at the beginning of the text
        tag_prefix = "".join(formatted_tags)
        return f"{tag_prefix} {text}"
    
    def get_emotion_for_conversation_type(self, conversation_type: str, intensity: str = "medium") -> str:
        """
        Get a default emotion tag for a conversation type.
        
        Args:
            conversation_type: "scam" or "legit"
            intensity: "low", "medium", "high"
            
        Returns:
            Appropriate emotion tag
        """
        if conversation_type == "scam":
            emotions = {
                "low": ["professional", "serious"],
                "medium": ["concerned", "urgent"],
                "high": ["alarmed", "pressing"]
            }
        else:  # legit
            emotions = {
                "low": ["calm", "polite"],
                "medium": ["friendly", "helpful"],
                "high": ["enthusiastic", "warm"]
            }
        
        return random.choice(emotions.get(intensity, emotions["medium"]))
    
    def analyze_text_for_tags(self, text: str) -> List[str]:
        """
        Analyze text content to suggest appropriate audio tags.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of suggested audio tags
        """
        text_lower = text.lower()
        suggested_tags = []
        
        # Emotional analysis
        if any(word in text_lower for word in ["urgent", "emergency", "immediately", "crisis"]):
            suggested_tags.append("urgent")
        elif any(word in text_lower for word in ["please", "thank", "appreciate", "grateful"]):
            suggested_tags.append("polite")
        elif any(word in text_lower for word in ["sorry", "apologize", "regret"]):
            suggested_tags.append("apologetic")
        elif any(word in text_lower for word in ["congratulations", "excellent", "wonderful", "great"]):
            suggested_tags.append("pleased")
        
        # Speech pattern analysis
        if text.count("?") >= 2:
            suggested_tags.append("questioning")
        elif text.count("!") >= 2:
            suggested_tags.append("emphatic")
        elif len(text.split()) <= 3:
            suggested_tags.append("brief")
        elif len(text.split()) >= 20:
            suggested_tags.append("deliberate")
        
        return suggested_tags[:2]  # Limit to 2 tags