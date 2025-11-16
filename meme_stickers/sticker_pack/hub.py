"""
Hub access for fetching sticker pack information and resources.
Handles HTTP communication with the pack hub server.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta

from .models import HubPackInfo

try:
    import httpx
except ImportError:
    httpx = None


class HubError(Exception):
    """Raised when hub communication fails"""
    pass


@dataclass
class GitHubSource:
    """GitHub source configuration for a pack"""
    type: Literal["github"] = "github"
    owner: str = ""
    repo: str = ""
    branch: str = "main"
    path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type,
            "owner": self.owner,
            "repo": self.repo,
            "branch": self.branch,
            "path": self.path,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GitHubSource":
        """Create GitHubSource from dictionary"""
        return GitHubSource(
            type=data.get("type", "github"),
            owner=data.get("owner", ""),
            repo=data.get("repo", ""),
            branch=data.get("branch", "main"),
            path=data.get("path", ""),
        )


@dataclass
class HubPackReference:
    """Reference to a pack in the Hub"""
    slug: str
    source: GitHubSource
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "slug": self.slug,
            "source": self.source.to_dict(),
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HubPackReference":
        """Create HubPackReference from dictionary"""
        source_data = data.get("source", {})
        source = GitHubSource.from_dict(source_data) if source_data else GitHubSource()
        
        return HubPackReference(
            slug=data.get("slug", ""),
            source=source,
        )


@dataclass
class HubIndex:
    """Index of packs available in the Hub"""
    packs: List[HubPackReference]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "packs": [pack.to_dict() for pack in self.packs],
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HubIndex":
        """Create HubIndex from dictionary"""
        if isinstance(data, list):
            packs_data = data
        else:
            packs_data = data.get("packs", [])
        
        packs = [HubPackReference.from_dict(pack_data) for pack_data in packs_data]
        
        return HubIndex(packs=packs)


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


async def fetch_hub_index(hub_url: str, client: Optional[Any] = None) -> List[HubPackReference]:
    """
    Fetch and parse the central Hub manifest.
    
    Args:
        hub_url: URL to the hub manifest.json file
        client: Optional httpx.AsyncClient to use for the request
        
    Returns:
        List of HubPackReference objects
        
    Raises:
        HubError: If communication with hub fails or JSON is invalid
    """
    if httpx is None:
        raise HubError("httpx is not installed")
    
    try:
        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=30)
            should_close_client = True
        
        try:
            response = await client.get(hub_url)
            response.raise_for_status()
            data = response.json()
            
            hub_index = HubIndex.from_dict(data)
            return hub_index.packs
        finally:
            if should_close_client:
                await client.aclose()
    
    except httpx.HTTPError as e:
        raise HubError(f"Failed to fetch hub index: {e}")
    except ValueError as e:
        raise HubError(f"Invalid JSON in hub manifest: {e}")
    except Exception as e:
        raise HubError(f"Unexpected error fetching hub index: {e}")


async def fetch_pack_manifest(source: GitHubSource, github_raw_template: str, client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Fetch a pack's manifest.json from GitHub.
    
    Args:
        source: GitHubSource configuration
        github_raw_template: Template for GitHub raw URLs
        client: Optional httpx.AsyncClient to use for the request
        
    Returns:
        Pack manifest dictionary
        
    Raises:
        HubError: If communication fails or JSON is invalid
    """
    if httpx is None:
        raise HubError("httpx is not installed")
    
    try:
        url = construct_github_raw_url(
            owner=source.owner,
            repo=source.repo,
            ref=source.branch,
            path=source.path,
            filename="metadata.json",
            template=github_raw_template,
        )
        
        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=30)
            should_close_client = True
        
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        finally:
            if should_close_client:
                await client.aclose()
    
    except httpx.HTTPError as e:
        raise HubError(f"Failed to fetch pack manifest: {e}")
    except ValueError as e:
        raise HubError(f"Invalid JSON in pack manifest: {e}")
    except Exception as e:
        raise HubError(f"Unexpected error fetching pack manifest: {e}")


def construct_github_raw_url(owner: str, repo: str, ref: str, path: str, filename: str, template: str) -> str:
    """
    Construct a GitHub raw content URL from source information.
    
    Args:
        owner: GitHub repository owner
        repo: GitHub repository name
        ref: Git reference (branch/tag/commit)
        path: Path within the repository
        filename: Filename to fetch
        template: URL template with placeholders for {owner}, {repo}, {ref}, {path}
        
    Returns:
        Constructed GitHub raw URL
    """
    full_path = f"{path}/{filename}".lstrip("/")
    url = template.format(owner=owner, repo=repo, ref=ref, path=full_path)
    return url
