#!/usr/bin/env python3
"""Bounded serial capture and ACPI power requests; never QEMU quit/reset."""
import argparse
import json
from pathlib import Path
import re
import socket
import sys
import time


def console_ready(path, hostname='clawos-live'):
    with Path(path).open('rb') as log:
        log.seek(0, 2)
        log.seek(max(0, log.tell() - 65536))
        text = log.read().decode('utf-8', errors='replace')
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    host = re.escape(hostname)
    return bool(re.search(rf'{host}#|root@{host}[^\n]*#', text))


def qmp_command(path, operation, arguments=None):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(path)
        with client.makefile('rwb') as stream:
            greeting = json.loads(stream.readline())
            if 'QMP' not in greeting:
                raise ValueError('Missing QMP greeting')
            for command in ('qmp_capabilities', operation):
                request = {'execute': command, 'id': command}
                if command == operation and arguments:
                    request['arguments'] = arguments
                stream.write((json.dumps(request) + '\n').encode())
                stream.flush()
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    line = stream.readline()
                    if not line:
                        raise ValueError('QMP closed before acknowledging ACPI request')
                    reply = json.loads(line)
                    if reply.get('id') != command:
                        continue
                    if 'error' in reply or 'return' not in reply:
                        raise ValueError('QMP rejected ACPI request')
                    break
                else:
                    raise TimeoutError('QMP response deadline exceeded')


def powerdown(path):
    qmp_command(path, 'system_powerdown')


def capture(path, destination, commands, seconds, until=None):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(path)
        # Pace UART input: a single large write can overrun the guest FIFO.
        for offset in range(0, len(commands), 64):
            client.sendall(commands[offset:offset + 64])
            time.sleep(.02)
        deadline = time.monotonic() + seconds
        tail = b''
        marker = until.encode() if until else None
        with Path(destination).open('wb') as output:
            while time.monotonic() < deadline:
                client.settimeout(min(1, max(.01, deadline - time.monotonic())))
                try:
                    data = client.recv(65536)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    if marker:
                        raise ValueError('Serial connection reset before completion marker') from None
                    return
                if not data:
                    if marker:
                        raise ValueError('Serial connection closed before completion marker')
                    return
                output.write(data)
                output.flush()
                combined = tail + data
                if marker and any(line.rstrip(b'\r') == marker for line in combined.split(b'\n')[:-1]):
                    return
                tail = combined[-8192:]
        raise TimeoutError('Serial capture deadline exceeded')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('powerdown').add_argument('socket')
    ready = sub.add_parser('ready')
    ready.add_argument('log')
    ready.add_argument('--hostname', choices=('clawos-live', 'clawos-installed'), default='clawos-live')
    screen = sub.add_parser('screendump')
    screen.add_argument('socket')
    screen.add_argument('destination')
    serial = sub.add_parser('capture')
    serial.add_argument('socket')
    serial.add_argument('log')
    serial.add_argument('seconds', type=int)
    serial.add_argument('--until')
    args = parser.parse_args()
    if args.action == 'powerdown':
        powerdown(args.socket)
    elif args.action == 'ready':
        sys.exit(0 if console_ready(args.log, args.hostname) else 1)
    elif args.action == 'screendump':
        qmp_command(args.socket, 'screendump', {'filename': str(Path(args.destination).resolve())})
    else:
        if not 1 <= args.seconds <= 3600:
            parser.error('seconds must be between 1 and 3600')
        capture(args.socket, args.log, sys.stdin.buffer.read(), args.seconds, args.until)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TimeoutError) as error:
        print(f'QEMU I/O failed: {type(error).__name__}', file=sys.stderr)
        sys.exit(1)
