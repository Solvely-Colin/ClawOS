"""Task identity and private drafts for the native supporting surfaces."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def session_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"agent:[A-Za-z0-9_.-]+:[A-Za-z0-9_.:/-]{1,220}", value):
        raise ValueError("Open a surface from its conversation or choose an owning task first.")
    return value


def task_id(key):
    return hashlib.sha256(session_key(key).encode()).hexdigest()[:24]


def task_for_node(node, tasks):
    app = node.get('app_id', '') or ''
    for identifier, task in tasks.items():
        try:
            key = session_key(task['sessionKey'])
            if identifier == task_id(key) and app in {
                'clawos-command-' + identifier, 'clawos-build-' + identifier,
                'clawos-browse-' + identifier,
                'clawos-conversation-' + identifier,
            }:
                return key
        except (KeyError, TypeError, ValueError):
            continue
    return None


def focused_task():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    try:
        state = json.loads((runtime / 'clawos/activity.json').read_text())
        tree = json.loads(subprocess.check_output(
            ['/usr/bin/swaymsg', '-t', 'get_tree', '-r'], text=True, timeout=2))
        def visit(node):
            if node.get('focused'):
                return task_for_node(node, state.get('tasks', {}))
            for child in node.get('nodes', []) + node.get('floating_nodes', []):
                found = visit(child)
                if found:
                    return found
            return None
        return visit(tree)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class Drafts:
    def __init__(self, root):
        self.root = Path(root)

    def load(self, key):
        try:
            return (self.root / (task_id(key) + '.txt')).read_text(encoding='utf-8')
        except FileNotFoundError:
            return ''

    def save(self, key, text):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.root / (task_id(key) + '.txt')
        fd, temporary = tempfile.mkstemp(dir=self.root, prefix='.draft-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def acknowledge(self, key, sent):
        # A late response from task A must not erase a newer draft in A or B.
        if self.load(key) == sent:
            self.save(key, '')


if __name__ == '__main__':
    try:
        key = os.environ.get('CLAWOS_SESSION_KEY') or focused_task()
        if not key and '--focused' in sys.argv:
            raise ValueError('No owning task on the focused window.')
        if not key:
            runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
            tasks = json.loads((runtime / 'clawos/activity.json').read_text()).get('tasks', {})
            choices = sorted({session_key(t['sessionKey']) for t in tasks.values()})
            if not choices:
                raise ValueError('Ask the Agent in your conversation to open this surface first.')
            selected = subprocess.run(['/usr/bin/fuzzel', '--dmenu', '--prompt=Task: '],
                                      input='\n'.join(choices), text=True, capture_output=True, check=True)
            key = selected.stdout.strip()
            if key not in choices:
                raise ValueError('No owning task selected.')
        print(session_key(key))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
