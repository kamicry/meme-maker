"""Tests for Hub manifest fetching and GitHub integration."""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from meme_stickers.sticker_pack.hub import (
    GitHubSource,
    HubPackReference,
    HubIndex,
    fetch_hub_index,
    fetch_pack_manifest,
    construct_github_raw_url,
    HubError,
)


class TestGitHubSource:
    """Test GitHubSource model."""
    
    def test_github_source_creation(self):
        """Test creating a GitHubSource."""
        source = GitHubSource(
            type="github",
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            branch="main",
            path="pjsk"
        )
        assert source.type == "github"
        assert source.owner == "lgc-NB2Dev"
        assert source.repo == "meme-stickers-hub"
        assert source.branch == "main"
        assert source.path == "pjsk"
    
    def test_github_source_defaults(self):
        """Test GitHubSource with defaults."""
        source = GitHubSource()
        assert source.type == "github"
        assert source.branch == "main"
    
    def test_github_source_to_dict(self):
        """Test converting GitHubSource to dictionary."""
        source = GitHubSource(
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            branch="main",
            path="pjsk"
        )
        data = source.to_dict()
        assert data["type"] == "github"
        assert data["owner"] == "lgc-NB2Dev"
        assert data["repo"] == "meme-stickers-hub"
        assert data["branch"] == "main"
        assert data["path"] == "pjsk"
    
    def test_github_source_from_dict(self):
        """Test creating GitHubSource from dictionary."""
        data = {
            "type": "github",
            "owner": "lgc-NB2Dev",
            "repo": "meme-stickers-hub",
            "branch": "main",
            "path": "pjsk"
        }
        source = GitHubSource.from_dict(data)
        assert source.owner == "lgc-NB2Dev"
        assert source.repo == "meme-stickers-hub"
        assert source.path == "pjsk"


class TestHubPackReference:
    """Test HubPackReference model."""
    
    def test_pack_reference_creation(self):
        """Test creating a HubPackReference."""
        source = GitHubSource(owner="owner", repo="repo", path="path")
        ref = HubPackReference(slug="pjsk", source=source)
        assert ref.slug == "pjsk"
        assert ref.source.owner == "owner"
    
    def test_pack_reference_to_dict(self):
        """Test converting HubPackReference to dictionary."""
        source = GitHubSource(owner="owner", repo="repo", path="path")
        ref = HubPackReference(slug="pjsk", source=source)
        data = ref.to_dict()
        assert data["slug"] == "pjsk"
        assert data["source"]["owner"] == "owner"
    
    def test_pack_reference_from_dict(self):
        """Test creating HubPackReference from dictionary."""
        data = {
            "slug": "pjsk",
            "source": {
                "type": "github",
                "owner": "lgc-NB2Dev",
                "repo": "meme-stickers-hub",
                "branch": "main",
                "path": "pjsk"
            }
        }
        ref = HubPackReference.from_dict(data)
        assert ref.slug == "pjsk"
        assert ref.source.owner == "lgc-NB2Dev"


class TestHubIndex:
    """Test HubIndex model."""
    
    def test_hub_index_from_array(self):
        """Test creating HubIndex from array."""
        data = [
            {
                "slug": "pjsk",
                "source": {
                    "type": "github",
                    "owner": "lgc-NB2Dev",
                    "repo": "meme-stickers-hub",
                    "branch": "main",
                    "path": "pjsk"
                }
            },
            {
                "slug": "arcaea",
                "source": {
                    "type": "github",
                    "owner": "lgc-NB2Dev",
                    "repo": "meme-stickers-hub",
                    "branch": "main",
                    "path": "arcaea"
                }
            }
        ]
        hub_index = HubIndex.from_dict(data)
        assert len(hub_index.packs) == 2
        assert hub_index.packs[0].slug == "pjsk"
        assert hub_index.packs[1].slug == "arcaea"
    
    def test_hub_index_from_dict(self):
        """Test creating HubIndex from dictionary with packs key."""
        data = {
            "packs": [
                {
                    "slug": "pjsk",
                    "source": {
                        "type": "github",
                        "owner": "lgc-NB2Dev",
                        "repo": "meme-stickers-hub",
                        "branch": "main",
                        "path": "pjsk"
                    }
                }
            ]
        }
        hub_index = HubIndex.from_dict(data)
        assert len(hub_index.packs) == 1
        assert hub_index.packs[0].slug == "pjsk"
    
    def test_hub_index_to_dict(self):
        """Test converting HubIndex to dictionary."""
        source = GitHubSource(owner="owner", repo="repo", path="path")
        ref = HubPackReference(slug="pjsk", source=source)
        hub_index = HubIndex(packs=[ref])
        data = hub_index.to_dict()
        assert "packs" in data
        assert len(data["packs"]) == 1
        assert data["packs"][0]["slug"] == "pjsk"


