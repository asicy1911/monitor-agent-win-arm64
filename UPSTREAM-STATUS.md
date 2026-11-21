# Upstream status

Windows changes are merged into a candidate branch and tested before a PR is opened.
Official Linux agent and Hub commits are tracked for manual protocol review.

| Source | Latest observed commit | Handling |
| --- | --- | --- |
| [Yeqingky/monitor-agent-win](https://github.com/Yeqingky/monitor-agent-win) | [eb0d281d24be](https://github.com/Yeqingky/monitor-agent-win/commit/eb0d281d24be163e818c1905a0ba7a08c4b5e353) | merged Windows source |
| [monitor-probe/agent](https://github.com/monitor-probe/agent) | [9986559bbe38](https://github.com/monitor-probe/agent/commit/9986559bbe38d5bc447ba08f98307e907c663cbd) | tracking only; review protocol changes |
| [monitor-probe/monitor](https://github.com/monitor-probe/monitor) | [df5e4b4beecd](https://github.com/monitor-probe/monitor/commit/df5e4b4beecde965f0ee4f1eb82e14d03942d90f) | tracking only; review protocol changes |

## Changes in this check

- [monitor-probe/agent: compare](https://github.com/monitor-probe/agent/compare/d6f1f498d3c98b68a4794b736a65c2c334fd488a...9986559bbe38d5bc447ba08f98307e907c663cbd)
- [monitor-probe/monitor: compare](https://github.com/monitor-probe/monitor/compare/2840c7b07735771b043c5a824c31e6eb435d0f56...df5e4b4beecde965f0ee4f1eb82e14d03942d90f)

ARM64 remains aarch64-pc-windows-msvc; retain the conditional CPUID handling.
The candidate runs the same ARM64, x64 MSVC and x64 GNU checks as normal CI.
Merging an observation-only update does not mean the Linux changes have been ported.
