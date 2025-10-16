# Long Conversation Generation Guide

This guide explains the new long conversation generation features that create realistic 5-minute scam conversations with SMS link behavior.

## Overview

The enhanced conversation generation system now supports:

- **Longer Conversations**: 25-40 turns (approximately 5 minutes of audio)
- **Multi-Stage Generation**: Breaks conversations into logical stages for better coherence
- **SMS Link Behavior**: Injects realistic SMS link tactics into 40-50% of conversations
- **Quality Maintenance**: Advanced context management and coherence validation

## Key Features

### 1. Multi-Stage Generation

Conversations are now generated in 5 distinct stages:

1. **Opening** (5-8 turns): Establish identity and build rapport
2. **Building Trust** (8-12 turns): Provide detailed information and address concerns
3. **Creating Urgency** (6-10 turns): Introduce time pressure and consequences
4. **Action Request** (4-8 turns): Request specific action (SMS link, payment, etc.)
5. **Closing** (2-5 turns): Confirm actions and provide reassurance

### 2. SMS Link Behavior

The system can inject realistic SMS link tactics into conversations:

- **Verification Links**: "I'll send you a verification link via SMS"
- **Payment Links**: "Check your SMS for the payment portal"
- **Security Checks**: "Click the link to verify your identity"
- **Document Downloads**: "Download the document from the link"
- **Prize Claims**: "Claim your prize using the link"

### 3. Quality Maintenance

Advanced features ensure conversation quality:

- **Context Summarization**: Maintains coherence between stages
- **Coherence Validation**: Checks for logical flow and consistency
- **Character Consistency**: Maintains personality traits throughout
- **Stage Guidelines**: Explicit instructions for each conversation phase

## Configuration

### Basic Settings

Update `configs/common.json`:

```json
{
  "followup_turns": {
    "num_turns_lower_limit": 25,
    "num_turns_upper_limit": 40
  },
  "multi_stage_generation": {
    "enabled": true,
    "stages": [
      {"name": "opening", "min_turns": 5, "max_turns": 8},
      {"name": "building_trust", "min_turns": 8, "max_turns": 12},
      {"name": "creating_urgency", "min_turns": 6, "max_turns": 10},
      {"name": "action_request", "min_turns": 4, "max_turns": 8},
      {"name": "closing", "min_turns": 2, "max_turns": 5}
    ]
  },
  "sms_link_behavior": {
    "enabled": true,
    "injection_probability": 0.45,
    "injection_stages": ["creating_urgency", "action_request"],
    "link_types": ["verification", "payment", "security_check", "document_download", "prize_claim"]
  }
}
```

### Locale-Specific SMS Templates

Create `configs/localizations/{locale}/sms_link_templates.json`:

```json
{
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
  }
}
```

## Usage Examples

### Basic Long Conversation Generation

```bash
# Generate long conversations with default settings
python main.py --locale ar-sa --steps conversation

# Generate with custom turn limits
python main.py --locale ar-sa --conversation-min-turns 30 --conversation-max-turns 45

# Test with small sample
python main.py --locale ar-sa --total-limit 10 --steps conversation
```

### SMS Link Behavior Control

```bash
# Disable SMS link injection for testing
python main.py --locale ar-sa --disable-sms-links

# Generate with specific SMS link types
python main.py --locale ar-sa --sms-link-types verification payment
```

### Testing and Validation

```bash
# Run comprehensive tests
python scripts/test_long_conversations.py --locale ar-sa --num-conversations 20

# Test specific features
python scripts/test_long_conversations.py --locale ar-sa --test-sms-behavior
```

## Output Structure

### Conversation Format

Long conversations include additional metadata:

```json
{
  "conversation_id": 1,
  "generation_method": "multi_stage",
  "num_turns": 32,
  "sms_link_injected": true,
  "link_type": "verification",
  "stages": [
    {
      "stage_name": "opening",
      "stage_turns": 6,
      "dialogue": [...],
      "context_summary": "Stage: opening | Turns: 6 | Caller key points: created urgency"
    }
  ],
  "coherence_issues": [],
  "dialogue": [...]
}
```

### Quality Metrics

The system tracks:

- **Turn Count Distribution**: Ensures 25-40 turn range
- **SMS Injection Rate**: Monitors 40-50% target
- **Coherence Score**: Validates conversation flow
- **Stage Completion**: Ensures all stages are generated
- **Character Consistency**: Maintains personality traits

## Best Practices

### 1. Stage Configuration

- **Opening**: Keep professional but friendly tone
- **Building Trust**: Use technical terms and official procedures
- **Creating Urgency**: Escalate gradually, maintain professionalism
- **Action Request**: Provide clear, step-by-step instructions
- **Closing**: End naturally with reassurance

