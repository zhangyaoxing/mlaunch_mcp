---
name: mlaunch-mcp
description: "Manage MongoDB clusters (single/replicaset/sharded) via mlaunch with `m`-managed binaries. Use when the user asks about mlaunch, mongod, mongos, creating/starting/stopping/managing MongoDB clusters, replica sets, or sharded clusters."
---

# mlaunch MCP Skill

Use `mlaunch init` (through the MCP tool) to create local MongoDB clusters.
`binarypath` comes from `m` — a MongoDB version manager similar to nvm.

## Workflow

### 1. Discover installed versions

```bash
m installed --json
```

Returns a JSON array like:
```json
[
  {"name": "8.0.26", "path": "$HOME/.local/m/versions/8.0.26/bin/"},
  {"name": "7.0.37", "path": "$HOME/.local/m/versions/7.0.37/bin/"},
  {"name": "6.0.20", "path": "$HOME/.local/m/versions/6.0.20/bin/"}
]
```

The `path` value is exactly what `binarypath` needs.

### 2. Install a version (if not already installed)

Non-interactive install (use `M_CONFIRM=0` to skip prompt):

```bash
M_CONFIRM=0 m 8.0.26        # specific version
M_CONFIRM=0 m 7.0           # latest in 7.0 series
```

### 3. Create a cluster

**Replica set (3 nodes, default):**

```
mlaunch__mlaunch_init(
    topology="replicaset",
    name="rs70",
    binarypath="<m path>"
)
```

**Replica set with auth and custom node count:**

```
mlaunch__mlaunch_init(
    topology="replicaset",
    name="rs_60",
    nodes=5,
    auth=True,
    binarypath="<m path>"
)
```

Default auth credentials: `user` / `password`.

**Sharded cluster (2 shards, each a 3-node replica set):**

```
mlaunch__mlaunch_init(
    topology="sharded",
    sharded="2",
    name="ss80",
    binarypath="<m path>"
)
```

### 4. Manage clusters

```bash
mlaunch list --dir <cluster_dir>   # list nodes & status
mlaunch stop --dir <cluster_dir>    # stop all nodes
mlaunch start --dir <cluster_dir>   # start stopped nodes
mlaunch restart --dir <cluster_dir> # restart nodes
```

### 5. Clean up

```bash
mlaunch stop --dir <cluster_dir>
rm -rf <cluster_dir>
```

Or remove a version from `m`:

```bash
m rm <version>
```

## Conventions

- Cluster directories live under the server's `--dir`
- Cluster name doubles as directory name for discoverability
- MCP server must be restarted after code changes to pick up new logic
- `binarypath` is the **directory** containing `mongod`/`mongos`, not the binary itself
- `m` prompts for install confirmation by default (`CONFIRM=1`); use `M_CONFIRM=0` env var to skip in non-interactive/scripted use

## References

See `references/man.md` for full `m` command reference.
