"""Read-only installer target discovery and fail-closed validation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess

DEVICE = re.compile(r'^/dev/(?:sd[a-z]+|vd[a-z]+|nvme[0-9]+n[0-9]+|mmcblk[0-9]+)$')
MIN_BYTES = 32 * 1024 ** 3
LSBLK_COLUMNS = 'NAME,KNAME,PATH,TYPE,SIZE,RO,RM,MODEL,SERIAL,WWN,MAJ:MIN,FSTYPE,PTTYPE,MOUNTPOINTS'


def descendants(node):
    yield node
    for child in node.get('children', []):
        yield from descendants(child)


def identity(disk):
    fields = {key: disk.get(key) for key in ('path', 'maj:min', 'size', 'model', 'serial', 'wwn', 'diskseq')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def confirmation_token(target):
    """The exact text a person must type to erase ``target``."""
    return 'ERASE-' + target


def describe(disk):
    """One human-readable line shared by every surface that names a disk."""
    size = int(disk.get('size') or 0) / (1024 ** 3)
    model = str(disk.get('model') or 'Disk').strip()
    serial = str(disk.get('serial') or '').strip()
    identity_hint = '…' + serial[-6:] if serial else 'unavailable'
    return f"{disk.get('path', '')} · {size:.0f} GiB · {model} · ID {identity_hint}"


def partitions(target):
    if not DEVICE.fullmatch(target):
        raise ValueError('Unsupported whole-disk path')
    suffix = 'p' if target[-1].isdigit() else ''
    return target + suffix + '1', target + suffix + '2'


def eligibility(disk, boot_devices):
    if not boot_devices:
        return 'Live boot media could not be identified'
    path = disk.get('path', '')
    nodes = list(descendants(disk))
    if disk.get('type') != 'disk' or not DEVICE.fullmatch(path):
        return 'Not a supported whole disk'
    if any(node.get('path') in boot_devices for node in nodes):
        return 'Installation boot media'
    if any(node.get('ro') in (True, 1, '1') for node in nodes):
        return 'Read-only disk'
    if any(any(point for point in (node.get('mountpoints') or [])) for node in nodes):
        return 'Disk or child is mounted or used as swap'
    if any(node.get('holders') for node in nodes):
        return 'Disk is in use by a device mapper or RAID holder'
    # A bare partition-table label counts as a signature for wipefs, so it must
    # count as non-blank here too; otherwise the GUI offers a disk the
    # privileged validate step then refuses.
    if disk.get('children') or disk.get('fstype') or disk.get('pttype'):
        return 'Only blank, unpartitioned disks are supported in this experimental installer'
    if int(disk.get('size') or 0) < MIN_BYTES:
        return 'At least 32 GiB is required'
    return None


def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL, timeout=15).strip()


def inventory():
    if platform.machine() != 'x86_64' or not Path('/sys/firmware/efi').is_dir():
        raise ValueError('Boot ClawOS in x86_64 UEFI mode')
    if run(['findmnt', '-nro', 'FSTYPE', '/']) != 'overlay' or 'archisobasedir=' not in Path('/proc/cmdline').read_text():
        raise ValueError('Installation is allowed only from the ClawOS live ISO')
    if not re.search(r'^ID=clawos$', Path('/etc/os-release').read_text(), re.M):
        raise ValueError('This is not the ClawOS live system')
    secure_boot = list(Path('/sys/firmware/efi/efivars').glob('SecureBoot-*'))
    for path in secure_boot:
        value = path.read_bytes()
        if len(value) < 5 or value[4] != 0:
            raise ValueError('Secure Boot is not supported by this experimental installer')
    boot = run(['findmnt', '-nro', 'SOURCE', '/run/archiso/bootmnt']).split('[')[0]
    boot = os.path.realpath(boot)
    if not boot.startswith('/dev/'):
        raise ValueError('Cannot identify and protect the live boot media')
    boot_devices = set(run(['lsblk', '-srnpo', 'NAME', boot]).splitlines())
    if not boot_devices:
        raise ValueError('Cannot identify the live boot media ancestry')
    disks = json.loads(run(['lsblk', '--json', '--bytes', '--paths', '--output', LSBLK_COLUMNS]))['blockdevices']
    for disk in disks:
        for node in descendants(disk):
            kname = Path(node.get('kname', '')).name
            node['holders'] = [p.name for p in (Path('/sys/class/block') / kname / 'holders').iterdir()]
            if node.get('type') == 'disk' and DEVICE.fullmatch(node.get('path', '')):
                node['diskseq'] = (Path('/sys/class/block') / kname / 'diskseq').read_text().strip()
                if not node['diskseq'].isdigit():
                    raise ValueError('Cannot establish the kernel disk generation')
    return disks, boot_devices


def list_targets():
    disks, boot = inventory()
    return [
        {**disk, 'diskId': identity(disk), 'label': describe(disk)}
        for disk in disks if eligibility(disk, boot) is None
    ]


def check_identity(target, disk_id, disks=None, when='during installation; stopping'):
    """Return the one whole disk at ``target`` whose identity still matches."""
    if disks is None:
        disks, _boot = inventory()
    matches = [disk for disk in disks if disk.get('path') == target]
    if len(matches) != 1 or os.path.realpath(target) != target:
        raise ValueError('Target must be an existing canonical whole disk')
    if identity(matches[0]) != disk_id:
        raise ValueError(f'Disk identity changed {when}')
    return matches[0]


def validate(target, disk_id, confirmation):
    disks, boot = inventory()
    disk = check_identity(target, disk_id, disks, when='since selection; inspect and select again')
    reason = eligibility(disk, boot)
    if reason:
        raise ValueError(reason)
    if confirmation != confirmation_token(target):
        raise ValueError('Type the exact erase confirmation for the selected disk')
    if not stat.S_ISBLK(os.stat(target).st_mode):
        raise ValueError('Target is not a block device')
    signatures = json.loads(run(['wipefs', '--no-act', '--json', target])).get('signatures', [])
    if signatures:
        raise ValueError('Disk has existing signatures; use a blank spare disk')
    esp, root = partitions(target)
    return {'target': target, 'diskId': disk_id, 'esp': esp, 'systemPartition': root}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'validate', 'check-identity', 'token'])
    parser.add_argument('--target')
    parser.add_argument('--disk-id')
    parser.add_argument('--confirm')
    args = parser.parse_args()
    if args.command == 'list':
        print(json.dumps(list_targets()))
    elif args.command == 'token':
        print(confirmation_token(args.target or ''))
    elif args.command == 'check-identity':
        check_identity(args.target, args.disk_id)
    else:
        print(json.dumps(validate(args.target, args.disk_id, args.confirm)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
        raise SystemExit(f'Installer target refused: {error}')
