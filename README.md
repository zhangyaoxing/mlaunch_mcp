# mlaunch-mcp

MCP (Model Context Protocol) server for [mtools/mlaunch](https://github.com/rueckstiess/mtools) — quickly spin up local MongoDB test clusters via MCP-compatible clients.

## Requirements

- Python 3.10+
- [mtools](https://github.com/rueckstiess/mtools) (`pip install mtools`)
- MongoDB binaries — managed via [`m`](https://github.com/aheckmann/m) or in PATH

## Installation

```bash
git clone git@github.com:zhangyaoxing/mlaunch_mcp.git
cd mlaunch_mcp
make venv
```

## MongoDB Version Management with `m`

[`m`](https://github.com/aheckmann/m) is a MongoDB version manager (like nvm
for Node).  It installs multiple MongoDB versions side-by-side and provides
the `--binarypath` that `mlaunch init` needs.

```bash
# Install m
npm install -g m

# Install MongoDB versions
m 7.0          # latest 7.0.x
m 8.0.26       # specific version

# List installed versions (with paths)
m installed --json
# → [{"name":"8.0.26","path":"$HOME/.local/m/versions/8.0.26/bin/"}, ...]

# Get binary path for a version
m bin 8.0.26

# Use a version
m 8.0.26
```

## MCP Client Configuration

Add to your MCP client's config (e.g. OpenClaw `~/.openclaw/openclaw.json`):

```json
{
  "mcpServers": {
    "mlaunch": {
      "command": "python",
      "args": ["-m", "mlaunch_mcp.server", "--dir", "/data/Workspace/mongodb"]
    }
  }
}
```

The `--dir` argument sets the base directory; each cluster is a subdirectory
under it.  mlaunch creates its default `data/` inside each cluster directory:

```
<base_dir>/
├── rs70/
│   └── data/       # mlaunch's default data directory
├── ss80/
│   └── data/
└── cluster_a1b2c3/ # auto-generated random name
    └── data/
```

## Available Tools

| Tool | Description |
|------|-------------|
| `mlaunch_init` | Create and start a new MongoDB cluster (single, replica set, or sharded) |
| `mlaunch_start` | Start stopped nodes in an existing cluster |
| `mlaunch_stop` | Stop running nodes in a cluster |
| `mlaunch_restart` | Restart nodes (stop then start) |
| `mlaunch_list` | List all nodes with status in structured JSON |
| `mlaunch_kill` | Send a signal to nodes |

### `mlaunch_init`

**Key parameters:**

| Parameter | Description |
|-----------|-------------|
| `topology` | `"single"`, `"replicaset"`, or `"sharded"` |
| `cluster_name` | Subdirectory name. Random name generated when omitted. |
| `nodes` | Number of data nodes per replica set (default: 3) |
| `name` | Replica set name |
| `sharded` | Shard definition, e.g. `"2"` (2 shards) or `"2/3"` (2 shards × 3 nodes each) |
| `config` | Number of config server nodes (sharded only, default: 1) |
| `csrs` | Use a replica set for config servers |
| `mongos` | Number of mongos routers (sharded only, default: 1) |
| `arbiter` | Add an arbiter node |
| `priority` | Enable priority-based elections |
| `auth` | Enable authentication |
| `username` / `password` | Auth credentials |
| `port` | Base port number |
| `binarypath` | Path to MongoDB binaries (use `m bin <version>` output) |

**Examples:**

```python
# Replica set — MongoDB 7.0, 3 nodes
mlaunch_init(
    topology="replicaset",
    cluster_name="rs70",
    name="rs70",
    binarypath="/home/user/.local/m/versions/7.0.37/bin"
)

# Sharded cluster — MongoDB 8.0, 2 shards
mlaunch_init(
    topology="sharded",
    sharded="2",
    cluster_name="ss80",
    name="ss80",
    binarypath="/home/user/.local/m/versions/8.0.26/bin"
)
```

### `mlaunch_list`

Returns structured JSON with node details:

```json
[
  {"hostname": "localhost", "port": 27017, "role": "mongos", "status": "running"},
  {"hostname": "localhost", "port": 27024, "role": "configserver", "status": "running"},
  {"hostname": "localhost", "port": 27018, "role": "shardsvr", "status": "running", "shard": "shard01"},
  {"hostname": "localhost", "port": 27019, "role": "shardsvr", "status": "running", "shard": "shard01"},
  {"hostname": "localhost", "port": 27020, "role": "shardsvr", "status": "running", "shard": "shard01"}
]
```

### Other tools

- `mlaunch_start` / `mlaunch_stop` / `mlaunch_restart` — manage cluster lifecycle
- `mlaunch_kill` — send signals (e.g. `SIGTERM`) to nodes
- All accept `cluster_name` (required) and optional `tags` to target specific nodes

## Install Checklist (New Machine)

```bash
# 1. Prerequisites
npm install -g m                    # version manager
pip install mtools                   # mlaunch
pip install -e /path/to/mlaunch_mcp # this project

# 2. Install MongoDB versions
m 7.0.37
m 8.0.26

# 3. Register MCP server in OpenClaw config (~/.openclaw/openclaw.json)
# → see "MCP Client Configuration" above

# 4. Enable skill (copy skills/mlaunch-mcp/ to OpenClaw skills path)
# → add to skills.entries in openclaw.json: "mlaunch-mcp": {"enabled": true}

# 5. Restart gateway
systemctl --user restart openclaw-gateway
```

## OpenClaw Skill

The `skills/mlaunch-mcp/` directory contains an OpenClaw skill that teaches
the AI agent how to use this MCP server with `m` for version management.

```
skills/mlaunch-mcp/
├── SKILL.md           # Triggerable skill definition
└── references/
    └── man.md         # Full m command reference
```

## Security

The combined path `<base_dir>/<cluster_name>` is resolved and validated
against allowed base directories (`~/data/`, `/tmp/`, `/var/tmp/`, `/data/`).
Path-traversal in `cluster_name` (e.g. `../escape`) is blocked.

## Development

```bash
make venv   # create venv and install dependencies
make test   # run tests
```

## License

MIT