class TestConstructGitHubRawUrl:
    """Test URL construction for GitHub raw files."""
    
    def test_construct_simple_url(self):
        """Test constructing a simple GitHub raw URL."""
        url = construct_github_raw_url(
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            ref="main",
            path="pjsk",
            filename="metadata.json",
            template="https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        )
        assert url == "https://raw.githubusercontent.com/lgc-NB2Dev/meme-stickers-hub/main/pjsk/metadata.json"
    
    def test_construct_url_with_leading_slash(self):
        """Test URL construction handles leading slashes."""
        url = construct_github_raw_url(
            owner="owner",
            repo="repo",
            ref="main",
            path="/some/path/",
            filename="file.json",
            template="https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        )
        assert "//some/path" not in url
        assert url == "https://raw.githubusercontent.com/owner/repo/main/some/path/file.json"
    
    def test_construct_url_with_custom_template(self):
        """Test URL construction with custom template."""
        url = construct_github_raw_url(
            owner="owner",
            repo="repo",
            ref="main",
            path="path",
            filename="file.json",
            template="https://mirror.example.com/{owner}/{repo}/{ref}/{path}"
        )
        assert url.startswith("https://mirror.example.com/")
        assert "owner/repo/main/path/file.json" in url


class TestFetchHubIndex:
    """Test fetch_hub_index function."""
    
    @pytest.mark.asyncio
    async def test_fetch_hub_index_success(self):
        """Test successful hub index fetch."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "slug": "pjsk",
                "source": {
                    "type": "github",
                    "owner": "lgc-NB2Dev",
                    "repo": "meme-stickers-hub",
                    "branch": "main",
                    "path": "pjsk"
                }
            }
        ]
        mock_client.get.return_value = mock_response
        
        result = await fetch_hub_index("http://example.com/manifest.json", mock_client)
        
        assert len(result) == 1
        assert result[0].slug == "pjsk"
        mock_client.get.assert_called_once_with("http://example.com/manifest.json")
    
    @pytest.mark.asyncio
    async def test_fetch_hub_index_network_error(self):
        """Test hub index fetch with network error."""
        import httpx
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Network error")
        
        with pytest.raises(HubError, match="Failed to fetch hub index"):
            await fetch_hub_index("http://example.com/manifest.json", mock_client)
    
    @pytest.mark.asyncio
    async def test_fetch_hub_index_invalid_json(self):
        """Test hub index fetch with invalid JSON."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response
        
        with pytest.raises(HubError, match="Invalid JSON"):
            await fetch_hub_index("http://example.com/manifest.json", mock_client)
    
    @pytest.mark.asyncio
    async def test_fetch_hub_index_no_client(self):
        """Test fetch_hub_index creates client if not provided."""
        with patch("meme_stickers.sticker_pack.hub.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "slug": "pjsk",
                    "source": {
                        "type": "github",
                        "owner": "lgc-NB2Dev",
                        "repo": "meme-stickers-hub",
                        "branch": "main",
                        "path": "pjsk"
                    }
                }
            ]
            mock_client.get.return_value = mock_response
            
            result = await fetch_hub_index("http://example.com/manifest.json", None)
            
            assert len(result) == 1
            mock_client.aclose.assert_called_once()


class TestFetchPackManifest:
    """Test fetch_pack_manifest function."""
    
    @pytest.mark.asyncio
    async def test_fetch_pack_manifest_success(self):
        """Test successful pack manifest fetch."""
        source = GitHubSource(
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            branch="main",
            path="pjsk"
        )
        
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "pjsk",
            "display_name": "Project SEKAI",
            "description": "Project SEKAI stickers",
            "version": "1.0.0",
            "author": "lgc"
        }
        mock_client.get.return_value = mock_response
        
        result = await fetch_pack_manifest(
            source,
            "https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}",
            mock_client
        )
        
        assert result["name"] == "pjsk"
        assert result["display_name"] == "Project SEKAI"
        mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_pack_manifest_network_error(self):
        """Test pack manifest fetch with network error."""
        import httpx
        source = GitHubSource(
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            branch="main",
            path="pjsk"
        )
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Network error")
        
        with pytest.raises(HubError, match="Failed to fetch pack manifest"):
            await fetch_pack_manifest(
                source,
                "https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}",
                mock_client
            )
    
    @pytest.mark.asyncio
    async def test_fetch_pack_manifest_invalid_json(self):
        """Test pack manifest fetch with invalid JSON."""
        source = GitHubSource(
            owner="lgc-NB2Dev",
            repo="meme-stickers-hub",
            branch="main",
            path="pjsk"
        )
        
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response
        
        with pytest.raises(HubError, match="Invalid JSON"):
            await fetch_pack_manifest(
                source,
                "https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}",
                mock_client
            )


