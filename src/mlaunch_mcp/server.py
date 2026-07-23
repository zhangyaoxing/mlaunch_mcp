"""MCP server for mtools/mlaunch - MongoDB test cluster management."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import shlex
import sys
from pathlib import Path
from typing import Any

from mcp.server import FastMCP

mcp = FastMCP("mlaunch")

DEFAULT_TIMEOUT = 600  # seconds

ALLOWED_BASE_DIRS = [
    Path.home() / "data",
    Path("/tmp"),
    Path("/var/tmp"),
    Path("/data"),
]

# Global base directory, set via --dir at server startup.
# Each cluster gets its own subdirectory under this base.
# pylint: disable=invalid-name  # mutable global, not a constant
_base_dir: str | None = None


def _resolve_base_dir(dir_arg: str) -> str:
    """Validate that *dir_arg* is within an allowed base path.

    Returns the resolved absolute path, or raises ValueError on failure.
    """
    resolved = Path(dir_arg).resolve()
    for base in ALLOWED_BASE_DIRS:
        base_resolved = base.resolve()
        try:
            resolved.relative_to(base_resolved)
            return str(resolved)
        except ValueError:
            continue
    raise ValueError(
        f"Directory '{dir_arg}' is not within allowed base paths: "
        f"{[str(b) for b in ALLOWED_BASE_DIRS]}"
    )


def _get_cluster_dir(cluster_name: str | None) -> str:
    """Return the absolute cluster directory for *cluster_name*.

    Combines the server-level base dir with *cluster_name*.
    Raises ``ValueError`` when neither is available.
    """
    if _base_dir is None:
        raise ValueError(
            "No base directory configured. Start the MCP server with --dir "
            "or pass cluster_name."
        )
    if cluster_name is None:
        raise ValueError(
            "cluster_name is required when no base directory is configured."
        )
    # Safety: cluster_name must be a simple directory name (no path traversal).
    name = Path(cluster_name).name
    if name != cluster_name or not name:
        raise ValueError(f"Invalid cluster_name: {cluster_name!r}")
    return str(Path(_base_dir) / name)


def _random_cluster_name() -> str:
    """Generate a short random cluster name."""
    return "cluster_" + secrets.token_hex(4)


async def _run_mlaunch(
    args: list[str],
    *,
    cwd: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    input_data: str | None = None,
) -> dict[str, Any]:
    """Run an mlaunch command and return structured results.

    If *cwd* is given, the command runs in that working directory
    (mlaunch uses its default ./data subdirectory within it).
    """
    cmd = ["mlaunch"] + args

    if cwd:
        os.makedirs(cwd, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_data else None,
            start_new_session=True,
            cwd=cwd,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(
                input=input_data.encode() if input_data else None
            ),
            timeout=timeout,
        )

        stdout = (
            stdout_bytes.decode("utf-8", errors="replace").strip()
            if stdout_bytes else ""
        )
        stderr = (
            stderr_bytes.decode("utf-8", errors="replace").strip()
            if stderr_bytes else ""
        )

        return {
            "success": proc.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "stdout": "",
            "stderr": (
                f"Command timed out after {timeout}s: "
                f"mlaunch {' '.join(args)}"
            ),
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "mlaunch not found. Install mtools: pip install mtools",
            "returncode": -1,
        }
    except (OSError, RuntimeError) as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {e}",
            "returncode": -1,
        }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

_ERR_FMT = (
    "Failed to {action}.\n\n"
    "STDERR:\n{stderr}\n\n"
    "STDOUT:\n{stdout}"
)


def _format_result(action: str, result: dict[str, Any]) -> str:
    """Format a subprocess result into a success or error string."""
    if result["success"]:
        return f"{action} successfully.\n\n{result['stdout']}"
    return _ERR_FMT.format(
        action=action.lower(),
        stderr=result["stderr"],
        stdout=result["stdout"],
    )


@mcp.tool()
async def mlaunch_init(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements,too-many-positional-arguments
    topology: str = "single",
    cluster_name: str | None = None,
    nodes: int | None = None,
    name: str | None = None,
    arbiter: bool = False,
    priority: bool = False,
    sharded: str | None = None,
    config: int | None = None,
    csrs: bool = False,
    mongos: int | None = None,
    auth: bool = False,
    username: str | None = None,
    password: str | None = None,
    auth_db: str | None = None,
    auth_roles: str | None = None,
    port: int | None = None,
    binarypath: str | None = None,
    hostname: str | None = None,
    verbose: bool = False,
) -> str:
    """Create and start a new MongoDB cluster (single, replica set, or sharded) 
    for testing purposes. Do not use for production workloads.

    The cluster data is stored under <base_dir>/<cluster_name>.  A random
    cluster_name is generated when none is provided.

    Args:
        topology: Cluster topology - 'single', 'replicaset', or 'sharded'.
        cluster_name: Name for the new cluster directory. Random if omitted.
        nodes: Number of data nodes per replica set (default: 3).
            For sharded topologies this is per-shard node count.  Combine
            with ``sharded``, e.g. ``sharded='2', nodes=3`` = 2 shards × 3.
        name: Replica set name.
        arbiter: Add an arbiter node to the replica set.
        priority: Enable priority-based elections in the replica set.
        sharded: Number of shards as a string, e.g. ``'2'`` or ``'3'``.
            Each shard is a replica set whose node count is controlled by
            the ``nodes`` parameter.  Do NOT use ``'2/3'`` — mlaunch
            interprets the slash as part of the replica set name.
        config: Number of config server nodes, sharded only (default: 1).
            When ``csrs=True``, a config server replica set of 3 nodes is
            recommended for production-like setups.
        csrs: Use a replica set for config servers (sharded only).
        mongos: Number of mongos routers (sharded only, default: 1).
        auth: Enable authentication.
        username: Username for authentication.
        password: Password for authentication.
        auth_db: Authentication database (default: admin).
        auth_roles: Additional roles for the user (space-separated).
        port: Base port number for mongod/mongos instances.
        binarypath: Directory containing mongod/mongos binaries,
            e.g. ``/path/to/8.0.26/bin/``.  Must be the bin directory,
            NOT the binary itself.
        hostname: Hostname to bind to (default: localhost).
        verbose: Enable verbose output.
    """
    if cluster_name is None:
        cluster_name = _random_cluster_name()

    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["init"]

    if topology == "single":
        cmd_args.append("--single")
        # single + sharded: each shard is a single-node replica set
        if sharded:
            cmd_args.append("--sharded")
            cmd_args.append(sharded)
    elif topology == "replicaset":
        cmd_args.append("--replicaset")
        if sharded:
            cmd_args.append("--sharded")
            cmd_args.append(sharded)
    elif topology == "sharded":
        if not sharded:
            return (
                "Error: 'sharded' parameter is required when topology='sharded'. "
                "Examples: sharded='2' (2 shards, add nodes=3 for 3 nodes per shard)."
            )
        # MongoDB 3.6+ requires shards to be replica sets.
        cmd_args.append("--replicaset")
        cmd_args.append("--sharded")
        cmd_args.append(sharded)
    else:
        return (
            f"Error: Unknown topology '{topology}'. "
            "Must be 'single', 'replicaset', or 'sharded'."
        )

    # Replica set options (apply to both replicaset and sharded topologies)
    if topology in ("replicaset", "sharded"):
        if nodes is not None:
            cmd_args.extend(["--nodes", str(nodes)])
        if arbiter:
            cmd_args.append("--arbiter")
        if name:
            cmd_args.extend(["--name", name])
        if priority:
            cmd_args.append("--priority")

    # Sharded-specific options
    if topology in ("sharded", "single") and sharded:
        if config is not None:
            cmd_args.extend(["--config", str(config)])
        if csrs:
            cmd_args.append("--csrs")
        if mongos is not None:
            cmd_args.extend(["--mongos", str(mongos)])

    # Auth options
    if auth:
        cmd_args.append("--auth")
    if username:
        cmd_args.extend(["--username", username])
    if password:
        cmd_args.extend(["--password", password])
    if auth_db:
        cmd_args.extend(["--auth-db", auth_db])
    if auth_roles:
        cmd_args.extend(["--auth-roles"] + shlex.split(auth_roles))

    # General options
    if port is not None:
        cmd_args.extend(["--port", str(port)])
    if binarypath:
        cmd_args.extend(["--binarypath", binarypath])
    if hostname:
        cmd_args.extend(["--hostname", hostname])

    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir, timeout=DEFAULT_TIMEOUT)

    if result["success"]:
        return (
            f"Cluster '{cluster_name}' initialized successfully.\n"
            f"Directory: {cluster_dir}\n\n"
            f"{result['stdout']}"
        )
    return (
        f"Failed to initialize cluster '{cluster_name}'.\n\n"
        f"STDERR:\n{result['stderr']}\n\n"
        f"STDOUT:\n{result['stdout']}"
    )


@mcp.tool()
async def mlaunch_start(
    cluster_name: str | None = None,
    tags: str | None = None,
    verbose: bool = False,
) -> str:
    """Start stopped nodes in an existing mlaunch cluster.

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to start. Omit for all stopped nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["start"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir)
    return _format_result("Nodes started", result)


