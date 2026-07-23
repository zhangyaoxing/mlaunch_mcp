"""Comprehensive parameter combination tests for mlaunch-mcp.

Tests all major parameter combinations of mlaunch_init and the lifecycle
tools (list, stop, start, restart, kill).

Key distinction:
- ``cluster_name``  → directory name under base dir (used by lifecycle tools)
- ``name``           → replica set name (only meaningful for replicasets)
"""

from __future__ import annotations

import itertools
import json

import pytest

from mlaunch_mcp.server import (
    mlaunch_init,
    mlaunch_list,
    mlaunch_start,
    mlaunch_stop,
    mlaunch_restart,
    mlaunch_kill,
)

# -- Constants ----------------------------------------------------------------

BINPATH_70 = "/home/yaoxing/.local/m/versions/7.0.36/bin"
BINPATH_80 = "/home/yaoxing/.local/m/versions/8.0.26/bin"

# Start from 60000 to avoid conflicts with leftover processes.
_port_counter = itertools.count(60000, 100)


# -- Fixtures -----------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_base_dir(monkeypatch, tmp_path):
    """All tests use a temp base directory."""
    monkeypatch.setattr("mlaunch_mcp.server._base_dir", str(tmp_path))


@pytest.fixture
def port():
    """Return a unique base port for this test (no collisions)."""
    return next(_port_counter)


# -- Helpers ------------------------------------------------------------------

def _assert_ok(result: str) -> None:
    """Assert that *result* string indicates success."""
    assert isinstance(result, str)
    ok = ("successfully" in result) or ("initialized successfully" in result)
    assert ok, f"Expected success, got: {result[:500]}"


def _assert_json(result: str) -> dict:
    """Assert *result* is valid JSON dict (nested role groups) and return it."""
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "mongos" in data or "shards" in data or "config" in data
    return data


def _flat_nodes(data: dict) -> list:
    """Flatten the nested mlaunch_list output to a list of all nodes."""
    nodes = list(data.get("mongos", [])) + list(data.get("config", []))
    for shard_nodes in data.get("shards", {}).values():
        nodes.extend(shard_nodes)
    return nodes


def _assert_fail(result: str) -> None:
    """Assert that *result* string indicates an error."""
    assert "Failed" in result or "Error" in result, (
        f"Expected failure, got: {result[:300]}"
    )


def _c(name: str) -> str:
    """Shortcut for cluster_name value (identity, for readability)."""
    return name


# =========================================================================
# Group 1: Basic Topologies   (port range ~40000-40800)
# =========================================================================

