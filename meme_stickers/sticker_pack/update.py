"""
Pack update logic for downloading and updating sticker packs.
Handles checking for updates, downloading, and validation.
"""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime

from .models import PackManifest, HubPackInfo
from .hub import HubClient, HubError
from .pack import Pack, PackError


class UpdateError(Exception):
    """Raised when update operation fails"""
    pass


class PackUpdater:
    """Handles pack updates and downloads"""
    
    def __init__(self, hub_client: HubClient):
        """
        Initialize pack updater.
        
        Args:
            hub_client: HubClient instance for hub communication
        """
        self.hub_client = hub_client
    
    async def check_update_available(
        self,
        pack_name: str,
        current_version: Optional[str] = None,
    ) -> bool:
        """
        Check if an update is available for a pack.
        
        Args:
            pack_name: Name of the pack
            current_version: Current version of the pack
            
        Returns:
            True if update is available
            
        Raises:
            UpdateError: If check fails
        """
        try:
            hub_pack = await self.hub_client.fetch_pack_info(pack_name)
            if not hub_pack:
                return False
            
            if current_version is None:
                return True
            
            # Simple version comparison (semantic versioning)
            return self._compare_versions(hub_pack.version, current_version) > 0
        
        except HubError as e:
            raise UpdateError(f"Failed to check for updates: {e}")
    
    async def download_pack(
        self,
        pack_info: HubPackInfo,
        output_dir: Path,
        progress_callback: Optional[Callable[[str], Any]] = None,
    ) -> Path:
        """
        Download a pack from the hub.
        
        Args:
            pack_info: HubPackInfo object
            output_dir: Directory to save the downloaded file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to downloaded file
            
        Raises:
            UpdateError: If download fails
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{pack_info.name}.zip"
        
        try:
            if progress_callback:
                progress_callback(f"Downloading {pack_info.display_name}...")
            
            # Download using hub client
            await self.hub_client.download_pack(pack_info.url, str(output_file))
            
            # Verify checksum if available
            if pack_info.checksum:
                if progress_callback:
                    progress_callback("Verifying checksum...")
                
                actual_checksum = self.hub_client.calculate_checksum(str(output_file))
                if actual_checksum != pack_info.checksum:
                    output_file.unlink()
                    raise UpdateError(f"Checksum mismatch for {pack_info.name}")
            
            return output_file
        
        except UpdateError:
            raise
        except Exception as e:
            if output_file.exists():
                output_file.unlink()
            raise UpdateError(f"Failed to download pack: {e}")
    
    async def extract_pack(
        self,
        zip_path: Path,
        extract_dir: Path,
        progress_callback: Optional[Callable[[str], Any]] = None,
    ) -> Path:
        """
        Extract a pack from zip file.
        
        Args:
            zip_path: Path to zip file
            extract_dir: Directory to extract to
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to extracted pack directory
            
        Raises:
            UpdateError: If extraction fails
        """
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if progress_callback:
                progress_callback("Extracting pack...")
            
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find pack directory (top-level directory in zip)
            subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            
            if len(subdirs) == 1:
                pack_dir = subdirs[0]
            else:
                pack_dir = extract_dir
            
            return pack_dir
        
        except Exception as e:
            raise UpdateError(f"Failed to extract pack: {e}")
    
    async def install_pack(
        self,
        pack_zip: Path,
        install_dir: Path,
        pack_name: Optional[str] = None,
        progress_callback: Optional[Callable[[str], Any]] = None,
    ) -> Path:
        """
        Install a pack from zip file.
        
        Args:
            pack_zip: Path to pack zip file
            install_dir: Directory to install pack to
            pack_name: Name for the installed pack (if None, uses manifest name)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to installed pack directory
            
        Raises:
            UpdateError: If installation fails
        """
        temp_extract = install_dir / ".temp_extract"
        
        try:
            # Extract to temporary directory
            pack_dir = await self.extract_pack(pack_zip, temp_extract, progress_callback)
            
            # Validate pack
            if progress_callback:
                progress_callback("Validating pack...")
            
            pack = Pack(pack_dir)
            manifest = await pack.load_manifest()
            
            # Discover stickers
            stickers = await pack.discover_stickers()
            manifest.stickers = stickers
            
            # Determine final pack name
            final_name = pack_name or manifest.name
            final_dir = install_dir / final_name
            
            # Remove existing pack if present
            if final_dir.exists():
                shutil.rmtree(final_dir)
            
            # Move pack to final location
            if progress_callback:
                progress_callback(f"Installing {manifest.display_name}...")
            
            shutil.move(str(pack_dir), str(final_dir))
            
            # Save manifest with discovered stickers
            final_pack = Pack(final_dir)
            final_pack.manifest = manifest
            await final_pack.save_manifest()
            
            return final_dir
        
        except UpdateError:
            raise
        except Exception as e:
            raise UpdateError(f"Failed to install pack: {e}")
        
        finally:
            # Clean up temporary directory
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two semantic versions.
        
        Args:
            v1: First version string
            v2: Second version string
            
        Returns:
            Positive if v1 > v2, negative if v1 < v2, zero if equal
        """
        def parse_version(v: str) -> tuple:
            try:
                parts = [int(x) for x in v.split(".")]
                return tuple(parts)
            except (ValueError, AttributeError):
                return (0,)
        
        ver1 = parse_version(v1)
        ver2 = parse_version(v2)
        
        if ver1 > ver2:
            return 1
        elif ver1 < ver2:
            return -1
        else:
            return 0
