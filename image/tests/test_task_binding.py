import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LIB = Path(__file__).resolve().parents[1] / 'profile-overlay/airootfs/usr/lib/clawos'
sys.path.insert(0, str(LIB))
from clawos_task import Drafts, task_id, task_for_node, session_key


class TaskBinding(unittest.TestCase):
    def test_windows_and_drafts_belong_to_tasks_across_switches_and_restart(self):
        a, b = 'agent:main:alpha', 'agent:main:beta'
        tasks = {task_id(key): {'sessionKey': key} for key in (a, b)}
        for kind in ('command', 'build', 'browse'):
            for key in (a, b):
                self.assertEqual(task_for_node({'app_id': f'clawos-{kind}-{task_id(key)}'}, tasks), key)
        self.assertIsNone(task_for_node({'app_id': 'clawos-browse'}, tasks))
        with tempfile.TemporaryDirectory() as directory:
            drafts = Drafts(directory)
            drafts.save(a, 'draft A')
            drafts.save(b, 'draft B')
            drafts = Drafts(directory)
            self.assertEqual(drafts.load(a), 'draft A')
            self.assertEqual(drafts.load(b), 'draft B')
            drafts.save(a, 'newer A')
            drafts.acknowledge(a, 'draft A')
            self.assertEqual(drafts.load(a), 'newer A')
            drafts.acknowledge(b, 'draft B')
            self.assertEqual(drafts.load(b), '')
            self.assertEqual(drafts.load(a), 'newer A')

    def test_two_queued_tasks_execute_in_reverse_order_without_cross_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            systemd = root / 'systemd-run'
            systemd.write_text('#!/bin/sh\nexit 0\n')
            systemd.chmod(0o755)
            openclaw = root / 'openclaw'
            openclaw.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
key = sys.argv[sys.argv.index('--session-key')+1]
source = pathlib.Path(sys.argv[sys.argv.index('--message-file')+1])
(pathlib.Path(os.environ['CAPTURE']) / source.stem).write_text(json.dumps([key, source.read_text()]))
''')
            openclaw.chmod(0o755)
            capture = root / 'capture'
            capture.mkdir()
            env = {**os.environ, 'XDG_STATE_HOME': str(root / 'state'),
                   'CLAWOS_SYSTEMD_RUN': str(systemd), 'CLAWOS_OPENCLAW': str(openclaw),
                   'CAPTURE': str(capture)}
            def submit(key):
                value = subprocess.run([sys.executable, str(LIB / 'clawos-agent-submit'), key],
                                       input='prompt for ' + key, text=True, capture_output=True,
                                       env=env, check=True)
                return key, json.loads(value.stdout)['requestId']
            with concurrent.futures.ThreadPoolExecutor() as pool:
                queued = list(pool.map(submit, ['agent:main:alpha', 'agent:main:beta']))
            for key, identifier in reversed(queued):
                request = root / 'state/clawos/agent-requests' / (identifier + '.txt')
                subprocess.run([sys.executable, str(LIB / 'clawos-agent-run'), str(request)],
                               env=env, check=True)
                self.assertEqual(json.loads((capture / identifier).read_text()), [key, 'prompt for ' + key])
                self.assertFalse(request.exists())
                self.assertFalse(request.with_suffix('.task.json').exists())
            rejected = subprocess.run([sys.executable, str(LIB / 'clawos-agent-submit')],
                                      input='unbound', text=True, env={**env, 'CLAWOS_SESSION_KEY': ''},
                                      capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)

    def test_invalid_identity_is_rejected(self):
        for key in (None, '', 'main', 'agent:main:task; touch /tmp/no', 'agent:main:a\n'):
            with self.assertRaises(ValueError):
                session_key(key)
