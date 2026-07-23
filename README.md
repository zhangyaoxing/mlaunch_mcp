# mlaunch-mcp

Quickly spin up local MongoDB test clusters (single, replica set, sharded)
via [mtools/mlaunch](https://github.com/rueckstiess/mtools).

---

## Install Checklist (New Machine)

```bash
# 1. Prerequisites
npm install -g m                        # MongoDB version manager
pip install mtools                      # mlaunch CLI

# 2. Install this project
git clone git@github.com:zhangyaoxing/mlaunch_mcp.git
cd mlaunch_mcp
pip install .
```

## Requirements

- Python 3.10+
- [`m`](https://github.com/aheckmann/m) — MongoDB version manager (`npm install -g m`)
- [mtools](https://github.com/rueckstiess/mtools) (`pip install mtools`)

## Configuration

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

The `--dir` sets the base directory; each cluster is a subdirectory under it:

```
<base_dir>/
├── rs70/
│   └── data/       # mlaunch's default data directory
├── ss80/
│   └── data/
└── cluster_a1b2c3/ # auto-generated random name
    └── data/
```

If you also use the OpenClaw skill, enable it:

```json
{
  "skills": {
    "entries": {
      "mlaunch-mcp": { "enabled": true }
    }
  }
}
```

Then restart:

```bash
systemctl --user restart openclaw-gateway
```

---

## CLI Usage

This project wraps mlaunch; the underlying CLI is always available directly:

```bash
mlaunch init --replicaset --nodes 3 --port 27017 --dir /data/Workspace/mongodb/rs70
mlaunch list --dir /data/Workspace/mongodb/rs70 --json
mlaunch stop  --dir /data/Workspace/mongodb/rs70
mlaunch start --dir /data/Workspace/mongodb/rs70
```

---

## MCP Tool Reference

The MCP server exposes these tools to AI agents:

| Tool | Description |
|------|-------------|
| `mlaunch_init` | Create and start a new MongoDB cluster |
| `mlaunch_list` | List all nodes (structured JSON) |
| `mlaunch_start` | Start stopped nodes |
| `mlaunch_stop` | Stop running nodes |
| `mlaunch_restart` | Restart nodes (stop then start) |
| `mlaunch_kill` | Send a signal to nodes |

All lifecycle tools accept `cluster_name` (required) and optional `tags` to
target specific nodes.

### `mlaunch_init` — Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `topology` | string | `"single"`, `"replicaset"`, or `"sharded"` |
| `cluster_name` | string | Subdirectory name. Random when omitted. |
| `nodes` | int | Nodes per replica set (default: 3) |
| `name` | string | Replica set name |
| `sharded` | string | Number of shards, e.g. `"2"` |
| `config` | int | Config server nodes — sharded only (default: 1) |
| `csrs` | bool | Use a replica set for config servers |
| `mongos` | int | Mongos routers — sharded only (default: 1) |
| `arbiter` | bool | Add an arbiter node |
| `priority` | bool | Enable priority-based elections |
| `auth` | bool | Enable authentication |
| `username` | string | Auth username |
| `password` | string | Auth password |
| `port` | int | Base port number |
| `binarypath` | string | Path to MongoDB binaries |
| `hostname` | string | Bind hostname (default: localhost) |
| `verbose` | bool | Verbose output |

### Examples

**Replica set — 3 nodes:**

```python
mlaunch_init(
    topology="replicaset",
    cluster_name="rs70",
    name="rs70"
)
```

**Sharded cluster — 2 shards, 3 nodes each, csrs:**

```python
mlaunch_init(
    topology="sharded",
    sharded="2",
    nodes=3,
    csrs=True,
    cluster_name="ss80"
)
```

**Replica set with auth and custom port:**

```python
mlaunch_init(
    topology="replicaset",
    cluster_name="rs_auth",
    auth=True,
    port=35000
)
```

### `mlaunch_list` — Output

```json
[
  {"hostname": "localhost", "port": 27017, "role": "mongos", "status": "running"},
  {"hostname": "localhost", "port": 27024, "role": "configserver", "status": "running"},
  {"hostname": "localhost", "port": 27018, "role": "shardsvr", "status": "running", "shard": "shard01"},
  {"hostname": "localhost", "port": 27019, "role": "shardsvr", "status": "running", "shard": "shard01"},
  {"hostname": "localhost", "port": 27020, "role": "shardsvr", "status": "running", "shard": "shard01"}
]
```

---

## OpenClaw Skill

The `skills/mlaunch-mcp/` directory contains an OpenClaw skill that teaches
the AI agent how to use this MCP server.

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