@mcp.tool()
async def mlaunch_stop(
    cluster_name: str | None = None,
    tags: str | None = None,
    verbose: bool = False,
) -> str:
    """Stop running nodes in an mlaunch cluster.

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to stop. Omit for all nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["stop"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir)
    return _format_result("Nodes stopped", result)


@mcp.tool()
async def mlaunch_restart(
    cluster_name: str | None = None,
    tags: str | None = None,
    verbose: bool = False,
) -> str:
    """Restart nodes in an mlaunch cluster (stop then start).

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to restart. Omit for all nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["restart"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir)
    return _format_result("Nodes restarted", result)


@mcp.tool()
async def mlaunch_list(
    cluster_name: str | None = None,
    verbose: bool = False,
) -> str:
    """List all nodes in an mlaunch cluster with status and connection info.

    Returns structured JSON with hostname, port, status, and role per node.

    Args:
        cluster_name: Name of the cluster directory.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["list", "--json"]
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir)

    if result["success"]:
        # mlaunch list --json may prepend a version line like
        # "Detected mongod version: 7.0.36\n" before the JSON array.
        # Strip any non-JSON prefix lines before parsing.
        stdout = result["stdout"]
        try:
            data = json.loads(stdout)
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            # Try to find JSON array on a later line
            for line in stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("["):
                    try:
                        data = json.loads(stripped)
                        return json.dumps(data, indent=2)
                    except json.JSONDecodeError:
                        pass
            return stdout
    return _format_result("Nodes listed", result)


@mcp.tool()
async def mlaunch_kill(
    cluster_name: str | None = None,
    tags: str | None = None,
    signal: str | None = None,
    verbose: bool = False,
) -> str:
    """Send a signal to nodes in an mlaunch cluster.

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to target. Omit for all nodes.
        signal: Signal to send (e.g., SIGTERM, SIGKILL, SIGINT).
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["kill"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    if signal:
        cmd_args.extend(["--signal", signal])
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, cwd=cluster_dir)
    return _format_result("Signal sent", result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the mlaunch MCP server.

    Supports --dir to set a base directory.  Each cluster is created in a
    subdirectory of this base, named by the cluster_name tool parameter
    (random if omitted).
    """
    # pylint: disable=global-statement  # module-level state is intentional
    global _base_dir

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--dir", type=str, default=None,
        help="Base directory for mlaunch cluster data",
    )
    args, remaining = parser.parse_known_args()

    if args.dir:
        try:
            _base_dir = _resolve_base_dir(args.dir)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    sys.argv = [sys.argv[0]] + remaining
    mcp.run()


if __name__ == "__main__":
    main()
