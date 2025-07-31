import json
import os
import random
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import time

load_dotenv()

language = "Malay"

# Initialize ElevenLabs client
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# List of voice IDs to choose from (you can add more or modify these)
VOICE_IDS = {
    "Malay": ["BeIxObt4dYBRJLYoe1hU","NpVSXJvYSdIbjOaMbShj", "Wc6X61hTD7yucJMheuLN", "UcqZLa941Kkt8ZhEEybf", "C1gMsiiE7sXAt59fmvYg"],
}

def generate_audio_for_conversation(conversation, output_dir):
    """Generate audio files for a single conversation"""
    conversation_id = conversation["conversation_id"]
    dialogue = conversation["dialogue"]
    
    # Create output directory for this conversation
    conv_dir = os.path.join(output_dir, f"conversation_{conversation_id}")
    os.makedirs(conv_dir, exist_ok=True)
    
    # Randomly choose two different voice IDs
    voice_ids = random.sample(VOICE_IDS[language], 2)
    caller_voice = voice_ids[0]
    callee_voice = voice_ids[1]
    
    print(f"Conversation {conversation_id}: Using voices {caller_voice} (caller) and {callee_voice} (callee)")
    
    audio_files = []
    
    for turn in dialogue:
        sent_id = turn["sent_id"]
        text = turn["text"]
        role = turn["role"]
        
        # Choose voice based on role
        voice_id = caller_voice if role == "caller" else callee_voice
        
        # Generate filename
        filename = f"turn_{sent_id:02d}_{role}.wav"
        filepath = os.path.join(conv_dir, filename)
        
        try:
            # Generate audio
            audio = elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            
            # Save audio file
            with open(filepath, "wb") as f:
                f.write(audio)
            
            audio_files.append({
                "turn_id": sent_id,
                "role": role,
                "text": text,
                "voice_id": voice_id,
                "filename": filename
            })
            
            print(f"  Generated: {filename}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error generating audio for turn {sent_id}: {e}")
    
    # Save metadata for this conversation
    metadata = {
        "conversation_id": conversation_id,
        "caller_voice_id": caller_voice,
        "callee_voice_id": callee_voice,
        "audio_files": audio_files
    }
    
    metadata_file = os.path.join(conv_dir, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return metadata

def main():
    # Load conversations from JSON file
    input_file = "generated_conversations.json"
    output_dir = "audio_conversations"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load conversations
    with open(input_file, "r", encoding="utf-8") as f:
        conversations = json.load(f)
    
    print(f"Found {len(conversations)} conversations to process")
    
    all_metadata = []
    
    for i, conversation in enumerate(conversations):
        print(f"\n--- Processing Conversation {i+1}/{len(conversations)} ---")
        
        try:
            metadata = generate_audio_for_conversation(conversation, output_dir)
            all_metadata.append(metadata)
            print(f"Successfully processed conversation {conversation['conversation_id']}")
            
        except Exception as e:
            print(f"Error processing conversation {conversation['conversation_id']}: {e}")
    
    # Save overall metadata
    overall_metadata = {
        "total_conversations": len(conversations),
        "successful_conversations": len(all_metadata),
        "conversations": all_metadata
    }
    
    overall_metadata_file = os.path.join(output_dir, "overall_metadata.json")
    with open(overall_metadata_file, "w", encoding="utf-8") as f:
        json.dump(overall_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\nCompleted! Generated audio for {len(all_metadata)} conversations")
    print(f"Output directory: {output_dir}")
    print(f"Overall metadata saved to: {overall_metadata_file}")

if __name__ == "__main__":
    main() 