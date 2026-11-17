# Upstream status

Baseline checked on 2026-11-17.

| Source | Baseline | Handling |
| --- | --- | --- |
| [Yeqingky/monitor-agent-win](https://github.com/Yeqingky/monitor-agent-win) | 1.2.3 / eb0d281d24be | Full Windows source and history retained |
| [monitor-probe/agent](https://github.com/monitor-probe/agent) | 1.2.4 / d6f1f498d3c9 | Protocol reference; Linux collection code is not copied |
| [monitor-probe/monitor](https://github.com/monitor-probe/monitor) | 2840c7b07735 | Current hello/report/ping.tasks/ping.result protocol checked |

The binary reports version 1.2.3, matching the Windows upstream base.
The ARM64 adaptation is identified by the repository commit in BUILD-INFO.json.

ARM64 changes are restricted to architecture-dependent virtualization detection.
Unrecognised firmware can report virt=none; this does not stop collection or reporting.
No live connection to the user's Oracle instance or Hub has been performed.

Sync upstream checks the three main branches daily, prepares a real merge for
Windows changes, runs CI on the exact candidate, then opens a PR.
Linux agent and Hub changes are tracked for manual review; observing them is not
a claim that all future protocol changes are compatible.
