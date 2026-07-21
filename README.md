# mlaunch-mcp

MCP (Model Context Protocol) server for [mtools/mlaunch](https://github.com/rueckstiess/mtools) — quickly spin up local MongoDB test clusters via MCP-compatible clients.

## Requirements

- Python 3.10+
- [mtools](https://github.com/rueckstiess/mtools) installed (`pip install mtools`)
- MongoDB binaries available in PATH or specified via `--binarypath`

## Installation

```bash
git clone https://github.com/<your-repo>/mlaunch-mcp.git
cd mlaunch_mcp
uv venv && uv pip install -e .
```

## MCP Client Configuration

Add to your MCP client's configuration:

```json
{
  "mcpServers": {
    "mlaunch": {
      "command": "/path/to/mlaunch_mcp/.venv/bin/python",
      "args": ["-m", "mlaunch_mcp.server", "--dir", "/tmp/my-clusters"]
    }
  }
}
```

The `--dir` startup argument sets a **base** directory.  Each cluster is
created in its own subdirectory under this base:

```
<base_dir>/
├── my-cluster/     # cluster_name = "my-cluster"
├── staging/        # cluster_name = "staging"
└── cluster_a1b2c3d4/  # auto-generated random name
```

## Available Tools

| Tool | Description |
|------|-------------|
| `mlaunch_init` | Create and start a new MongoDB cluster (single, replica set, or sharded) |
| `mlaunch_start` | Start stopped nodes in an existing cluster |
| `mlaunch_stop` | Stop running nodes in a cluster |
| `mlaunch_restart` | Restart nodes (stop then start) |
| `mlaunch_list` | List all nodes with status and connection info (structured JSON) |
| `mlaunch_kill` | Send a signal to nodes |

All tools accept a **`cluster_name`** parameter that identifies which
subdirectory to use.  It is combined with the server-level `--dir` base.

### Tool Details

#### `mlaunch_init`

Create and start a new MongoDB cluster.

Key parameters:
- **`cluster_name`**: Subdirectory name for the cluster.  A random name
  (e.g. `cluster_a1b2c3d4`) is generated when omitted.
- `topology`: `"single"`, `"replicaset"`, or `"sharded"`
- `nodes`: Number of data nodes (replica set, default: 3)
- `name`: Replica set name
- `arbiter`: Add an arbiter node
- `auth`: Enable authentication
- `username` / `password`: Auth credentials
- `port`: Base port number
- `binarypath`: Path to MongoDB binaries

#### `mlaunch_list`

Returns structured JSON with node details.  Example:
```json
{
  "nodes": [
    {
      "name": "rs0/primary",
      "hostname": "localhost",
      "port": 27017,
      "role": "primary",
      "status": "running"
    }
  ]
}
```

#### Other tools (`mlaunch_start`, `mlaunch_stop`, `mlaunch_restart`, `mlaunch_kill`)

- **`cluster_name`**: (required) Identifies the cluster to operate on.
- `tags`: Space-separated node tags to target (omit for all nodes).
- `verbose`: Enable verbose output.
- `mlaunch_kill` also accepts `signal` (e.g. `SIGTERM`, `SIGKILL`).

## Security

The combined path `<base_dir>/<cluster_name>` is always resolved and
validated against allowed base directories:

- `~/data/`
- `/tmp/`
- `/var/tmp/`

Path-traversal in `cluster_name` (e.g. `../escape`) is blocked.

## Development

```bash
# Install dev dependencies
uv pip install pytest pytest-asyncio

# Run tests
.venv/bin/python -m pytest tests/ -v
```

## License

MIT
