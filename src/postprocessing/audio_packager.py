"""
Audio packager for creating ZIP archives of conversation audio files.
"""

import zipfile
import logging
from pathlib import Path
from typing import List, Tuple

from config.config_loader import Config


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
    
    def package_all(self):
        """
        Package both scam and legitimate audio files.
        """
        logger.info("Packaging audio files")
        
        # Package scam audio
        self._package_scam_audio()
        
        # Package legitimate audio
        self._package_legit_audio()
    
    def _package_scam_audio(self):
        """
        Package scam conversation audio files into a ZIP archive.
        """
        audio_dir = self.config.post_processing_scam_audio_dir
        output_path = self.config.post_processing_scam_audio_zip_output
        
        if not audio_dir.exists():
            logger.warning(f"Scam audio directory not found: {audio_dir}")
            return
        
        logger.info(f"Packaging scam audio from {audio_dir}")
        
        files_to_zip = self._collect_audio_files(audio_dir)
        
        if files_to_zip:
            self._create_zip(files_to_zip, output_path)
            logger.info(f"Packaged {len(files_to_zip)} scam audio files")
        else:
            logger.warning("No scam audio files found to package")
    
    def _package_legit_audio(self):
        """
        Package legitimate conversation audio files into a ZIP archive.
        """
        audio_dir = self.config.post_processing_legit_audio_dir
        output_path = self.config.post_processing_legit_audio_zip_output
        
        if not audio_dir.exists():
            logger.warning(f"Legitimate audio directory not found: {audio_dir}")
            return
        
        logger.info(f"Packaging legitimate audio from {audio_dir}")
        
        files_to_zip = self._collect_audio_files(audio_dir)
        
        if files_to_zip:
            self._create_zip(files_to_zip, output_path)
            logger.info(f"Packaged {len(files_to_zip)} legitimate audio files")
        else:
            logger.warning("No legitimate audio files found to package")
    
    def _collect_audio_files(self, audio_dir: Path) -> List[Tuple[Path, str]]:
        """
        Collect all final audio files from conversation subdirectories.
        
        Args:
            audio_dir: Base audio directory
            
        Returns:
            List of (file_path, archive_name) tuples
        """
        files_to_zip = []
        
        # Look for conversation subdirectories
        for subdir in audio_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith("conversation_"):
                # Look for the final processed audio file
                for pattern in ["*_final.wav", "*_with_effects.wav", "*_combined.wav"]:
                    final_files = list(subdir.glob(pattern))
                    if final_files:
                        # Use the first matching file
                        file_path = final_files[0]
                        # Create flat archive structure with descriptive names
                        archive_name = f"{subdir.name}_{file_path.name}"
                        files_to_zip.append((file_path, archive_name))
                        break
        
        logger.debug(f"Found {len(files_to_zip)} audio files to package")
        return files_to_zip
    
    def _create_zip(self, files_to_zip: List[Tuple[Path, str]], output_path: Path):
        """
        Create a ZIP archive with the specified files.
        
        Args:
            files_to_zip: List of (file_path, archive_name) tuples
            output_path: Path for the output ZIP file
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create ZIP file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, archive_name in files_to_zip:
                logger.debug(f"Adding {archive_name} to archive")
                zipf.write(file_path, archive_name)
        
        # Log file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Created ZIP archive: {output_path} ({size_mb:.1f} MB)")