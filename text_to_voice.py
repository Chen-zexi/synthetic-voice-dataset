import json
import os
import random
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import time
from pydub import AudioSegment
import glob
from pydub import AudioSegment
from pydub.effects import low_pass_filter, high_pass_filter
from config import VOICE_IDS, voice_language, voice_input_file, voice_output_dir, voice_sample_limit
load_dotenv()

# Initialize ElevenLabs client
elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)


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

def add_background_and_sound_effects(audio_file, background_audio_volume_reduction_in_db=18):
    """Add background and sound effects to the audio file
    Select a random background sound from the background_sounds folder
    Select a random sound effect from the sound_effects folder
    Add the background sound and sound effect to the audio file
    Save the audio file
    """
    background_sounds = glob.glob(os.path.join("sound_effects/backgrounds", "*.mp3"))
    call_end_sound_effects = glob.glob(os.path.join("sound_effects/call_effects", "call_end_*.mp3"))[0]
    # call_start_sound_effects = glob.glob(os.path.join("sound_effects/call_effects", "call_start_*.mp3"))[0] # not used for now
    background_sound = random.choice(background_sounds)
    background_audio = AudioSegment.from_file(background_sound)
    call_end_sound_effect_audio = AudioSegment.from_file(call_end_sound_effects)
    call_audio = AudioSegment.from_file(audio_file)

    # Handle length mismatch between call audio and background audio
    call_duration = len(call_audio)
    background_duration = len(background_audio)

    if background_duration < call_duration:
        # Repeat the background audio to match or exceed the call audio length
        repeats = (call_duration // background_duration) + 1
        extended_background = background_audio * repeats
        # Trim to exact length
        background_audio = extended_background[:call_duration]
    elif background_duration > call_duration:
        # Randomly sample a snippet from the background audio
        start = random.randint(0, background_duration - call_duration)
        background_audio = background_audio[start:start + call_duration]
    # Now background_audio is the same length as call_audio

    # Reduce background audio volume to be significantly lower than the call audio
    background_audio_quiet = background_audio - background_audio_volume_reduction_in_db  # Lower by 18 dB (adjust as needed)
    # Optionally, you can also reduce the sound effect volume if needed
    # sound_effect_audio_quiet = sound_effect_audio - 10

    # Overlay the quieter background audio with the call audio
    combined_audio = call_audio.overlay(background_audio_quiet)

    # Finish the call ending with the sound effect
    # Append the call_end_sound_effect_audio to the end of the combined_audio (do NOT overlay)
    combined_audio = combined_audio + call_end_sound_effect_audio

    # save the combined audio file
    combined_audio.export(audio_file.replace('.wav', '_background_and_sound_effects.wav'), format="wav")
    

def apply_phone_call_quality_bandpass_filter(audio_file):
    audio = AudioSegment.from_file(audio_file)
    audio = high_pass_filter(audio, 300)
    audio = low_pass_filter(audio, 3400)
    audio.export(audio_file.replace('.wav', '_bandpass_filtered.wav'), format="wav")

def generate_audio_for_conversation(conversation, output_dir):
    """Generate audio files for a single conversation"""
    conversation_id = conversation["conversation_id"]
    dialogue = conversation["dialogue"]
    
    # Create output directory for this conversation
    conv_dir = os.path.join(output_dir, f"conversation_{conversation_id}")
    os.makedirs(conv_dir, exist_ok=True)
    
    # Randomly choose two different voice IDs
    voice_ids = random.sample(VOICE_IDS[voice_language], 2)
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

        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"  Skipping existing file: {filename}")
            continue
        
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

    # add post processing to the combined audio file
    add_background_and_sound_effects(combined_filepath)

    # apply bandpass filter to the combined audio file
    apply_phone_call_quality_bandpass_filter(combined_filepath)
    
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
   
    if not os.path.exists(voice_input_file):
        print(f"Error: {voice_input_file} not found!")
        return
    
    # Create output directory
    os.makedirs(voice_output_dir, exist_ok=True)
    
    # Load conversations
    with open(voice_input_file, "r", encoding="utf-8") as f:
        conversations = json.load(f)
    
    print(f"Found {len(conversations)} conversations to process")
    
    all_metadata = []
    
    for i, conversation in enumerate(conversations[:voice_sample_limit]):
        print(f"\n--- Processing Conversation {i+1}/{len(conversations)} ---")
        
        try:
            metadata = generate_audio_for_conversation(conversation, voice_output_dir)
            all_metadata.append(metadata)
            print(f"Successfully processed conversation {conversation['conversation_id']}")
            
        except Exception as e:
            print(f"Error processing conversation {conversation['conversation_id']}: {e}")
        
        
if __name__ == "__main__":
    main() 