"""Tests for mlaunch-mcp server."""

from __future__ import annotations

import json

import pytest

from mlaunch_mcp.server import (
    _resolve_base_dir,
    _get_cluster_dir,
    _run_mlaunch,
    _random_cluster_name,
    _format_result,
)


class TestResolveBaseDir:
    """Tests for _resolve_base_dir path validation."""

    def test_allowed_path_under_tmp(self, tmp_path):
        """A path under tmp should be accepted."""
        result = _resolve_base_dir(str(tmp_path))
        assert result == str(tmp_path)

    def test_disallowed_path_raises(self):
        """A path outside allowed dirs should raise ValueError."""
        with pytest.raises(ValueError, match="not within allowed base paths"):
            _resolve_base_dir("/etc")


class TestGetClusterDir:
    """Tests for _get_cluster_dir combining base dir + cluster name."""

    def test_combines_base_and_name(self, monkeypatch, tmp_path):
        """Should join base_dir and cluster_name."""
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        result = _get_cluster_dir("my-cluster")
        assert result == str(tmp_path / "my-cluster")

    def test_raises_when_no_base_dir(self, monkeypatch):
        """Should raise when _base_dir is None."""
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", None)
        with pytest.raises(ValueError, match="No base directory"):
            _get_cluster_dir("some-cluster")

    def test_raises_when_cluster_name_is_none(self, monkeypatch, tmp_path):
        """Should raise when cluster_name is None."""
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="cluster_name is required"):
            _get_cluster_dir(None)

    def test_blocks_path_traversal(self, monkeypatch, tmp_path):
        """Path traversal in cluster_name should be rejected."""
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid cluster_name"):
            _get_cluster_dir("../escape")

    def test_blocks_empty_name(self, monkeypatch, tmp_path):
        """Empty cluster_name should be rejected."""
        monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))
        with pytest.raises(ValueError, match="Invalid cluster_name"):
            _get_cluster_dir("")


class TestRandomClusterName:
    """Tests for random cluster name generation."""

    # pylint: disable=too-few-public-methods

    def test_generates_unique_names(self):
        """Consecutive calls should return distinct names."""
        n1 = _random_cluster_name()
        n2 = _random_cluster_name()
        assert n1 != n2
        assert n1.startswith("cluster_")
        assert len(n1) == len("cluster_") + 8  # 4 bytes hex = 8 chars


class TestFormatResult:
    """Tests for _format_result helper."""

    def test_success(self):
        """Should include 'successfully' and stdout on success."""
        result = {"success": True, "stdout": "ok", "stderr": ""}
        out = _format_result("Nodes started", result)
        assert "successfully" in out
        assert "ok" in out

    def test_failure(self):
        """Should include 'Failed' and stderr on failure."""
        result = {"success": False, "stdout": "", "stderr": "boom"}
        out = _format_result("Nodes stopped", result)
        assert "Failed" in out
        assert "boom" in out


class TestRunMlaunch:
    """Integration tests that shell out to the real mlaunch binary."""

    @pytest.mark.asyncio
    async def test_list_json(self, tmp_path):
        """mlaunch list --json should return JSON or a clear error."""
        result = await _run_mlaunch(
            ["list", "--json", "--dir", str(tmp_path)]
        )
        if result["success"]:
            data = json.loads(result["stdout"])
            assert isinstance(data, (list, dict))
        else:
            assert result["stderr"]

    @pytest.mark.asyncio
    async def test_version(self):
        """mlaunch --version exits successfully."""
        result = await _run_mlaunch(["--version"])
        assert result["success"] is True
        assert "mlaunch" in result["stdout"] or "mtools" in result["stdout"]

    @pytest.mark.asyncio
    async def test_command_not_found(self):
        """Invalid flags produce a failure result."""
        result = await _run_mlaunch(["--nonexistent-flag-xyz"])
        assert result["success"] is False
