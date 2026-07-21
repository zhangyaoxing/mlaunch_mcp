"""Tests for mlaunch-mcp server."""

from __future__ import annotations

import json
import pytest

from mlaunch_mcp.server import (
    _resolve_base_dir,
    _get_cluster_dir,
    _run_mlaunch,
    _random_cluster_name,
)


class TestResolveBaseDir:
    def test_allowed_path_under_tmp(self, tmp_path):
        result = _resolve_base_dir(str(tmp_path))
        assert result == str(tmp_path)

    def test_disallowed_path_raises(self):
        with pytest.raises(ValueError, match="not within allowed base paths"):
            _resolve_base_dir("/etc")


class TestGetClusterDir:
    def test_combines_base_and_name(self, monkeypatch, tmp_path):
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        result = _get_cluster_dir("my-cluster")
        assert result == str(tmp_path / "my-cluster")

    def test_raises_when_no_base_dir(self, monkeypatch):
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", None)
        with pytest.raises(ValueError, match="No base directory"):
            _get_cluster_dir("some-cluster")

    def test_raises_when_cluster_name_is_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="cluster_name is required"):
            _get_cluster_dir(None)

    def test_blocks_path_traversal(self, monkeypatch, tmp_path):
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid cluster_name"):
            _get_cluster_dir("../escape")

    def test_blocks_empty_name(self, monkeypatch, tmp_path):
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid cluster_name"):
            _get_cluster_dir("")


class TestRandomClusterName:
    def test_generates_unique_names(self):
        n1 = _random_cluster_name()
        n2 = _random_cluster_name()
        assert n1 != n2
        assert n1.startswith("cluster_")
        assert len(n1) == len("cluster_") + 8  # 4 bytes hex = 8 chars


class TestRunMlaunch:
    @pytest.mark.asyncio
    async def test_list_json(self, tmp_path):
        """Test mlaunch list --json with an explicit --dir."""
        result = await _run_mlaunch(["list", "--json", "--dir", str(tmp_path)])
        if result["success"]:
            data = json.loads(result["stdout"])
            assert isinstance(data, (list, dict))
        else:
            # No cluster exists at tmp_path — this is fine
            assert result["stderr"]

    @pytest.mark.asyncio
    async def test_version(self):
        """Test mlaunch --version works."""
        result = await _run_mlaunch(["--version"])
        assert result["success"] is True
        assert "mlaunch" in result["stdout"] or "mtools" in result["stdout"]

    @pytest.mark.asyncio
    async def test_command_not_found(self):
        """Test handling of invalid flag."""
        result = await _run_mlaunch(["--nonexistent-flag-xyz"])
        assert result["success"] is False