### 2. SMS Link Integration

- **Timing**: Inject during urgency and action request stages
- **Context**: Ensure SMS links fit the scam scenario
- **Variety**: Use different link types for diversity
- **Realism**: Include victim hesitation and compliance

### 3. Quality Maintenance

- **Context Summarization**: Keep stage summaries concise but informative
- **Coherence Validation**: Check for logical flow and consistency
- **Character Consistency**: Maintain personality traits throughout
- **Stage Guidelines**: Follow explicit instructions for each phase

## Troubleshooting

### Common Issues

1. **Conversations Too Short**
   - Check `num_turns_lower_limit` in configuration
   - Verify multi-stage generation is enabled
   - Ensure stage turn limits are appropriate

2. **SMS Links Not Appearing**
   - Verify `sms_link_behavior.enabled` is true
   - Check `injection_probability` setting
   - Ensure SMS templates exist for locale

3. **Poor Conversation Quality**
   - Enable context management features
   - Check character profile consistency
   - Verify stage guidelines are followed

4. **Coherence Issues**
   - Review context summarization between stages
   - Check for contradictory statements
   - Validate character consistency

### Debug Mode

```bash
# Enable verbose logging
python main.py --locale ar-sa --verbose

# Test with specific configuration
python main.py --locale ar-sa --config-dir custom_configs
```

## Performance Considerations

### Generation Time

- **Multi-stage generation**: ~2-3x longer than single-stage
- **Context management**: Minimal overhead
- **SMS link injection**: Negligible impact
- **Quality validation**: Small additional processing time

### Memory Usage

- **Stage context**: Minimal memory footprint
- **Conversation storage**: Slightly larger due to metadata
- **Template caching**: Efficient template management

### API Costs

- **Token usage**: Higher due to longer conversations
- **Multi-stage calls**: Multiple API calls per conversation
- **Context summarization**: Additional processing

## Migration Guide

### From Short to Long Conversations

1. **Update Configuration**:
   ```bash
   # Update turn limits
   sed -i 's/"num_turns_lower_limit": 7/"num_turns_lower_limit": 25/' configs/common.json
   sed -i 's/"num_turns_upper_limit": 10/"num_turns_upper_limit": 40/' configs/common.json
   ```

2. **Enable Multi-Stage Generation**:
   ```json
   "multi_stage_generation": {
     "enabled": true
   }
   ```

3. **Configure SMS Link Behavior**:
   ```json
   "sms_link_behavior": {
     "enabled": true,
     "injection_probability": 0.45
   }
   ```

### Backward Compatibility

- **Existing conversations**: Continue to work unchanged
- **Configuration**: Backward compatible with old settings
- **API**: No breaking changes to existing interfaces
- **Output format**: Enhanced but compatible

## Advanced Configuration

### Custom Stage Definitions

```json
"multi_stage_generation": {
  "stages": [
    {"name": "greeting", "min_turns": 3, "max_turns": 5},
    {"name": "credibility", "min_turns": 10, "max_turns": 15},
    {"name": "pressure", "min_turns": 8, "max_turns": 12},
    {"name": "action", "min_turns": 6, "max_turns": 10},
    {"name": "wrap_up", "min_turns": 2, "max_turns": 4}
  ]
}
```

### SMS Link Customization

```json
"sms_link_behavior": {
  "enabled": true,
  "injection_probability": 0.6,
  "injection_stages": ["pressure", "action"],
  "link_types": ["verification", "payment"],
  "custom_phrases": {
    "verification": ["Click the secure link I sent"],
    "payment": ["Use the payment link in your SMS"]
  }
}
```

## Monitoring and Analytics

### Quality Metrics

- **Turn Count Distribution**: Histogram of conversation lengths
- **SMS Injection Rate**: Percentage of conversations with SMS links
- **Coherence Score**: Average conversation coherence rating
- **Stage Completion**: Success rate for each conversation stage

### Performance Metrics

- **Generation Time**: Average time per conversation
- **API Usage**: Token consumption and costs
- **Success Rate**: Percentage of successful generations
- **Error Rate**: Frequency of generation failures

### Reporting

```bash
# Generate quality report
python scripts/test_long_conversations.py --generate-report

# Monitor SMS injection rate
python scripts/test_long_conversations.py --monitor-sms-rate

# Validate conversation quality
python scripts/test_long_conversations.py --validate-quality
```

## Conclusion

The long conversation generation system provides a powerful way to create realistic, high-quality scam conversations that better reflect real-world scenarios. The multi-stage approach ensures coherence, while SMS link behavior adds authenticity to the generated data.

For questions or issues, refer to the main README.md or create an issue in the project repository.
