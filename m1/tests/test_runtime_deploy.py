import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'm1/profile-overlay/airootfs/usr/lib/clawos'


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


deploy = load('deploy', LIB / 'clawos-deploy')
windows = load('windows', LIB / 'clawos_windows.py')


class WindowIdentity(unittest.TestCase):
    def test_title_changes_do_not_change_identity(self):
        node = {'type': 'con', 'id': 4, 'name': 'A renamed conversation',
                'app_id': 'chrome-__run_user_1000_clawos-control-ui-bootstrap-agent.html-Default'}
        self.assertEqual(windows.find_agent_window({'floating_nodes': [node]})['id'], 4)
        node['name'] = 'main — OpenClaw'
        self.assertTrue(windows.is_agent_window(node))

    def test_unrelated_title_is_not_identity(self):
        self.assertFalse(windows.is_agent_window({'name': 'OpenClaw Control', 'app_id': 'firefox'}))

    def test_ambiguous_identity_fails(self):
        node = {'type': 'con', 'id': 3, 'app_id': 'clawos-agent'}
        with self.assertRaises(ValueError):
            windows.find_agent_window({'nodes': [node, dict(node, id=4)]})

    def test_mark_survives_app_id_change(self):
        self.assertTrue(windows.is_agent_window({'marks': ['clawos-agent-canvas'], 'app_id': 'new-id'}))