class TestReplicaSetBasic:
    """Replica set with minimum required parameters."""

    @pytest.mark.asyncio
    async def test_rs_default(self, port):
        """cluster_name + topology + binarypath."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_basic"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert "rs_basic" in r

    @pytest.mark.asyncio
    async def test_rs_single_node(self, port):
        """nodes=1."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_1node"),
            nodes=1,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_rs_five_nodes(self, port):
        """nodes=5."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_5node"),
            nodes=5,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)


class TestSingleNode:
    """Single-node cluster tests."""

    @pytest.mark.asyncio
    async def test_single_basic(self, port):
        r = await mlaunch_init(
            topology="single",
            cluster_name=_c("single1"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_single_mongodb_80(self, port):
        """MongoDB 8.0 binary."""
        r = await mlaunch_init(
            topology="single",
            cluster_name=_c("single80"),
            binarypath=BINPATH_80,
            port=port,
        )
        _assert_ok(r)


class TestShardedCluster:
    """Sharded cluster tests."""

    @pytest.mark.asyncio
    async def test_sharded_basic(self, port):
        """2 shards, standard."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="2",
            cluster_name=_c("ss_basic"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_sharded_csrs(self, port):
        """2 shards + csrs."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="2",
            cluster_name=_c("ss_csrs"),
            csrs=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_sharded_full(self, port):
        """csrs + config=3 + mongos=2."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="2",
            cluster_name=_c("ss_full"),
            csrs=True,
            config=3,
            mongos=2,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_sharded_1shard(self, port):
        """Single shard (sharded='1') — uses --replicaset for 3.6+."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="1",
            cluster_name=_c("ss_one"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_sharded_2x3(self, port):
        """2 shards × 3 nodes via sharded='2' + nodes=3."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="2",
            nodes=3,
            cluster_name=_c("ss_2x3"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)


# =========================================================================
# Group 2: Replica Set Options   (port range ~40800-41100)
# =========================================================================

class TestReplicaSetOptions:
    """arbiter, priority, and custom replicaset name."""

    @pytest.mark.asyncio
    async def test_arbiter(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_arb"),
            arbiter=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_priority(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_pri"),
            priority=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_arbiter_priority_combo(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_ap"),
            arbiter=True,
            priority=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_custom_rs_name(self, port):
        """Custom replica set name via 'name' param."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_named"),
            name="mySpecialRS",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert "mySpecialRS" in r


# =========================================================================
# Group 3: Auth Combinations   (port range ~41100-41600)
# =========================================================================

class TestAuth:
    """Authentication parameter combinations."""

    @pytest.mark.asyncio
    async def test_auth_default(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_auth1"),
            auth=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_auth_custom_creds(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_auth2"),
            auth=True,
            username="qa",
            password="secret",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_auth_full(self, port):
        """username + password + auth_db + auth_roles."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_auth3"),
            auth=True,
            username="admin_user",
            password="admin_pass",
            auth_db="admin",
            auth_roles="root",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_auth_multi_roles(self, port):
        """Multiple space-separated roles."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_auth4"),
            auth=True,
            username="dba",
            password="dba_pass",
            auth_roles="readWrite dbAdmin",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_auth_single(self, port):
        """Auth on single-node topology."""
        r = await mlaunch_init(
            topology="single",
            cluster_name=_c("s_auth"),
            auth=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)


# =========================================================================
# Group 4: Port & Hostname   (port range ~41600-41900)
# =========================================================================

class TestPortAndHostname:
    """Custom port and hostname parameters."""

    @pytest.mark.asyncio
    async def test_custom_port(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_p"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert str(port) in r

    @pytest.mark.asyncio
    async def test_custom_hostname(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_h"),
            hostname="localhost",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_port_and_hostname(self, port):
        """Both port and hostname on single node."""
        r = await mlaunch_init(
            topology="single",
            cluster_name=_c("s_ph"),
            hostname="localhost",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert str(port) in r


# =========================================================================
# Group 5: Random Name & Verbose   (port range ~41900-42200)
# =========================================================================

class TestRandomNameAndVerbose:
    """Random cluster name generation and verbose mode."""

    @pytest.mark.asyncio
    async def test_random_name(self, port):
        """No cluster_name → auto-generated."""
        r = await mlaunch_init(
            topology="single",
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert "cluster_" in r

    @pytest.mark.asyncio
    async def test_verbose_replicaset(self, port):
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("rs_v"),
            verbose=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_verbose_sharded(self, port):
        r = await mlaunch_init(
            topology="sharded",
            sharded="1",
            cluster_name=_c("ss_v"),
            verbose=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)


# =========================================================================
# Group 6: Lifecycle   (port range ~42200-42600)
# =========================================================================

class TestLifecycle:
    """init → list → stop → start → restart → kill."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, port):
        """Complete lifecycle on a single cluster."""
        # 1. Init
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("lc"),
            nodes=1,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

        # 2. List — all running
        data = _assert_json(await mlaunch_list(cluster_name="lc"))
        nodes = _flat_nodes(data)
        assert len(nodes) >= 1
        assert all(n["status"] == "running" for n in nodes), str(nodes)

        # 3. Stop
        _assert_ok(await mlaunch_stop(cluster_name="lc"))

        # 4. List after stop
        after_stop = await mlaunch_list(cluster_name="lc")
        if after_stop.strip():
            as_data = json.loads(after_stop)
            ns = _flat_nodes(as_data)
            if ns:
                assert all(n.get("status") != "running" for n in ns), str(ns)

        # 5. Start
        _assert_ok(await mlaunch_start(cluster_name="lc"))

        # 6. List after start — running again
        data3 = _assert_json(await mlaunch_list(cluster_name="lc"))
        nodes3 = _flat_nodes(data3)
        assert all(n["status"] == "running" for n in nodes3), str(nodes3)

        # 7. Restart
        _assert_ok(await mlaunch_restart(cluster_name="lc"))

        # 8. List after restart
        data4 = _assert_json(await mlaunch_list(cluster_name="lc"))
        nodes4 = _flat_nodes(data4)
        assert all(n["status"] == "running" for n in nodes4), str(nodes4)

        # 9. Kill SIGTERM
        _assert_ok(await mlaunch_kill(cluster_name="lc", signal="SIGTERM"))

    @pytest.mark.asyncio
    async def test_list_verbose(self, port):
        """mlaunch_list with verbose=True."""
        await mlaunch_init(
            topology="single",
            cluster_name=_c("lc_v"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_json(await mlaunch_list(cluster_name="lc_v", verbose=True))

    @pytest.mark.asyncio
    async def test_kill_signal(self, port):
        """mlaunch_kill with SIGINT."""
        await mlaunch_init(
            topology="single",
            cluster_name=_c("lc_k"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(await mlaunch_kill(cluster_name="lc_k", signal="SIGINT"))

    @pytest.mark.asyncio
    async def test_stop_start_tags(self, port):
        """stop/start with tags='all'."""
        await mlaunch_init(
            topology="single",
            cluster_name=_c("lc_t"),
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(await mlaunch_stop(cluster_name="lc_t", tags="all"))
        _assert_ok(await mlaunch_start(cluster_name="lc_t", tags="all"))


# =========================================================================
# Group 7: Validation & Errors   (port range ~42600-42800)
# =========================================================================

class TestValidationErrors:
    """Input validation and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_topology(self, port):
        assert "Error" in await mlaunch_init(topology="nonsense")

    @pytest.mark.asyncio
    async def test_sharded_no_count(self, port):
        """sharded topology without sharded count — now validated."""
        r = await mlaunch_init(
            topology="sharded",
            cluster_name=_c("no_sc"),
            binarypath=BINPATH_70,
            port=port,
        )
        assert "Error" in r and "sharded" in r.lower()

    @pytest.mark.asyncio
    async def test_list_nonexistent(self, port):
        _assert_fail(await mlaunch_list(cluster_name="nx_xyz"))

    @pytest.mark.asyncio
    async def test_stop_nonexistent(self, port):
        _assert_fail(await mlaunch_stop(cluster_name="nx_xyz"))


# =========================================================================
# Group 8: Complex Combinations   (port range ~42800-43200)
# =========================================================================

class TestComplexCombinations:
    """Multiple parameters combined."""

    @pytest.mark.asyncio
    async def test_rs_auth_port(self, port):
        """Replicaset + auth + port."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("cx_ap"),
            auth=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert str(port) in r

    @pytest.mark.asyncio
    async def test_sharded_auth_csrs(self, port):
        """Sharded + auth + csrs."""
        r = await mlaunch_init(
            topology="sharded",
            sharded="1",
            cluster_name=_c("cx_sac"),
            auth=True,
            csrs=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)

    @pytest.mark.asyncio
    async def test_single_many_params(self, port):
        """Single node + auth + username + password + verbose + port."""
        r = await mlaunch_init(
            topology="single",
            cluster_name=_c("cx_sf"),
            auth=True,
            username="sa",
            password="pw",
            verbose=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
        assert str(port) in r

    @pytest.mark.asyncio
    async def test_rs_nodes_arb_auth(self, port):
        """Replicaset + nodes=5 + arbiter + auth."""
        r = await mlaunch_init(
            topology="replicaset",
            cluster_name=_c("cx_raa"),
            nodes=5,
            arbiter=True,
            auth=True,
            binarypath=BINPATH_70,
            port=port,
        )
        _assert_ok(r)
