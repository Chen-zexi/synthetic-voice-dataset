"""
Audio packager for creating ZIP archives of conversation audio files.
"""

import zipfile
import logging
import os
import subprocess
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

from config.config_loader import Config
from utils.logging_utils import ConditionalLogger
import shutil 

logger = logging.getLogger(__name__)


class AudioPackager:
    """
    Packages audio files into ZIP archives for distribution.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the audio packager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.clogger = ConditionalLogger(__name__, config.verbose)
        logger.info("Audio packager initialized")
        logger.info(f"Scam audio directory: {self.config.post_processing_scam_audio_dir}")
    
    def package_all(self):
        """
        Package both scam and legitimate audio files.
        """
        self.clogger.debug("Packaging audio files")
        
        # Resample audio files before packaging
        self._resample_audio_files()
        
        # Check which directories exist
        scam_exists = self.config.post_processing_scam_audio_dir.exists()
        legit_exists = self.config.post_processing_legit_audio_dir.exists()
        
        # Package scam audio if directory exists
        if scam_exists:
            self._package_scam_audio()
        else:
            self.clogger.debug(f"Scam audio directory not found: {self.config.post_processing_scam_audio_dir}")
        
        # Package legitimate audio if directory exists
        if legit_exists:
            self._package_legit_audio()
        else:
            self.clogger.debug(f"Legit audio directory not found: {self.config.post_processing_legit_audio_dir}")
    
    def _resample_audio_files(self):
        """
        Resample audio files to 16kHz, mono, 64kbps before packaging.
        """
        
        # Process scam audio directory
        scam_audio_dir = self.config.post_processing_scam_audio_dir
        if scam_audio_dir.exists():
            self.clogger.info(f"Resampling audio files in {scam_audio_dir}")
            self._resample_audio_directory(scam_audio_dir)
        else:
            self.clogger.warning(f"Scam audio directory not found in resampleing audio files function: {scam_audio_dir}")
        
        # Process legitimate audio directory
        legit_audio_dir = self.config.post_processing_legit_audio_dir
        if legit_audio_dir.exists():
            self.clogger.info(f"Resampling audio files in {legit_audio_dir}")
            self._resample_audio_directory(legit_audio_dir)
        else:
            self.clogger.warning(f"Legitimate audio directory not found in resampleing audio files function: {legit_audio_dir}")
    
    def _resample_audio_directory(self, root_dir: Path):
        """
        Resample audio files in a directory structure.
        
        Args:
            root_dir: Root directory containing audio folders
        """
        self.clogger.info(f"Resampling audio files in {root_dir}")
        # Loop over each folder in the root directory
        for folder_name in os.listdir(root_dir):
            folder_path = os.path.join(root_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            output_dir = folder_path  # Write resampled files to the same folder as the original files
            
            # Loop over each file in the folder
            for file_name in os.listdir(folder_path):
                if file_name.lower().endswith('.wav'):
                    if file_name.endswith('_sampled.wav'):
                        continue
                    file_path = os.path.join(folder_path, file_name)
                    conversation_id_str = file_name.split(".")[0]
                    output_path = os.path.join(output_dir, f"{conversation_id_str}_sampled.wav")

                    self.clogger.debug(f"Resampling {file_name} to {output_path}")
                    # Use ffmpeg to resample to 16kHz, mono, 64kbps
                    command = [
                        "ffmpeg",
                        "-y",  # Overwrite output file if it exists
                        "-i", file_path,
                        "-ar", "16000",  # Set sample rate to 16kHz
                        "-ac", "1",      # Set to mono
                        "-b:a", "64k",   # Set audio bitrate to 64kbps
                        output_path
                    ]
                    
                    try:
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if result.returncode == 0:
                            self.clogger.info(f"Resampled {file_name} to {output_path}")
                        else:
                            self.clogger.warning(f"Failed to resample {file_name}: {result.stderr.decode()}")
                    except Exception as e:
                        self.clogger.error(f"Error resampling {file_name}: {e}")
    
    def _package_scam_audio(self):
        """
        Package scam conversation audio files into a ZIP archive.
        """
        audio_dir = self.config.post_processing_scam_audio_dir
        output_path = self.config.post_processing_scam_audio_zip_output
        
        if not audio_dir.exists():
            self.clogger.warning(f"Scam audio directory not found: {audio_dir}")
            return
        
        self.clogger.info(f"Packaging scam audio from {audio_dir}")
        
        files_to_zip = self._collect_audio_files(audio_dir)
        
        if files_to_zip:
            self._create_zip(files_to_zip, output_path)
            self.clogger.debug(f"Packaged {len(files_to_zip)} scam audio files")
        else:
            self.clogger.warning("No scam audio files found to package")
    
    def _package_legit_audio(self):
        """
        Package legitimate conversation audio files into a ZIP archive.
        """
        audio_dir = self.config.post_processing_legit_audio_dir
        output_path = self.config.post_processing_legit_audio_zip_output
        
        if not audio_dir.exists():
            self.clogger.warning(f"Legitimate audio directory not found: {audio_dir}")
            return
        
        self.clogger.info(f"Packaging legitimate audio from {audio_dir}")
        
        files_to_zip = self._collect_audio_files(audio_dir)
        
        if files_to_zip:
            self._create_zip(files_to_zip, output_path)
            self.clogger.debug(f"Packaged {len(files_to_zip)} legitimate audio files")
        else:
            self.clogger.warning("No legitimate audio files found to package")
    
    def _collect_audio_files(self, audio_dir: Path) -> List[Tuple[Path, str]]:
        """
        Collect all final audio files from conversation subdirectories.
        Prioritizes resampled files in _sampled directories.
        
        Args:
            audio_dir: Base audio directory
            
        Returns:
            List of (file_path, archive_name) tuples
        """
        files_to_zip = []
        
        for subdir in audio_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith("conversation_"):
                # Prefer the "_sampled.wav" version if it exists, otherwise use the original version
                for pattern in ["*_final_sampled.wav"]:
                    final_files = list(subdir.glob(pattern))
                    
                    if final_files:
                        # Use the first matching file
                        file_path = final_files[0]
                        # Rename the file for the archive: remove '_final_sampled' from the filename and use '.wav'
                        new_file_name = file_path.name.replace('_final_sampled', '').replace('_combined', '')
                        new_file_path = file_path.parent / new_file_name
                        if not new_file_path.exists():
                            file_path.rename(new_file_path)
                        file_path = new_file_path
                        archive_name = f"{subdir.name}_{new_file_name}"
                        files_to_zip.append((file_path, archive_name))
                        break

        if not files_to_zip:
            self.clogger.warning(f"No audio files found to package in {audio_dir}")
            return []
        
        self.clogger.debug(f"Found {len(files_to_zip)} audio files to package")
        return files_to_zip
    
    def _create_zip(self, files_to_zip: List[Tuple[Path, str]], output_path: Path):
        """
        Create a ZIP archive with the specified files.
        Sets random creation dates between 2025-07-01 and 2025-07-15.
        
        Args:
            files_to_zip: List of (file_path, archive_name) tuples
            output_path: Path for the output ZIP file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Define date range for random creation dates
        start_date = datetime(2025, 7, 1)
        end_date = datetime(2025, 7, 15)
        
        # Create ZIP file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, archive_name in files_to_zip:
                # Generate random date between 2025-07-01 and 2025-07-15
                random_days = random.randint(0, (end_date - start_date).days)
                random_date = start_date + timedelta(days=random_days)
                
                # Add random time within the day
                random_hours = random.randint(0, 23)
                random_minutes = random.randint(0, 59)
                random_seconds = random.randint(0, 59)
                random_date = random_date.replace(
                    hour=random_hours, 
                    minute=random_minutes, 
                    second=random_seconds
                )
                
                self.clogger.debug(f"Adding {archive_name} to archive with date {random_date}")
                
                # Create ZipInfo with custom date
                zip_info = zipfile.ZipInfo(archive_name)
                zip_info.date_time = (
                    random_date.year,
                    random_date.month,
                    random_date.day,
                    random_date.hour,
                    random_date.minute,
                    random_date.second
                )
                
                # Read file content and add to zip with custom date
                with open(file_path, 'rb') as f:
                    zipf.writestr(zip_info, f.read())
        
        # Log file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        self.clogger.debug(f"Created ZIP archive: {output_path} ({size_mb:.1f} MB)")