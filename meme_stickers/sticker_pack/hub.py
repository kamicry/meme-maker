"""
Hub access for fetching sticker pack information and resources.
Handles HTTP communication with the pack hub server.
"""

import asyncio
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .models import HubPackInfo

try:
    import httpx
except ImportError:
    httpx = None


class HubError(Exception):
    """Raised when hub communication fails"""
    pass


class HubClient:
    """Client for communicating with the sticker pack hub"""
    
    def __init__(self, hub_url: str, timeout: int = 30, cache_ttl: int = 3600):
        """
        Initialize hub client.
        
        Args:
            hub_url: Base URL of the hub server
            timeout: Request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
        """
        self.hub_url = hub_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._pack_cache: Optional[List[HubPackInfo]] = None
        self._cache_time: Optional[datetime] = None
    
    async def fetch_packs(self, force_refresh: bool = False) -> List[HubPackInfo]:
        """
        Fetch list of available packs from hub.
        
        Args:
            force_refresh: Force refresh cache
            
        Returns:
            List of HubPackInfo objects
            
        Raises:
            HubError: If communication with hub fails
        """
        # Check cache
        if not force_refresh and self._pack_cache is not None:
            if self._cache_time is not None:
                age = datetime.now() - self._cache_time
                if age < timedelta(seconds=self.cache_ttl):
                    return self._pack_cache
        
        if httpx is None:
            raise HubError("httpx is not installed")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.hub_url}/packs")
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "success":
                    raise HubError(f"Hub returned error: {data.get('error', 'Unknown error')}")
                
                packs = [
                    HubPackInfo.from_dict(pack_data)
                    for pack_data in data.get("packs", [])
                ]
                
                # Update cache
                self._pack_cache = packs
                self._cache_time = datetime.now()
                
                return packs
        
        except httpx.HTTPError as e:
            raise HubError(f"Failed to fetch packs from hub: {e}")
        except Exception as e:
            raise HubError(f"Unexpected error fetching packs: {e}")
    
    async def fetch_pack_info(self, pack_name: str, force_refresh: bool = False) -> Optional[HubPackInfo]:
        """
        Fetch information about a specific pack.
        
        Args:
            pack_name: Name of the pack
            force_refresh: Force refresh cache
            
        Returns:
            HubPackInfo or None if not found
        """
        packs = await self.fetch_packs(force_refresh=force_refresh)
        for pack in packs:
            if pack.name == pack_name:
                return pack
        return None
    
    async def download_pack(self, url: str, output_path: str) -> str:
        """
        Download a pack from URL.
        
        Args:
            url: URL to download from
            output_path: Path to save the file to
            
        Returns:
            Path to downloaded file
            
        Raises:
            HubError: If download fails
        """
        if httpx is None:
            raise HubError("httpx is not installed")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                return output_path
        
        except httpx.HTTPError as e:
            raise HubError(f"Failed to download pack: {e}")
        except Exception as e:
            raise HubError(f"Unexpected error downloading pack: {e}")
    
    async def fetch_remote_manifest(self, url: str) -> Dict[str, Any]:
        """
        Fetch a manifest from a remote URL.
        
        Args:
            url: URL to manifest JSON file
            
        Returns:
            Manifest dictionary
            
        Raises:
            HubError: If fetch fails
        """
        if httpx is None:
            raise HubError("httpx is not installed")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPError as e:
            raise HubError(f"Failed to fetch manifest: {e}")
        except Exception as e:
            raise HubError(f"Unexpected error fetching manifest: {e}")
    
    def calculate_checksum(self, file_path: str, algorithm: str = "md5") -> str:
        """
        Calculate checksum for a file.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha1, sha256)
            
        Returns:
            Hex digest of file
        """
        if algorithm == "md5":
            hash_obj = hashlib.md5()
        elif algorithm == "sha1":
            hash_obj = hashlib.sha1()
        elif algorithm == "sha256":
            hash_obj = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def clear_cache(self) -> None:
        """Clear the pack cache"""
        self._pack_cache = None
        self._cache_time = None