class Deployment(unittest.TestCase):
    def test_delivery_retries_without_replaying_deployment(self):
        identifier = '33333333-3333-4333-8333-333333333333'
        job = self.store / 'jobs' / identifier
        job.mkdir()
        receipt = {'jobId':identifier,'state':'complete','owner':'clawos',
                   'target':{'sessionKey':'agent:main:test','sessionId':'original'}}
        deploy.write_json(job / 'receipt.json', receipt)
        with patch.object(deploy,'STORE',self.store), patch.object(deploy,'gateway_call',side_effect=[RuntimeError('offline'),{'messageId':'one'}]) as call:
            deploy.deliver_pending()
            self.assertEqual(deploy.read_json(job / 'delivery.json')['state'],'retrying')
            deploy.deliver_pending()
            deploy.deliver_pending()
            self.assertEqual(call.call_count,2)
            self.assertEqual(deploy.read_json(job / 'delivery.json')['messageId'],'one')

    def test_lost_acknowledgement_retries_same_delivery_identity(self):
        identifier = '44444444-4444-4444-8444-444444444444'
        job = self.store / 'jobs' / identifier
        job.mkdir()
        deploy.write_json(job / 'receipt.json', {'jobId':identifier,'state':'rolled-back','owner':'clawos',
            'target':{'sessionKey':'agent:main:test','sessionId':'original'}})
        requests = []
        def lost_ack(owner, method, params):
            requests.append((method, params))
            if len(requests) == 1:
                raise TimeoutError('simulated commit succeeded, acknowledgement lost')
            return {'messageId':'same-message'}
        with patch.object(deploy,'STORE',self.store), patch.object(deploy,'gateway_call',side_effect=lost_ack):
            deploy.deliver_pending()
            deploy.deliver_pending()
        self.assertEqual(requests[0], requests[1])
        self.assertEqual(deploy.read_json(job / 'delivery.json')['state'],'delivered')

    def test_public_receipt_excludes_private_output_and_is_readable(self):
        identifier = '22222222-2222-4222-8222-222222222222'
        receipt = {'jobId': identifier, 'state': 'complete', 'version': 'v1',
                   'error': 'private token', 'health': {'secret': 'private data'},
                   'command': 'private command', 'prompt': 'private prompt'}
        with patch.object(deploy, 'STORE', self.store):
            deploy.publish_receipt(receipt)
        path = self.store.parent / 'deploy-receipts' / (identifier + '.json')
        text = path.read_text()
        self.assertNotIn('private', text)
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        self.assertEqual(json.loads(text)['state'], 'complete')
        self.assertTrue(json.loads(text)['healthVerified'])

    def test_gateway_restart_waits_for_graceful_agent_drain(self):
        with patch.object(deploy, 'run') as run, patch.object(deploy, 'user_command', side_effect=lambda owner, args: args):
            deploy.reload_runtime('clawos', ['usr/lib/clawos/openclaw-plugin/lib/embodiment.js'])
        restart = next(call for call in run.call_args_list if 'openclaw-gateway.service' in call.args[0])
        self.assertGreaterEqual(restart.kwargs['timeout'], 330 + 60)

    def test_recovery_uses_repaired_worker_without_overwriting_original(self):
        identifier = '11111111-1111-4111-8111-111111111111'
        job = self.store / 'jobs' / identifier
        job.mkdir()
        (job / 'worker.py').write_text('original worker evidence')
        deploy.write_json(job / 'receipt.json', {'jobId': identifier, 'version': 'candidate', 'state': 'recovery-required'})
        deploy.write_json(job / 'before.json', {})
        deploy.write_json(job / 'previous-manifest.json', {'version': 'previous'})
        deploy.write_json(self.store / 'installed.json', {'version': 'previous'})
        with patch.object(deploy, 'STORE', self.store), patch.object(deploy.os, 'geteuid', return_value=0), \
             patch.object(deploy.sys, 'argv', ['clawos-deploy', 'rollback', identifier]), \
             patch.object(deploy, 'run') as run, patch('builtins.print'):
            deploy.main()
        self.assertEqual((job / 'worker.py').read_text(), 'original worker evidence')
        self.assertEqual(deploy.digest(job / 'recovery-worker.py'), deploy.digest(Path(deploy.__file__)))
        self.assertIn(str(job / 'recovery-worker.py'), run.call_args.args[0])
        receipt = deploy.read_json(job / 'receipt.json')
        self.assertEqual(receipt['recoveryWorkerSha256'], deploy.digest(job / 'recovery-worker.py'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'root'
        self.root.mkdir()
        self.store = Path(self.temp.name) / 'store'
        self.store.mkdir()
        self.job = self.store / 'jobs/test-job'
        self.job.mkdir(parents=True)
        self.name = 'usr/lib/clawos/example'
        self.target = self.root / self.name
        self.target.parent.mkdir(parents=True)
        self.target.write_text('old')
        self.target.chmod(0o755)

    def payload(self, values):
        files = {}
        for name, value in values.items():
            target = self.job / 'package/files' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(value)
            files[name] = {'sha256': deploy.digest(target), 'mode': 0o755}
        version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        manifest = {'schema': 1, 'files': files, 'version': version}
        deploy.write_json(self.job / 'package/manifest.json', manifest)
        return manifest

    def receipt(self, manifest, names):
        deploy.write_json(self.job / 'receipt.json', {'jobId': 'test-job', 'version': manifest['version'],
                          'owner': 'clawos', 'changedFiles': names, 'state': 'queued'})

    def test_payload_hash_is_checked(self):
        self.payload({self.name: 'new'})
        (self.job / 'package/files' / self.name).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            deploy.verify_payload(self.job / 'package')

    def test_nonexecutable_command_is_rejected_before_apply(self):
        manifest = self.payload({'usr/lib/clawos/clawosctl': 'command'})
        manifest['files']['usr/lib/clawos/clawosctl']['mode'] = 0o644
        deploy.write_json(self.job / 'package/manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'must be executable'):
            deploy.verify_payload(self.job / 'package')

    def test_credentials_boot_and_traversal_rejected(self):
        for name in ('etc/clawos/preferences.json', 'etc/clawos/clawosd.json',
                     'etc/clawos/full-root.sudoers', 'boot/vmlinuz-linux',
                     'usr/lib/clawos/../../shadow', '/etc/shadow'):
            self.assertFalse(deploy.allowed(name))

    def test_symlink_destination_rejected(self):
        self.target.unlink()
        self.target.symlink_to(Path(self.temp.name) / 'outside')
        with self.assertRaises(ValueError):
            deploy.destination(self.root, self.name)

    def test_success_and_explicit_rollback(self):
        manifest = self.payload({self.name: 'new'})
        self.receipt(manifest, [self.name])
        with patch.object(deploy, 'STORE', self.store), patch.object(deploy, 'run'), \
             patch.object(deploy, 'reload_runtime'), patch.object(deploy, 'health', return_value={'ready': True}):
            deploy.worker('test-job', root=self.root)
            self.assertEqual(self.target.read_text(), 'new')
            self.assertEqual(deploy.read_json(self.job / 'receipt.json')['state'], 'complete')
            deploy.worker('test-job', rollback=True, root=self.root)
            self.assertEqual(self.target.read_text(), 'old')
            self.assertEqual(deploy.read_json(self.job / 'receipt.json')['state'], 'rolled-back')

    def test_failed_health_restores_added_modified_and_removed_files(self):
        added = 'usr/lib/clawos/added'
        removed = 'usr/lib/clawos/retired'
        (self.root / removed).write_text('retired-before')
        manifest = self.payload({self.name: 'bad', added: 'new-file'})
        self.receipt(manifest, [self.name, added, removed])
        with patch.object(deploy, 'STORE', self.store), patch.object(deploy, 'run'), \
             patch.object(deploy, 'reload_runtime'), \
             patch.object(deploy, 'health', side_effect=[RuntimeError('injected failure'), {'ready': True}]):
            deploy.worker('test-job', root=self.root)
        self.assertEqual(self.target.read_text(), 'old')
        self.assertFalse((self.root / added).exists())
        self.assertEqual((self.root / removed).read_text(), 'retired-before')
        self.assertEqual(deploy.read_json(self.job / 'receipt.json')['state'], 'rolled-back')

    def test_snapshot_failure_does_not_modify_runtime(self):
        manifest = self.payload({self.name: 'new'})
        self.receipt(manifest, [self.name])
        with patch.object(deploy, 'STORE', self.store), \
             patch.object(deploy, 'run', side_effect=RuntimeError('snapshot failed')):
            with self.assertRaises(RuntimeError):
                deploy.worker('test-job', root=self.root)
        self.assertEqual(self.target.read_text(), 'old')


if __name__ == '__main__':
    unittest.main()
