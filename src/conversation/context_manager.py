"""
Context management for multi-stage conversation generation.
"""

import logging
from typing import List, Dict, Optional, Tuple
from src.conversation.schemas import DialogueTurn, ConversationStage

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """
    Manages context between conversation stages for coherence and quality.
    """
    
    def __init__(self):
        """Initialize the context manager."""
        self.logger = logging.getLogger(__name__)
    
    def summarize_stage_context(self, stage_dialogue: List[Dict], stage_name: str) -> str:
        """
        Summarize the context from a conversation stage.
        
        Args:
            stage_dialogue: List of dialogue turns from the stage
            stage_name: Name of the conversation stage
            
        Returns:
            Context summary string
        """
        if not stage_dialogue:
            return f"Stage '{stage_name}' completed with no dialogue."
        
        # Extract key information from the dialogue
        caller_turns = [turn for turn in stage_dialogue if turn.get('role') == 'caller']
        callee_turns = [turn for turn in stage_dialogue if turn.get('role') == 'callee']
        
        # Build context summary
        context_parts = [f"Stage: {stage_name}"]
        context_parts.append(f"Turns: {len(stage_dialogue)}")
        
        # Key caller points
        if caller_turns:
            key_caller_points = self._extract_key_points(caller_turns)
            if key_caller_points:
                context_parts.append(f"Caller key points: {'; '.join(key_caller_points)}")
        
        # Key callee responses
        if callee_turns:
            key_callee_responses = self._extract_key_responses(callee_turns)
            if key_callee_responses:
                context_parts.append(f"Callee responses: {'; '.join(key_callee_responses)}")
        
        # Emotional/urgency level
        urgency_level = self._assess_urgency_level(stage_dialogue)
        if urgency_level:
            context_parts.append(f"Urgency level: {urgency_level}")
        
        return " | ".join(context_parts)
    
    def _extract_key_points(self, caller_turns: List[Dict]) -> List[str]:
        """
        Extract key points from caller turns.
        
        Args:
            caller_turns: List of caller dialogue turns
            
        Returns:
            List of key points
        """
        key_points = []
        
        for turn in caller_turns:
            text = turn.get('text', '').lower()
            
            # Look for key scammer tactics
            if any(word in text for word in ['urgent', 'immediately', 'right now', 'asap']):
                key_points.append("created urgency")
            
            if any(word in text for word in ['verify', 'confirm', 'check', 'validate']):
                key_points.append("requested verification")
            
            if any(word in text for word in ['sms', 'text', 'message', 'link', 'click']):
                key_points.append("mentioned SMS/link")
            
            if any(word in text for word in ['payment', 'pay', 'money', 'fee', 'charge']):
                key_points.append("discussed payment")
            
            if any(word in text for word in ['security', 'safety', 'protect', 'secure']):
                key_points.append("emphasized security")
            
            if any(word in text for word in ['account', 'profile', 'information', 'details']):
                key_points.append("requested account info")
        
        return list(set(key_points))  # Remove duplicates
    
    def _extract_key_responses(self, callee_turns: List[Dict]) -> List[str]:
        """
        Extract key responses from callee turns.
        
        Args:
            callee_turns: List of callee dialogue turns
            
        Returns:
            List of key response types
        """
        key_responses = []
        
        for turn in callee_turns:
            text = turn.get('text', '').lower()
            
            # Look for victim response patterns
            if any(word in text for word in ['yes', 'okay', 'sure', 'alright', 'fine']):
                key_responses.append("showed compliance")
            
            if any(word in text for word in ['no', 'not sure', 'hesitant', 'doubt']):
                key_responses.append("expressed hesitation")
            
            if any(word in text for word in ['question', 'why', 'how', 'what', 'when']):
                key_responses.append("asked questions")
            
            if any(word in text for word in ['received', 'got', 'see', 'check']):
                key_responses.append("acknowledged receipt")
            
            if any(word in text for word in ['scared', 'worried', 'concerned', 'nervous']):
                key_responses.append("showed concern")
        
        return list(set(key_responses))  # Remove duplicates
    
    def _assess_urgency_level(self, stage_dialogue: List[Dict]) -> Optional[str]:
        """
        Assess the urgency level of a conversation stage.
        
        Args:
            stage_dialogue: List of dialogue turns
            
        Returns:
            Urgency level description or None
        """
        urgency_indicators = 0
        total_turns = len(stage_dialogue)
        
        if total_turns == 0:
            return None
        
        for turn in stage_dialogue:
            text = turn.get('text', '').lower()
            
            # Count urgency indicators
            if any(word in text for word in ['urgent', 'immediately', 'right now', 'asap', 'hurry']):
                urgency_indicators += 1
            
            if any(word in text for word in ['time', 'deadline', 'expire', 'expired', 'limited']):
                urgency_indicators += 1
            
            if any(word in text for word in ['consequence', 'penalty', 'suspended', 'locked', 'blocked']):
                urgency_indicators += 1
        
        urgency_ratio = urgency_indicators / total_turns
        
        if urgency_ratio > 0.5:
            return "high"
        elif urgency_ratio > 0.2:
            return "medium"
        elif urgency_ratio > 0:
            return "low"
        else:
            return "none"
    
    def build_continuation_prompt(self, previous_context: str, next_stage: str, 
                                 full_conversation: List[Dict] = None) -> str:
        """
        Build a prompt for continuing the conversation in the next stage.
        
        Args:
            previous_context: Context from previous stages
            next_stage: Name of the next stage
            full_conversation: Full conversation so far (optional)
            
        Returns:
            Continuation prompt
        """
        prompt_parts = [
            f"Continue the conversation in the '{next_stage}' stage.",
            f"Previous context: {previous_context}"
        ]
        
        if full_conversation:
            # Add recent dialogue for context
            recent_turns = full_conversation[-4:] if len(full_conversation) > 4 else full_conversation
            if recent_turns:
                recent_dialogue = " | ".join([
                    f"{turn.get('role', 'unknown')}: {turn.get('text', '')[:100]}..."
                    for turn in recent_turns
                ])
                prompt_parts.append(f"Recent dialogue: {recent_dialogue}")
        
        # Add stage-specific guidance
        stage_guidance = self._get_stage_guidance(next_stage)
        if stage_guidance:
            prompt_parts.append(f"Stage guidance: {stage_guidance}")
        
        return " | ".join(prompt_parts)
    
    def _get_stage_guidance(self, stage_name: str) -> str:
        """
        Get guidance for a specific conversation stage.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            Stage-specific guidance
        """
        guidance_map = {
            "opening": "Establish identity, build initial rapport, introduce the reason for calling",
            "building_trust": "Provide detailed information, use technical terms, address concerns professionally",
            "creating_urgency": "Introduce time pressure, escalate importance, maintain professionalism while creating urgency",
            "action_request": "Request specific action, provide clear instructions, handle objections",
            "closing": "Confirm actions, provide reassurance, end call naturally"
        }
        
        return guidance_map.get(stage_name, "Continue the conversation naturally")
    
    def validate_conversation_coherence(self, full_conversation: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate the coherence of a full conversation.
        
        Args:
            full_conversation: Complete conversation dialogue
            
        Returns:
            Tuple of (is_coherent, list_of_issues)
        """
        issues = []
        
        if not full_conversation:
            return False, ["Empty conversation"]
        
        # Check for role alternation
        role_issues = self._check_role_alternation(full_conversation)
        if role_issues:
            issues.extend(role_issues)
        
        # Check for logical flow
        flow_issues = self._check_logical_flow(full_conversation)
        if flow_issues:
            issues.extend(flow_issues)
        
        # Check for consistency
        consistency_issues = self._check_consistency(full_conversation)
        if consistency_issues:
            issues.extend(consistency_issues)
        
        is_coherent = len(issues) == 0
        return is_coherent, issues
    
    def _check_role_alternation(self, conversation: List[Dict]) -> List[str]:
        """
        Check if roles alternate properly in the conversation.
        
        Args:
            conversation: List of dialogue turns
            
        Returns:
            List of role alternation issues
        """
        issues = []
        
        for i, turn in enumerate(conversation):
            if i == 0:
                # First turn should be caller
                if turn.get('role') != 'caller':
                    issues.append(f"First turn should be caller, got {turn.get('role')}")
            else:
                # Subsequent turns should alternate
                prev_role = conversation[i-1].get('role')
                current_role = turn.get('role')
                
                if prev_role == current_role:
                    issues.append(f"Consecutive turns with same role '{current_role}' at position {i}")
        
        return issues
    
    def _check_logical_flow(self, conversation: List[Dict]) -> List[str]:
        """
        Check for logical flow issues in the conversation.
        
        Args:
            conversation: List of dialogue turns
            
        Returns:
            List of logical flow issues
        """
        issues = []
        
        # Check for abrupt topic changes
        for i in range(1, len(conversation)):
            prev_text = conversation[i-1].get('text', '').lower()
            curr_text = conversation[i].get('text', '').lower()
            
            # Look for contradictory statements
            if 'yes' in prev_text and 'no' in curr_text:
                issues.append(f"Potential contradiction between turns {i-1} and {i}")
            
            # Check for unrealistic responses
            if len(curr_text) > 200:  # Very long responses might be unrealistic
                issues.append(f"Turn {i} has unusually long response ({len(curr_text)} chars)")
        
        return issues
    
    def _check_consistency(self, conversation: List[Dict]) -> List[str]:
        """
        Check for consistency issues in the conversation.
        
        Args:
            conversation: List of dialogue turns
            
        Returns:
            List of consistency issues
        """
        issues = []
        
        # Extract key entities mentioned
        entities = set()
        for turn in conversation:
            text = turn.get('text', '')
            # Look for names, numbers, dates, etc.
            # This is a simplified check - could be enhanced
            if any(char.isdigit() for char in text):
                entities.add("numbers")
            if any(word in text.lower() for word in ['mr.', 'ms.', 'mrs.', 'dr.']):
                entities.add("titles")
        
        # Check for consistent use of entities
        if len(entities) > 3:  # Too many different entity types might indicate inconsistency
            issues.append("Conversation mentions many different types of entities")
        
        return issues
    
    def get_conversation_summary(self, full_conversation: List[Dict]) -> str:
        """
        Get a comprehensive summary of the full conversation.
        
        Args:
            full_conversation: Complete conversation dialogue
            
        Returns:
            Conversation summary
        """
        if not full_conversation:
            return "Empty conversation"
        
        summary_parts = [
            f"Total turns: {len(full_conversation)}",
            f"Caller turns: {len([t for t in full_conversation if t.get('role') == 'caller'])}",
            f"Callee turns: {len([t for t in full_conversation if t.get('role') == 'callee'])}"
        ]
        
        # Assess overall conversation characteristics
        is_coherent, issues = self.validate_conversation_coherence(full_conversation)
        summary_parts.append(f"Coherence: {'Good' if is_coherent else 'Issues detected'}")
        
        if issues:
            summary_parts.append(f"Issues: {', '.join(issues[:3])}")  # Show first 3 issues
        
        return " | ".join(summary_parts)
