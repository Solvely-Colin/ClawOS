#!/usr/bin/env python3
"""Validate ClawOS identity and the explicitly allowed Arch build sources."""
import argparse
from datetime import datetime
from pathlib import Path
import re
import shlex
import sys

REPO = Path(__file__).resolve().parents[2]
SECTIONS = {'options', 'core', 'extra'}
INCLUDE = '/etc/pacman.d/mirrorlist'


def read_file(path, boundary):
    path, boundary = Path(path), Path(boundary)
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Package/identity inputs must not use symlinks')
        if part == boundary:
            break
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Missing, non-regular or oversized build input')
    return path.read_text(encoding='utf-8')


def active_lines(text):
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def archive_server(versions):
    matches = re.findall(r'^ARCH_SNAPSHOT=([0-9]{4}/[0-9]{2}/[0-9]{2})$', versions, re.M)
    if len(matches) != 1:
        raise ValueError('Expected one pinned Arch snapshot')
    datetime.strptime(matches[0], '%Y/%m/%d')
    return f'https://archive.archlinux.org/repos/{matches[0]}/$repo/os/$arch'


def check_mirror(text, expected):
    lines = active_lines(text)
    if len(lines) != 1 or not re.fullmatch(r'Server\s*=\s*' + re.escape(expected), lines[0]):
        raise ValueError('Mirrorlist must contain only the pinned Arch archive server')


def check_pacman(text, expected):
    seen, sources = set(), set()
    signatures = {}
    section = None
    for line in active_lines(text):
        header = re.fullmatch(r'\[([A-Za-z0-9._-]+)\]', line)
        if header:
            section = header[1]
            if section not in SECTIONS or section in seen:
                raise ValueError('Unexpected or duplicate package repository section')
            seen.add(section)
            continue
        if section is None or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*(?:\s*=\s*.*)?', line):
            raise ValueError('Malformed package configuration')
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if key == 'Include':
            if not separator or value != INCLUDE:
                raise ValueError('Package includes must use the pinned mirrorlist')
            sources.add(section)
        elif key == 'Server':
            if value != expected:
                raise ValueError('Unexpected package server')
            sources.add(section)
        elif key == 'SigLevel':
            if section in signatures:
                raise ValueError('Duplicate package signature policy')
            tokens = set(value.split())
            if 'Required' not in tokens or not tokens <= {'Required', 'DatabaseOptional', 'TrustedOnly'}:
                raise ValueError('Package signatures must remain required')
            signatures[section] = tokens
    if seen != SECTIONS or not {'core', 'extra'} <= sources or 'options' not in signatures:
        raise ValueError('Expected core/extra repositories and a required signature policy')


def check_identity(text):
    values = {}
    for line in active_lines(text):
        key, separator, value = line.partition('=')
        if not separator or key in values:
            raise ValueError('Malformed or duplicate OS identity field')
        words = shlex.split(value)
        if len(words) != 1:
            raise ValueError('Malformed OS identity value')
        values[key] = words[0]
    if values.get('ID') != 'clawos' or values.get('ID_LIKE') != 'arch':
        raise ValueError('Expected ClawOS identity with Arch lineage')


def check_packages(text):
    packages = active_lines(text)
    if not packages or len(packages) != len(set(packages)):
        raise ValueError('Empty or duplicate package selection')
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9@+._-]*', package) for package in packages):
        raise ValueError('Package selection must contain plain package names')


def check_source(repo):
    repo = Path(repo)
    overlay = repo / 'image/profile-overlay'
    expected = archive_server(read_file(repo / 'image/config/versions.env', repo))
    check_pacman(read_file(overlay / 'pacman.conf', repo), expected)
    check_mirror(read_file(repo / 'image/config/mirrorlist', repo), expected)
    check_packages(read_file(overlay / 'packages.x86_64', repo))
    check_identity(read_file(overlay / 'airootfs/etc/os-release', repo))
    return expected


def check_root(root, expected, partial=False):
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected an ordinary root directory')
    check_identity(read_file(root / 'etc/os-release', root))
    pacman = root / 'etc/pacman.conf'
    if pacman.exists() or pacman.is_symlink():
        check_pacman(read_file(pacman, root), expected)
    mirror = root / 'etc/pacman.d/mirrorlist'
    if not partial or mirror.exists() or mirror.is_symlink():
        check_mirror(read_file(mirror, root), expected)
    directory = root / 'etc/pacman.d'
    if directory.is_symlink():
        raise ValueError('Package configuration directory must not be a symlink')
    if directory.exists():
        for entry in directory.iterdir():
            if entry.name == 'mirrorlist':
                continue
            if entry.name not in {'gnupg', 'hooks'} or entry.is_symlink() or not entry.is_dir():
                raise ValueError('Unexpected package-source entry')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, nargs='?', help='Optional materialized or mounted ClawOS root')
    args = parser.parse_args()
    expected = check_source(REPO)
    if args.root is not None:
        partial = args.root.resolve() == (REPO / 'image/profile-overlay/airootfs').resolve()
        check_root(args.root, expected, partial=partial)
    print('ClawOS identity and pinned Arch source checks passed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, UnicodeError, ValueError) as error:
        print(f'Arch-base validation failed: {error}', file=sys.stderr)
        sys.exit(1)