class TestManagerGetHubPacks:
    """Test StickerPackManager.get_hub_packs method."""
    
    @pytest.mark.asyncio
    async def test_get_hub_packs(self):
        """Test getting hub packs from manager."""
        import tempfile
        from pathlib import Path
        from meme_stickers.sticker_pack.manager import StickerPackManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StickerPackManager(Path(tmpdir))
            
            with patch("meme_stickers.sticker_pack.manager.fetch_hub_index") as mock_fetch:
                source = GitHubSource(
                    owner="lgc-NB2Dev",
                    repo="meme-stickers-hub",
                    branch="main",
                    path="pjsk"
                )
                ref = HubPackReference(slug="pjsk", source=source)
                mock_fetch.return_value = [ref]
                
                result = await manager.get_hub_packs()
                
                assert len(result) == 1
                assert result[0].slug == "pjsk"
    
    @pytest.mark.asyncio
    async def test_get_hub_packs_error(self):
        """Test get_hub_packs with error."""
        import tempfile
        from pathlib import Path
        from meme_stickers.sticker_pack.manager import StickerPackManager, ManagerError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StickerPackManager(Path(tmpdir))
            
            with patch("meme_stickers.sticker_pack.manager.fetch_hub_index") as mock_fetch:
                mock_fetch.side_effect = HubError("Network error")
                
                with pytest.raises(ManagerError):
                    await manager.get_hub_packs()


class TestManagerInstallFromHub:
    """Test StickerPackManager.install_from_hub method."""
    
    @pytest.mark.asyncio
    async def test_install_from_hub_not_found(self):
        """Test install_from_hub with pack not found."""
        import tempfile
        from pathlib import Path
        from meme_stickers.sticker_pack.manager import StickerPackManager, ManagerError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StickerPackManager(Path(tmpdir))
            
            with patch("meme_stickers.sticker_pack.manager.fetch_hub_index") as mock_fetch:
                mock_fetch.return_value = []
                
                with pytest.raises(ManagerError, match="Pack not found in hub"):
                    await manager.install_from_hub("nonexistent")
    
    @pytest.mark.asyncio
    async def test_install_from_hub_error(self):
        """Test install_from_hub with error."""
        import tempfile
        from pathlib import Path
        from meme_stickers.sticker_pack.manager import StickerPackManager, ManagerError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StickerPackManager(Path(tmpdir))
            
            with patch("meme_stickers.sticker_pack.manager.fetch_hub_index") as mock_fetch:
                mock_fetch.side_effect = HubError("Network error")
                
                with pytest.raises(ManagerError):
                    await manager.install_from_hub("pjsk")
