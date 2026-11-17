"""Prepare a real Git merge for CI; only a later job can push the candidate."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPOS = {
    'windows': 'Yeqingky/monitor-agent-win',
    'official_agent': 'monitor-probe/agent',
    'hub': 'monitor-probe/monitor',
}


def git(root, *args, check=True):
    return subprocess.run(['git', *args], cwd=root, check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def output(name, value):
    text = str(value).lower() if isinstance(value, bool) else str(value)
    print(f'{name}={text}')
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            stream.write(f'{name}={text}\n')


def prepare(root, destination, remotes=None):
    remotes = remotes or {key: f'https://github.com/{repo}.git' for key, repo in REPOS.items()}
    if git(root, 'status', '--porcelain').stdout:
        raise RuntimeError('Upstream preparation requires a clean checkout')
    state_path = root / 'upstream-lock.json'
    state = json.loads(state_path.read_text(encoding='utf-8'))
    heads = {}
    for key, remote in remotes.items():
        line = git(root, 'ls-remote', '--exit-code', remote, 'refs/heads/main').stdout
        heads[key] = line.split()[0]
        if len(heads[key]) != 40 or any(c not in '0123456789abcdef' for c in heads[key]):
            raise RuntimeError('Invalid Git commit')
    changed = [key for key in REPOS if heads[key] != state[key]['commit']]
    if not changed:
        output('changed', False)
        output('conflict', False)
        return False, False
    destination.mkdir(parents=True, exist_ok=True)
    git(root, 'config', 'user.name', 'github-actions[bot]')
    git(root, 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    conflicts = []
    if 'windows' in changed:
        git(root, 'fetch', '--no-tags', '--no-recurse-submodules', remotes['windows'], heads['windows'])
        merge = git(root, 'merge', '--no-ff', '--no-edit', heads['windows'], check=False)
        if merge.returncode:
            conflicts = git(root, 'diff', '--name-only', '--diff-filter=U').stdout.splitlines()
            if not conflicts:
                raise RuntimeError(f'Git merge failed: {merge.stderr}')
            (destination / 'conflicts.patch').write_text(git(root, 'diff', '--cc').stdout, encoding='utf-8')
            git(root, 'merge', '--abort')
        else:
            state['windows']['commit'] = heads['windows']
    # Linux source is observed, never copied over the Windows collector.
    for key in ('official_agent', 'hub'):
        state[key]['commit'] = heads[key]
    report = [
        '# Upstream status', '',
        'Windows changes are merged into a candidate branch and tested before a PR is opened.',
        'Official Linux agent and Hub commits are tracked for manual protocol review.', '',
        '| Source | Latest observed commit | Handling |',
        '| --- | --- | --- |',
    ]
    for key, repo in REPOS.items():
        handling = 'merge blocked: resolve conflicts' if key == 'windows' and conflicts else (
            'merged Windows source' if key == 'windows' else 'tracking only; review protocol changes')
        report.append(f'| [{repo}](https://github.com/{repo}) | [{heads[key][:12]}](https://github.com/{repo}/commit/{heads[key]}) | {handling} |')
    report.extend(['', '## Changes in this check', ''])
    for key in changed:
        # Previous main-branch lock state is still available in HEAD even after the source merge.
        old = json.loads(git(root, 'show', 'HEAD:upstream-lock.json').stdout)[key]['commit']
        repo = REPOS[key]
        report.append(f'- [{repo}: compare](https://github.com/{repo}/compare/{old}...{heads[key]})')
    if conflicts:
        report.extend(['', '## Windows merge conflicts', '',
                       'Source changes were aborted. This is a draft tracking PR; do not merge it as an agent upgrade.', ''])
        report.extend(f'- `{path}`' for path in conflicts)
        report.extend(['', 'Download conflicts.patch from the upstream-candidate workflow artifact,',
                       'or merge the Windows commit locally and resolve it before building.'])
    report.extend(['', 'ARM64 remains aarch64-pc-windows-msvc; retain the conditional CPUID handling.',
                   'The candidate runs the same ARM64, x64 MSVC and x64 GNU checks as normal CI.',
                   'Merging an observation-only update does not mean the Linux changes have been ported.', ''])
    text = '\n'.join(report)
    (root / 'UPSTREAM-STATUS.md').write_text(text, encoding='utf-8')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    git(root, 'add', 'upstream-lock.json', 'UPSTREAM-STATUS.md')
    if git(root, 'diff', '--cached', '--quiet', check=False).returncode:
        git(root, 'commit', '-m', 'chore: record upstream status')
    git(root, 'bundle', 'create', str(destination / 'candidate.bundle'), 'HEAD')
    (destination / 'pr-body.md').write_text(text, encoding='utf-8')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(text)
    output('changed', True)
    output('conflict', bool(conflicts))
    return True, bool(conflicts)


if __name__ == '__main__':
    prepare(ROOT, Path(os.environ['CANDIDATE_DIR']).resolve())
