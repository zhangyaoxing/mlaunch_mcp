# TOOLS.md — mlaunch MCP 环境信息

_本文件记录这台机器的 MongoDB 工具链信息，便于 MCP 工具自动发现可用版本。_

## MongoDB 版本管理（m）

`m` 是一个 MongoDB 版本管理工具，类似 nvm/nvm-windows。

### 安装位置

```
~/.local/m/versions/<version>/bin/
```

### 常用命令

```bash
# 列出已安装版本（推荐用 JSON 格式）
m installed --json

# 列出可安装的版本
m ls

# 获取指定版本的二进制路径
m bin 8.0.26

# 安装一个版本
m 8.0          # 安装 8.0 系列最新
m 8.0.26       # 安装指定版本

# 切换当前使用的版本
m 8.0.26

# 直接以某版本运行 mongod/mongos
m use 8.0.26 --port 27017
m shard 8.0.26 --port 27017

# 删除版本
m rm 6.0.29

# 数据库工具
m tools stable
m tools installed --json

# MongoDB Shell
m mongosh stable
m mongosh installed --json
```

### 已安装版本

| 版本 | 路径 |
|---|---|
| 6.0.29 | `~/.local/m/versions/6.0.29/bin/` |
| 7.0.37 | `~/.local/m/versions/7.0.37/bin/` |
| 8.0.26 | `~/.local/m/versions/8.0.26/bin/` |

### 在 MCP 中使用

`mlaunch init` 的 `binarypath` 参数接受 `m bin <version>` 的输出（去掉末位的 `/bin/`），例如：

```
binarypath = /home/yaoxing/.local/m/versions/8.0.26/bin
```

`m installed --json` 可直接用于枚举可用的 `binarypath` 选项。

### 源码

- 项目主页: <https://github.com/aheckmann/m>
- Node.js 工具，通过 npm 安装
