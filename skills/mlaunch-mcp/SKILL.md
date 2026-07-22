---
name: mlaunch-mcp
description: "Manage MongoDB clusters (single/replicaset/sharded) via mlaunch with `m`-managed binaries."
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
  {"name": "6.0.29", "path": "$HOME/.local/m/versions/6.0.29/bin/"}
]
```

The `path` value is exactly what `binarypath` needs.

### 2. Create a cluster

**Replica set (3 nodes, default):**

```
mlaunch__mlaunch_init(
    topology="replicaset",
    name="rs70",
    binarypath="<m path>"
)
```

**Sharded cluster (2 shards, each a 3-node replica set):**

```
mlaunch__mlaunch_init(
    topology="sharded",
    sharded="2",
    name="ss80",
    binarypath="<m path>"
)
```

### 3. Manage clusters

```bash
mlaunch list --dir <cluster_dir>   # list nodes & status
mlaunch stop --dir <cluster_dir>    # stop all nodes
mlaunch start --dir <cluster_dir>   # start stopped nodes
mlaunch restart --dir <cluster_dir> # restart nodes
```

### 4. Clean up

```bash
mlaunch stop --dir <cluster_dir>
rm -rf <cluster_dir>
```

Or remove a version from `m`:

```bash
m rm <version>
```

## Conventions

- Cluster directories live under the server's `--dir` (default: `/data/Workspace/mongodb/`)
- Cluster name doubles as directory name for discoverability
- MCP server must be restarted after code changes to pick up new logic
- `binarypath` is the **directory** containing `mongod`/`mongos`, not the binary itself

## References

See `man/TOOLS.md` for `m` command reference.
