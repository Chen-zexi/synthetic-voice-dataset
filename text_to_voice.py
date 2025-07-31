import json
import os
import random
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import time
from pydub import AudioSegment
import glob

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

def combine_audio_files(conversation_dir, conversation_id):
    """Combine all audio files in a conversation directory into a single file"""
    # Get all mp3 files in the conversation directory
    audio_files = glob.glob(os.path.join(conversation_dir, "turn_*.mp3"))
    
    if not audio_files:
        print(f"No audio files found in {conversation_dir}")
        return None
    
    # Sort files by turn number to maintain conversation order
    audio_files.sort(key=lambda x: int(x.split('turn_')[1].split('_')[0]))
    
    print(f"Combining {len(audio_files)} audio files for conversation {conversation_id}")
    print(audio_files)
    
    # Load the first audio file
    combined_audio = AudioSegment.from_mp3(audio_files[0])
    
    # Add silence between turns (500ms)
    silence = AudioSegment.silent(duration=500)
    
    # Combine all audio files
    for audio_file in audio_files[1:]:
        audio_segment = AudioSegment.from_mp3(audio_file)
        combined_audio = combined_audio + silence + audio_segment
    
    # Save combined audio file as WAV for better compatibility
    combined_filename = f"conversation_{conversation_id}_combined.wav"
    combined_filepath = os.path.join(conversation_dir, combined_filename)
    combined_audio.export(combined_filepath, format="wav")
    
    print(f"Combined audio saved: {combined_filepath}")
    return combined_filepath

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
        
        # Generate filename - use .mp3 extension since we're using MP3 format
        filename = f"turn_{sent_id:02d}_{role}.mp3"
        filepath = os.path.join(conv_dir, filename)
        
        try:
            # Generate audio
            audio = elevenlabs.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio)
            
            # Save audio file
            with open(filepath, "wb") as f:
                f.write(audio_bytes)
            
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
    
    # Combine all audio files into a single file
    combined_filepath = combine_audio_files(conv_dir, conversation_id)
    
    # Save metadata for this conversation
    metadata = {
        "conversation_id": conversation_id,
        "caller_voice_id": caller_voice,
        "callee_voice_id": callee_voice,
        "audio_files": audio_files,
        "combined_audio_file": os.path.basename(combined_filepath) if combined_filepath else None
    }
    
    metadata_file = os.path.join(conv_dir, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return metadata

def main():
    # Load conversations from JSON file
    input_file = "generated_conversations_malay.json"
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
    
    for i, conversation in enumerate(conversations[:1]):
        print(f"\n--- Processing Conversation {i+1}/{len(conversations)} ---")
        
        try:
            metadata = generate_audio_for_conversation(conversation, output_dir)
            all_metadata.append(metadata)
            print(f"Successfully processed conversation {conversation['conversation_id']}")
            
        except Exception as e:
            print(f"Error processing conversation {conversation['conversation_id']}: {e}")
        
        
if __name__ == "__main__":
    main() 