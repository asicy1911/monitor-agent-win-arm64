# Monitor Agent · Windows ARM64

用于甲骨文云 Ampere 等 **Windows ARM64** 主机的 Monitor 探针。
基于 [Yeqingky/monitor-agent-win](https://github.com/Yeqingky/monitor-agent-win)
完整 Windows 实现，参考 [官方 agent](https://github.com/monitor-probe/agent)
与 [Hub](https://github.com/monitor-probe/monitor) 协议。保留上游 Git 历史和 MIT 许可。

**主产物：`monitor-agent-aarch64-pc-windows-msvc.zip`。**
这是 ARM64 原生程序，不需要 x64 模拟、Rust、Python、PowerShell 定时采集或第三方服务包装器。
PowerShell 仅用于可选安装脚本，服务和采集由 exe 自身完成。

## GitHub 云编译

推送或合并到 `main` 后会自动运行 **Build Windows**，先验证再生成程序包。
也可以按下面步骤手动重建。

1. 在本仓库打开 **Actions → Build Windows → Run workflow**，选择 `main`。
2. 保持 `publish` 不勾选，运行。
3. 工作流先验证再编译。完成后在运行页面下方 **Artifacts** 下载
   `monitor-agent-aarch64-pc-windows-msvc`。
4. 解开 GitHub 的 artifact 外层 ZIP，再解开里面同名的程序 ZIP；
   得到 `monitor-agent.exe`、`Install.ps1`、`BUILD-INFO.json` 等文件。

| 主机系统 | 选择的程序包 |
| --- | --- |
| Windows ARM64（甲骨文 Ampere） | `monitor-agent-aarch64-pc-windows-msvc.zip` |
| Windows x64 | `monitor-agent-x86_64-pc-windows-msvc.zip` |
| Windows x64，兼容原上游 GNU 命名 | `monitor-agent-x86_64-pc-windows-gnu.zip` |

CI 使用 `windows-11-arm` 对 ARM64 做原生编译、单元测试、实际 WebSocket
上报/TCP 探测/重连测试和 Windows 服务安装/升级测试。
MSVC 产物静态链接 CRT，不要求用户安装 Visual C++ Redistributable。
GitHub 托管 ARM64 runner 的可用性与费用以账号和 GitHub 当前规则为准。

## 在甲骨文 Windows 上安装

先在 Hub 后台新建一个节点，复制该节点的 token。
Hub 后台生成的 Linux `curl | sh` 命令不能直接在 Windows 执行；
使用同一条命令中的 `--server` 和 `--token` 即可。

在程序解压目录打开**管理员 PowerShell**：

```powershell
.\monitor-agent.exe install --server "https://你的面板域名" --token "该节点Token"
.\monitor-agent.exe status
```

或使用会检查程序架构的安装脚本：

```powershell
.\Install.ps1 -Server "https://你的面板域名" -Token "该节点Token"
```

- 安装器复制程序到 `%ProgramData%\monitor-agent\monitor-agent.exe`。
- token 写入受 ACL 保护的 `agent.env`，仅 SYSTEM 和 Administrators 可访问。
- 注册 Windows 服务，延迟自动启动，失败后自动重启。
- 不需要在 Windows 安装 Hub，也不需要为 agent 开入站端口；它主动连接 Hub。
- `--server` 填 Hub 基础地址，不能加 `/api/agent/ws`。
- 配置文件、token、日志不要提交到 GitHub。

默认拒绝连接远程明文 HTTP。Hub 确实只配置了 HTTP 时显式添加 `--insecure`：

```powershell
.\monitor-agent.exe install --server "http://服务器IP:28080" --token "该节点Token" --insecure
```

若 1Panel 把 Hub 仅绑定在 `127.0.0.1:28080`，Windows 应连接反向代理后的
HTTPS 域名。反向代理需要允许 WebSocket。

## 常用操作

```powershell
# 下载新版到另一个目录后，保留原配置升级
.\monitor-agent.exe install

# 修改统计网卡；名称精确匹配 adapter alias
netsh.exe interface show interface
.\monitor-agent.exe install --iface "Ethernet"

.\monitor-agent.exe start
.\monitor-agent.exe stop
.\monitor-agent.exe status
.\monitor-agent.exe uninstall

# 查看日志
Get-Content "$env:ProgramData\monitor-agent\agent.log" -Tail 60
```

升级请运行新解压目录中的 exe；服务运行中的副本由安装器替换。
卸载会保留配置。使用 `--service-name monitor-agent-backup` 可安装独立实例。
其他参数和行为见 [Windows 上游说明](https://github.com/Yeqingky/monitor-agent-win#安装和运行)。

## 跟进上游

**Actions → Sync upstream → Run workflow** 可立即检查；默认每天北京时间 10:23 检查一次。

| 上游 | 检查后的处理 |
| --- | --- |
| Windows agent | 执行 Git merge；ARM64/x64 CI 全部通过后，向本仓库提交 PR |
| 官方 Linux agent | 记录提交与对比链接，供核对协议；不覆盖 Windows 采集代码 |
| 官方 Hub | 记录提交与对比链接，供核对协议 |

首次使用自动 PR，在 **Settings → Actions → General → Workflow permissions**
勾选 **Allow GitHub Actions to create and approve pull requests**。
若组织策略不允许，可下载工作流中的 `upstream-candidate` 并本地处理。
工作流按 job 申请最少权限，不需要配置个人 PAT。

处理更新时：

1. 查看自动 PR 中的比较链接及 [UPSTREAM-STATUS.md](UPSTREAM-STATUS.md)。
2. 正常 PR 的候选提交已经通过同一次 Sync upstream 运行中的三平台 CI。
   GitHub 默认 token 创建的 PR 不一定再次触发 PR CI；这不影响此前的候选验证。
3. 审阅后合并。保留 merge commit，**不要 squash 或 rebase 这类上游同步 PR**，
   否则会丢失已合入上游的父提交关系。
4. 在 `main` 运行 **Build Windows**，下载新程序执行 `install` 升级。

有冲突时自动取消 source merge，生成 draft PR 和 `conflicts.patch`；
**draft 跟踪 PR 不能当作新 agent 版本直接合并**。需先解决冲突并重新验证。
检查/测试失败时不会向主分支写入或自动发布。

本地跟进 Windows 上游：

```bash
git remote add upstream-windows https://github.com/Yeqingky/monitor-agent-win.git
git fetch upstream-windows main
git switch -c update/windows-upstream
git merge upstream-windows/main
# 解决冲突、验证后推送分支，并创建 PR
```

具体基线、已观察版本及兼容性限制记录在
[upstream-lock.json](upstream-lock.json) 和 [UPSTREAM-STATUS.md](UPSTREAM-STATUS.md)。
观察到新 Linux/Hub 版本不代表已自动完成它的 Windows 移植。

## 发布到 Releases

普通手动构建仅产出 Artifacts。正式发布时，tag 必须等于 `v` + `Cargo.toml` 的版本。
当前基线为 `1.2.3`，第一次可执行：

```bash
git tag v1.2.3
git push origin v1.2.3
```

推送 tag 会运行验证、编译并创建 Release，附三种架构程序、ZIP、
构建信息和 `sha256sums.txt`。重复发布同一 tag 不会覆盖既有 Release。
下载后可用 `Get-FileHash 文件名 -Algorithm SHA256` 核对校验值。

## 采集与限制

沿用 Windows 上游的 CPU、内存、page file、固定磁盘、流量计数、
TCP/UDP、进程、uptime、IP、TCP 延迟探测、重连和服务管理。
`Facts` / `Metrics` 及 JSON-RPC 方法名保持不变。

ARM64 上不调用 x86 CPUID，改从 Windows 固件标识尽力判断虚拟化类型。
未知固件会显示 `virt=none`，不影响其他监控。CPU 名称来自 Windows 注册表，
个别镜像可能只提供通用名称；本分支不会把所有 Oracle 机器强行标为 KVM。

Windows 的 load 是根据 CPU 使用率平滑得到的近似值，不等同于 Linux 内核 load。
流量统计取所选网卡计数器，由 Hub 负责累加，保留重启和网卡集合变化的识别逻辑。

GitHub runner 测试不能代替你实际的甲骨文镜像与 Hub 联机验收。
首次安装后确认节点在线、CPU/内存/流量变化、延迟探测及重启后自启动。

## 本地开发

需要 Rust stable、MSVC 与对应的 Windows SDK/ARM64 C++ 工具链：

```powershell
rustup target add aarch64-pc-windows-msvc
$env:RUSTFLAGS = "-C target-feature=+crt-static"
cargo fmt --all --check
cargo check --locked --target aarch64-pc-windows-msvc
cargo clippy --locked --target aarch64-pc-windows-msvc --all-targets -- -D warnings
cargo test --locked --target aarch64-pc-windows-msvc
cargo build --release --locked --target aarch64-pc-windows-msvc
```

MIT；保留 stqfdyr 和 Yeqingky 的原版权信息。
