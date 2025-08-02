from config_arabic import (post_processing_legit_json_input, post_processing_legit_json_output,
                           post_processing_scam_json_input, post_processing_scam_json_output,
                           post_processing_region, post_processing_scam_audio_zip_output,
                           post_processing_legit_audio_zip_output, post_processing_scam_audio_dir,
                           post_processing_legit_audio_dir)
from collections import OrderedDict
import json
import zipfile
import os

#------------------------post processing scam json------------------------

# Load from input path
with open(post_processing_scam_json_input, "r", encoding="utf-8") as f:
    data = json.load(f)

# Process each conversation
updated_data = []
for convo in data:
    convo.pop("first_turn", None)  # Remove 'first_turn' if it exists

    # Add 'region' and 'is_vp' at the beginning
    new_convo = OrderedDict()
    new_convo["region"] = post_processing_region
    new_convo["is_vp"] = 1
    new_convo.update(convo)

    updated_data.append(new_convo)

# Save to output path
with open(post_processing_scam_json_output, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

#------------------------post processing legit json------------------------
# Load from input path
with open(post_processing_legit_json_input, "r", encoding="utf-8") as f:
    data = json.load(f)

# Process each conversation
updated_data = []
for convo in data:
    convo.pop("first_turn", None)  # Remove 'first_turn' if it exists

    # Add 'region' and 'is_vp' at the beginning
    new_convo = OrderedDict()
    new_convo["is_vp"] = 0
    new_convo.update(convo)

    updated_data.append(new_convo)

# Save to output path
with open(post_processing_legit_json_output, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

#------------------------ zip all scam audio------------------------
# Collect all matching .wav files
files_to_zip = []
for subdir in os.listdir(post_processing_scam_audio_dir):
    subdir_path = os.path.join(post_processing_scam_audio_dir, subdir)
    if os.path.isdir(subdir_path) and subdir.startswith("conversation_"):
        for file in os.listdir(subdir_path):
            if file.endswith("_combined_background_and_sound_effects.wav"):
                full_path = os.path.join(subdir_path, file)
                archive_name = file
                files_to_zip.append((full_path, archive_name))

# Create the ZIP
with zipfile.ZipFile(post_processing_scam_audio_zip_output, "w") as zipf:
    for file_path, arcname in files_to_zip:
        zipf.write(file_path, arcname)

print(f"Zipped {len(files_to_zip)} files into flat archive: {post_processing_scam_audio_zip_output}")

#------------------------ zip all legit audio------------------------
# Collect all matching .wav files
files_to_zip = []
for subdir in os.listdir(post_processing_legit_audio_dir):
    subdir_path = os.path.join(post_processing_legit_audio_dir, subdir)
    if os.path.isdir(subdir_path) and subdir.startswith("conversation_"):
        for file in os.listdir(subdir_path):
            if file.endswith("_combined_background_and_sound_effects.wav"):
                full_path = os.path.join(subdir_path, file)
                archive_name = file
                files_to_zip.append((full_path, archive_name))

# Create the ZIP
with zipfile.ZipFile(post_processing_legit_audio_zip_output, "w") as zipf:
    for file_path, arcname in files_to_zip:
        zipf.write(file_path, arcname)

print(f"Zipped {len(files_to_zip)} files into flat archive: {post_processing_legit_audio_zip_output}")
