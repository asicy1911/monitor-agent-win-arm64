"""Validate PE architecture and package the binary with its source identity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def version_check():
    version = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']
    publishing = os.getenv('PUBLISH', '').lower() == 'true'
    if publishing or os.getenv('GITHUB_REF', '').startswith('refs/tags/'):
        if os.getenv('GITHUB_REF_TYPE') != 'tag' or os.getenv('GITHUB_REF_NAME') != f'v{version}':
            raise SystemExit(f'Publishing requires tag v{version}; disable publish to download artifacts.')
    return version


def package(target):
    version = version_check()
    source = ROOT / 'target' / target / 'release' / 'monitor-agent.exe'
    data = source.read_bytes()
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    if data[:2] != b'MZ' or data[pe_offset:pe_offset + 4] != b'PE\0\0':
        raise SystemExit('Not a Windows PE executable')
    machine = struct.unpack_from('<H', data, pe_offset + 4)[0]
    expected = 0xAA64 if target.startswith('aarch64-') else 0x8664
    if machine != expected:
        raise SystemExit(f'Wrong PE architecture: {machine:#x}, expected {expected:#x}')
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    name = f'monitor-agent-{target}'
    executable = out / f'{name}.exe'
    shutil.copyfile(source, executable)
    info = {
        'version': version, 'target': target,
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
        'sha256': hashlib.sha256(data).hexdigest(),
        'upstreams': json.loads((ROOT / 'upstream-lock.json').read_text()),
    }
    info_path = out / f'{name}.json'
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with zipfile.ZipFile(out / f'{name}.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(executable, 'monitor-agent.exe')
        archive.write(info_path, 'BUILD-INFO.json')
        for file in ('Install.ps1', 'README.md', 'LICENSE', 'UPSTREAM-STATUS.md'):
            archive.write(ROOT / file, file)
    print(f'Packaged {name}, PE machine={machine:#x}, SHA256={info["sha256"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=['aarch64-pc-windows-msvc', 'x86_64-pc-windows-msvc', 'x86_64-pc-windows-gnu'])
    parser.add_argument('--check-version', action='store_true')
    args = parser.parse_args()
    if args.check_version:
        version_check()
    elif args.target:
        package(args.target)
    else:
        parser.error('Use --target or --check-version')
