"""MCP server for mtools/mlaunch - MongoDB test cluster management."""

from __future__ import annotations

import argparse
import asyncio
import json
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
]

# Global base directory, set via --dir at server startup.
# Each cluster gets its own subdirectory under this base.
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

    Combines the server-level base dir with *cluster_name*.  If
    *cluster_name* is ``None`` and no base dir was configured, raises
    ``ValueError``.
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
    timeout: int = DEFAULT_TIMEOUT,
    input_data: str | None = None,
) -> dict[str, Any]:
    """Run an mlaunch command and return structured results."""
    cmd = ["mlaunch"] + args

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if input_data else None,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(
                input=input_data.encode() if input_data else None
            ),
            timeout=timeout,
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip() if stdout_bytes else ""
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip() if stderr_bytes else ""

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
            "stderr": f"Command timed out after {timeout}s: mlaunch {' '.join(args)}",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "mlaunch not found. Please install mtools: pip install mtools",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {e}",
            "returncode": -1,
        }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def mlaunch_init(
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
    """Create and start a new MongoDB cluster (single, replica set, or sharded).

    The cluster data is stored under <base_dir>/<cluster_name>.  A random
    cluster_name is generated when none is provided.

    Args:
        topology: Cluster topology - 'single', 'replicaset', or 'sharded'.
        cluster_name: Name for the new cluster directory. Random if omitted.
        nodes: Number of data nodes in a replica set (default: 3).
        name: Replica set name.
        arbiter: Add an arbiter node to the replica set.
        priority: Enable priority-based elections in the replica set.
        sharded: Shard definitions, e.g. '2' or '2/3' (2 shards, 3 replicas each).
        config: Number of config server nodes (sharded only, default: 1).
        csrs: Use a replica set for config servers (sharded only).
        mongos: Number of mongos routers (sharded only, default: 1).
        auth: Enable authentication.
        username: Username for authentication.
        password: Password for authentication.
        auth_db: Authentication database (default: admin).
        auth_roles: Additional roles for the user (space-separated).
        port: Base port number for mongod/mongos instances.
        binarypath: Path to MongoDB binaries.
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

    # Topology flag
    if topology == "single":
        cmd_args.append("--single")
    elif topology == "replicaset":
        cmd_args.append("--replicaset")
    elif topology == "sharded":
        cmd_args.append("--sharded")
        if sharded:
            cmd_args.append(sharded)
    else:
        return f"Error: Unknown topology '{topology}'. Must be 'single', 'replicaset', or 'sharded'."

    # Replica set options
    if topology == "replicaset":
        if nodes is not None:
            cmd_args.extend(["--nodes", str(nodes)])
        if arbiter:
            cmd_args.append("--arbiter")
        if name:
            cmd_args.extend(["--name", name])
        if priority:
            cmd_args.append("--priority")

    # Sharded options
    if topology == "sharded":
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

    cmd_args.extend(["--dir", cluster_dir])

    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args, timeout=DEFAULT_TIMEOUT)

    if result["success"]:
        return (
            f"Cluster '{cluster_name}' initialized successfully.\n"
            f"Directory: {cluster_dir}\n\n"
            f"{result['stdout']}"
        )
    else:
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
        cluster_name: Name of the cluster directory. Required unless the
                      server was started with --dir and only one cluster exists.
        tags: Space-separated node tags to start. If omitted, starts all stopped nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["start"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    cmd_args.extend(["--dir", cluster_dir])
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args)

    if result["success"]:
        return f"Nodes started successfully.\n\n{result['stdout']}"
    else:
        return f"Failed to start nodes.\n\nSTDERR:\n{result['stderr']}\n\nSTDOUT:\n{result['stdout']}"


@mcp.tool()
async def mlaunch_stop(
    cluster_name: str | None = None,
    tags: str | None = None,
    verbose: bool = False,
) -> str:
    """Stop running nodes in an mlaunch cluster.

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to stop. If omitted, stops all nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["stop"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    cmd_args.extend(["--dir", cluster_dir])
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args)

    if result["success"]:
        return f"Nodes stopped successfully.\n\n{result['stdout']}"
    else:
        return f"Failed to stop nodes.\n\nSTDERR:\n{result['stderr']}\n\nSTDOUT:\n{result['stdout']}"


@mcp.tool()
async def mlaunch_restart(
    cluster_name: str | None = None,
    tags: str | None = None,
    verbose: bool = False,
) -> str:
    """Restart nodes in an mlaunch cluster (stop then start).

    Args:
        cluster_name: Name of the cluster directory.
        tags: Space-separated node tags to restart. If omitted, restarts all nodes.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["restart"]
    if tags:
        cmd_args.extend(shlex.split(tags))
    cmd_args.extend(["--dir", cluster_dir])
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args)

    if result["success"]:
        return f"Nodes restarted successfully.\n\n{result['stdout']}"
    else:
        return f"Failed to restart nodes.\n\nSTDERR:\n{result['stderr']}\n\nSTDOUT:\n{result['stdout']}"


@mcp.tool()
async def mlaunch_list(
    cluster_name: str | None = None,
    verbose: bool = False,
) -> str:
    """List all nodes in an mlaunch cluster with their status and connection info.

    Returns structured JSON output with node details including hostname, port,
    status, and role for each node.

    Args:
        cluster_name: Name of the cluster directory.
        verbose: Enable verbose output.
    """
    try:
        cluster_dir = _get_cluster_dir(cluster_name)
    except ValueError as e:
        return str(e)

    cmd_args = ["list", "--json", "--dir", cluster_dir]
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args)

    if result["success"]:
        try:
            data = json.loads(result["stdout"])
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return result["stdout"]
    else:
        return f"Failed to list nodes.\n\nSTDERR:\n{result['stderr']}\n\nSTDOUT:\n{result['stdout']}"


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
        tags: Space-separated node tags to target. If omitted, targets all nodes.
        signal: Signal to send (e.g., SIGTERM, SIGKILL, SIGINT). Default: SIGTERM.
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
    cmd_args.extend(["--dir", cluster_dir])
    if verbose:
        cmd_args.append("--verbose")

    result = await _run_mlaunch(cmd_args)

    if result["success"]:
        return f"Signal sent successfully.\n\n{result['stdout']}"
    else:
        return f"Failed to send signal.\n\nSTDERR:\n{result['stderr']}\n\nSTDOUT:\n{result['stdout']}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the mlaunch MCP server.

    Supports --dir to set a base directory.  Each cluster is created in a
    subdirectory of this base, named by the cluster_name tool parameter
    (random if omitted).
    """
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
