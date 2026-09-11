#!/usr/bin/env python3
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clawosd_core import Broker, BrokerError, BtrfsRecovery  # noqa: E402


class FakeRunner:
    def __init__(self, fail=False):
        self.commands = []
        self.fail = fail
        self.timezone = "UTC"
        self.services = {
            "NetworkManager.service": "active",
            "sshd.service": "active",
            "tailscaled.service": "inactive",
            "clawos-session@clawos.service": "active",
        }

    def run(self, argv, timeout=900):
        self.commands.append(list(argv))
        if self.fail and argv[0] == "/usr/bin/pacman":
            raise BrokerError("injected package failure")
        if argv == ["/usr/bin/id", "-u", "clawos"]:
            return "1000\n"
        if argv == ["/usr/bin/getent", "passwd", "clawos"]:
            return "clawos:x:1000:1000::/home/clawos:/bin/bash\n"
        if argv[-3:] == ["--user", "is-active", "openclaw-gateway.service"]:
            return "active\n"
        if argv == ["/usr/bin/timedatectl", "show", "--property=Timezone", "--value"]:
            return f"{self.timezone}\n"
        if argv[:2] == ["/usr/bin/timedatectl", "set-timezone"]:
            self.timezone = argv[2]
        if argv == ["/usr/bin/hostnamectl", "--static"]:
            return "clawos-test\n"
        if argv == ["/usr/bin/uname", "-r"]:
            return "test-kernel\n"
        if argv[:4] == ["/usr/bin/systemctl", "show", "--property=ActiveState", "--value"]:
            return f"{self.services.get(argv[4], 'inactive')}\n"
        if len(argv) == 3 and argv[0] == "/usr/bin/systemctl" and argv[1] in {"start", "stop", "restart"}:
            self.services[argv[2]] = "inactive" if argv[1] == "stop" else "active"
        if argv == ["/usr/bin/nmcli", "--terse", "--fields", "STATE", "general"]:
            return "connected\n"
        if argv == ["/usr/bin/nmcli", "--terse", "--fields", "DEVICE,TYPE,STATE", "device", "status"]:
            return "ens3:ethernet:connected\nlo:loopback:connected (externally)\n"
        return ""


class FakeRecovery:
    def __init__(self):
        self.created = []
        self.staged = []

    def create(self, action_id):
        value = f"clawosd-{action_id}"
        self.created.append(value)
        return value

    def stage(self, snapshot_id):
        self.staged.append(snapshot_id)
        return {"snapshotId": snapshot_id, "rebootRequired": True}


class RecoveryRunner:
    def __init__(self):
        self.commands = []

    def run(self, argv, timeout=900):
        self.commands.append(list(argv))
        if argv == ["/usr/bin/findmnt", "-n", "-o", "SOURCE", "/"]:
            return "/dev/mapper/cryptroot[/@]\n"
        if argv[:3] == ["/usr/bin/btrfs", "subvolume", "snapshot"]:
            Path(argv[-1]).mkdir()
        return ""


class BtrfsRecoveryTests(unittest.TestCase):
    def test_stage_mounts_the_block_device_not_findmnt_subvolume_suffix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot_id = "clawosd-11111111-1111-4111-8111-111111111111"
            snapshot_root = root / "snapshots"
            (snapshot_root / snapshot_id).mkdir(parents=True)
            top = root / "top"
            (top / "@").mkdir(parents=True)
            (top / "@snapshots" / snapshot_id).mkdir(parents=True)
            runner = RecoveryRunner()
            result = BtrfsRecovery(
                runner=runner, snapshot_root=snapshot_root, mount_root=top,
            ).stage(snapshot_id)
            mount = next(command for command in runner.commands if command[:2] == ["/usr/bin/mount", "-t"])
            self.assertEqual(mount[-2], "/dev/mapper/cryptroot")
            self.assertTrue((top / "@").is_dir())
            self.assertTrue((top / result["failedRoot"]).is_dir())


class BrokerTests(unittest.TestCase):
    def setUp(self):
        identities = patch("clawosd_core.account_uid", side_effect=lambda name: {"clawos": 1000, "claw": 999}[name])
        identities.start()
        self.addCleanup(identities.stop)
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.clock_value = 1000
        self.config = root / "clawosd.json"
        self.config.write_text(json.dumps({
            "version": 1,
            "securityLevel": "full-user-approvals",
            "approvalExpiresSeconds": 120,
            "packages": {"allow": ["tree"]},
            "services": {"allow": [
                "NetworkManager.service", "sshd.service", "tailscaled.service",
                "clawos-session@clawos.service",
            ]},
            "openclaw": {"ownerUser": "clawos", "promotedVersion": "2026.8.2"},
        }))
        self.boot_id = root / "boot_id"
        self.boot_id.write_text("11111111-1111-4111-8111-111111111111\n")
        self.uptime = root / "uptime"
        self.uptime.write_text("123.45 100.00\n")
        self.sudoers = root / "90-clawos-full-root"
        self.full_root_sudoers = root / "full-root.sudoers"
        self.full_root_sudoers.write_text("clawos ALL=(ALL:ALL) NOPASSWD: ALL\n")
        self.runner = FakeRunner()
        self.recovery = FakeRecovery()
        self.broker = Broker(
            config_path=self.config,
            state_dir=root / "state",
            audit_path=root / "audit.jsonl",
            preferences_path=root / "preferences.json",
            boot_id_path=self.boot_id,
            uptime_path=self.uptime,
            sudoers_path=self.sudoers,
            full_root_sudoers_path=self.full_root_sudoers,
            runner=self.runner,
            recovery=self.recovery,
            clock=lambda: self.clock_value,
            token_factory=lambda: "a" * 43,
        )
        self.peer = {"uid": 1000, "pid": 4242}

    def tearDown(self):
        self.temporary.cleanup()

    def test_status_does_not_infer_machine_readiness_from_broker_availability(self):
        self.runner.commands.clear()
        status = self.broker.status()
        self.assertEqual(status["state"], "unknown")
        self.assertEqual(status["brokerState"], "ready")
        self.assertEqual(status["readiness"], {
            "setup": "unverified", "desktop": "unverified",
            "lock": "unverified", "gateway": "unverified",
            "model": "unverified",
        })
        self.assertEqual(self.runner.commands, [])
        self.assertEqual(status["pendingCount"], 0)
        self.assertEqual(status["activeGrantCount"], 0)
        self.assertIn("system.time.configure", status["capabilities"])

    def test_status_remains_unverified_for_every_security_level(self):
        for level in ("full-root", "full-user-approvals", "user-limited"):
            with self.subTest(level=level):
                self.broker.config["securityLevel"] = level
                self.assertEqual(self.broker.status()["state"], "unknown")
                self.assertEqual(self.broker.status()["readiness"]["model"], "unverified")

    def gateway_peer(self, uid=1000, pid=4242, unit="openclaw-gateway.service"):
        self.broker.proc_root = Path(self.temporary.name) / "proc"
        directory = self.broker.proc_root / str(pid)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "cgroup").write_text(
            f"0::/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/{unit}\n")
        return {"uid": uid, "pid": pid}

    def enable_agent_policy(self, level="user-limited"):
        self.broker.config["securityLevel"] = level
        self.broker.config["openclaw"]["agentUser"] = "claw"
        self.broker.config["agentPolicies"] = {
            "requireTrustedAttribution": True, "defaultAllow": [], "agents": {"main": ["*"]}}

    def test_unrelated_uid_cannot_prepare_list_commit_or_cancel(self):
        self.broker.config["securityLevel"] = "full-root"
        token = self.broker.prepare("service.manage", {
            "service": "sshd.service", "operation": "stop"}, self.peer)["token"]
        intruder = self.gateway_peer(uid=65534)
        for context in (None, {}, {"agentId": "main"}, {"agentId": 0}):
            with self.assertRaises(BrokerError):
                self.broker.prepare("service.manage", {
                    "service": "sshd.service", "operation": "stop"}, intruder, context)
        for operation in (lambda: self.broker.list_pending_for_peer(intruder),
                          lambda: self.broker.commit(token, intruder, authorized=True),
                          lambda: self.broker.cancel(token, intruder)):
            with self.assertRaises(BrokerError):
                operation()
        self.assertEqual(self.runner.commands, [])
        self.assertEqual(self.broker.pending_for_peer(token, self.peer)["state"], "pending")

    def test_gateway_context_cannot_fall_back_to_desktop_privilege(self):
        self.enable_agent_policy("full-root")
        gateway = self.gateway_peer()
        for context in (None, {}, {"agentId": ""}, {"agentId": None}, {"agentId": ["main"]}):
            with self.assertRaises(BrokerError):
                self.broker.prepare("package.install", {"package": "tree"}, gateway, context)
        token = self.broker.prepare("package.install", {"package": "tree"}, gateway,
                                    {"agentId": "main"})["token"]
        next_process = self.gateway_peer(pid=4343, unit="openclaw-node.service")
        self.assertEqual(self.broker.commit(token, next_process)["state"], "complete")

    def test_runtime_requires_exact_unit_and_matching_user_slice(self):
        self.enable_agent_policy()
        context = {"agentId": "main"}
        for unit in ("fake-openclaw-gateway.service", "openclaw-gateway.service.scope",
                     "openclaw-node.service-evil"):
            peer = self.gateway_peer(uid=999, unit=unit)
            with self.assertRaises(BrokerError):
                self.broker.prepare("package.install", {"package": "tree"}, peer, context)
        wrong_slice = self.gateway_peer(uid=1000)
        wrong_slice["uid"] = 999
        with self.assertRaises(BrokerError):
            self.broker.prepare("package.install", {"package": "tree"}, wrong_slice, context)

    def test_owner_can_approve_runtime_request_but_runtime_cannot_take_owner_token(self):
        self.enable_agent_policy()
        runtime = self.gateway_peer(uid=999)
        token = self.broker.prepare("package.install", {"package": "tree"}, runtime,
                                    {"agentId": "main"})["token"]
        owner = {"uid": 1000, "pid": 8888}
        self.assertEqual(self.broker.list_pending_for_peer(owner)[0]["token"], token)
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(token, owner)
        self.assertEqual(self.broker.commit(token, owner, authorized=True)["state"], "complete")
        owner_token = self.broker.prepare("package.install", {"package": "tree"}, owner)["token"]
        self.assertEqual(self.broker.list_pending_for_peer(runtime), [])
        with self.assertRaisesRegex(BrokerError, "another account"):
            self.broker.commit(owner_token, runtime, authorized=True)
        with self.assertRaises(BrokerError):
            self.broker.cancel(owner_token, runtime)
        self.assertEqual(self.broker.cancel(owner_token, {"uid": 0, "pid": 123})["state"], "cancelled")

    def test_unbound_and_wrong_boot_tokens_fail_closed(self):
        token = self.broker.prepare("package.install", {"package": "tree"}, self.peer)["token"]
        path = self.broker._pending_path(token)
        original = json.loads(path.read_text())
        for field in ("requester", "bootId"):
            record = dict(original)
            record.pop(field)
            self.broker._write_json(path, record)
            with self.assertRaises(BrokerError):
                self.broker.commit(token, self.peer, authorized=True)
        self.broker._write_json(path, original)
        self.boot_id.write_text("22222222-2222-4222-8222-222222222222\n")
        with self.assertRaises(BrokerError):
            self.broker.commit(token, self.peer, authorized=True)
        self.assertEqual(self.runner.commands, [])

    def test_policy_is_rechecked_before_commit_and_cancellation_still_works(self):
        self.enable_agent_policy("full-root")
        peer = self.gateway_peer()
        token = self.broker.prepare("package.install", {"package": "tree"}, peer,
                                    {"agentId": "main"})["token"]
        self.broker.config["agentPolicies"]["agents"]["main"] = []
        with self.assertRaisesRegex(BrokerError, "not allowed"):
            self.broker.commit(token, peer, authorized=True)
        self.assertEqual(self.runner.commands, [])
        self.assertEqual(self.broker.cancel(token, peer)["state"], "cancelled")

    def test_prepare_is_allowlisted_typed_and_non_authoritative(self):
        request = self.broker.prepare(
            "package.install", {"package": "tree"}, self.peer,
            {"agentId": "main", "sessionKey": "agent:main:main", "runId": "r1"},
        )
        self.assertEqual(request["state"], "pending")
        self.assertEqual(request["requester"]["peerUid"], 1000)
        self.assertEqual(request["requester"]["attribution"], "self-reported")
        self.assertEqual(self.runner.commands, [])
        with self.assertRaises(BrokerError):
            self.broker.prepare("package.install", {"package": "curl"}, self.peer)
        with self.assertRaises(BrokerError):
            self.broker.prepare("package.install", {"package": "tree", "command": "id"}, self.peer)
        with self.assertRaises(BrokerError):
            self.broker.prepare("shell", {"command": "id"}, self.peer)

    def test_commit_requires_authorization_and_token_is_single_use(self):
        request = self.broker.prepare("package.install", {"package": "tree"}, self.peer)
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        result = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(self.runner.commands, [["/usr/bin/pacman", "--noconfirm", "--needed", "-S", "tree"]])
        with self.assertRaises(BrokerError):
            self.broker.commit(request["token"], self.peer, authorized=True)

    def test_expired_token_never_executes(self):
        request = self.broker.prepare("package.install", {"package": "tree"}, self.peer)
        self.clock_value = request["expiresAt"] + 1
        with self.assertRaises(BrokerError):
            self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(self.runner.commands, [])

    def test_full_root_commits_without_polkit_authorization(self):
        self.broker.config["securityLevel"] = "full-root"
        request = self.broker.prepare("package.install", {"package": "tree"}, self.peer)
        self.assertFalse(request["requiresApproval"])
        result = self.broker.commit(request["token"], self.peer, authorized=False)
        self.assertEqual(result["state"], "complete")

    def test_full_root_keeps_high_impact_actions_approval_gated(self):
        self.broker.config["securityLevel"] = "full-root"
        actions = self.broker.capabilities()["actions"]
        for action in ("power.schedule", "role.switch", "security.level.configure", "recovery.rollback"):
            self.assertTrue(actions[action]["requiresApproval"], action)
        for action in ("package.install", "system.time.configure", "service.manage"):
            self.assertFalse(actions[action]["requiresApproval"], action)

    def test_denied_high_impact_action_has_no_execution_side_effects(self):
        self.broker.config["securityLevel"] = "full-root"
        request = self.broker.prepare("power.schedule", {"operation": "poweroff"}, self.peer)
        before = list(self.runner.commands)
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        self.assertEqual(self.runner.commands, before)
        self.assertEqual(request["impact"], "high")

    def test_time_preferences_are_typed_applied_verified_and_reversible(self):
        self.broker.config["securityLevel"] = "full-root"
        request = self.broker.prepare(
            "system.time.configure",
            {"timezone": "America/New_York", "clockFormat": "12h"},
            self.peer,
        )
        self.assertIn("America/New_York", request["summary"])
        result = self.broker.commit(request["token"], self.peer, authorized=False)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["timezone"], "America/New_York")
        self.assertEqual(result["clockFormat"], "12h")
        self.assertEqual(result["previous"], {"timezone": "UTC", "clockFormat": "12h"})
        self.assertEqual(json.loads(self.broker.preferences_path.read_text()), {"clockFormat": "12h"})
        self.assertEqual(self.broker.preferences_path.stat().st_mode & 0o777, 0o644)
        self.assertIn(
            ["/usr/bin/timedatectl", "set-timezone", "America/New_York"],
            self.runner.commands,
        )

    def test_time_preferences_reject_unknown_or_extra_parameters(self):
        with self.assertRaisesRegex(BrokerError, "IANA"):
            self.broker.prepare(
                "system.time.configure",
                {"timezone": "../../etc/passwd", "clockFormat": "12h"},
                self.peer,
            )
        with self.assertRaisesRegex(BrokerError, "12h or 24h"):
            self.broker.prepare(
                "system.time.configure",
                {"timezone": "UTC", "clockFormat": "locale"},
                self.peer,
            )

    def test_machine_inspection_is_typed_read_only_and_coherent(self):
        snapshot = self.broker.inspect()
        self.assertEqual(snapshot["hostname"], "clawos-test")
        self.assertEqual(snapshot["kernel"], "test-kernel")
        self.assertEqual(snapshot["timezone"], "UTC")
        self.assertEqual(snapshot["clockFormat"], "12h")
        self.assertEqual(snapshot["services"]["sshd.service"], "active")
        self.assertEqual(snapshot["services"]["tailscaled.service"], "inactive")
        self.assertEqual(snapshot["network"]["state"], "connected")
        self.assertEqual(snapshot["network"]["devices"][0], {
            "device": "ens3", "type": "ethernet", "state": "connected",
        })
        self.assertEqual(snapshot["bootId"], "11111111-1111-4111-8111-111111111111")
        self.assertEqual(snapshot["uptimeSeconds"], 123)
        self.assertEqual(snapshot["pendingCount"], 0)

    def test_service_management_is_allowlisted_verified_and_receipted(self):
        self.broker.config["securityLevel"] = "full-root"
        with self.assertRaisesRegex(BrokerError, "allowlist"):
            self.broker.prepare(
                "service.manage", {"service": "docker.service", "operation": "restart"}, self.peer,
            )
        request = self.broker.prepare(
            "service.manage", {"service": "sshd.service", "operation": "restart"}, self.peer,
        )
        result = self.broker.commit(request["token"], self.peer, authorized=False)
        self.assertEqual(result["activeState"], "active")
        self.assertEqual(result["previous"], {"activeState": "active"})
        receipt = self.broker.get_action(result["actionId"])
        self.assertEqual(receipt["state"], "complete")
        self.assertEqual(receipt["completedAt"], self.clock_value)
        self.assertEqual(receipt["service"], "sshd.service")
        self.assertNotIn("token", receipt)
        with self.assertRaisesRegex(BrokerError, "Invalid action ID"):
            self.broker.get_action("not-an-action")

    def test_scheduled_power_receipt_reconciles_after_next_boot(self):
        self.broker.config["securityLevel"] = "full-root"
        request = self.broker.prepare("power.schedule", {"operation": "reboot"}, self.peer)
        self.assertTrue(request["requiresApproval"])
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        result = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(result["state"], "scheduled")
        self.assertEqual(result["bootIdBefore"], "11111111-1111-4111-8111-111111111111")
        self.assertTrue(any(
            command[-3:] == ["--on-active=3s", "/usr/bin/systemctl", "reboot"]
            for command in self.runner.commands
        ))
        still_scheduled = Broker(
            config_path=self.config,
            state_dir=Path(self.temporary.name) / "state",
            audit_path=Path(self.temporary.name) / "audit.jsonl",
            preferences_path=Path(self.temporary.name) / "preferences.json",
            boot_id_path=self.boot_id,
            uptime_path=self.uptime,
            runner=self.runner,
            recovery=self.recovery,
            clock=lambda: self.clock_value,
            token_factory=lambda: "b" * 43,
        )
        self.assertEqual(still_scheduled.get_action(result["actionId"])["state"], "scheduled")
        self.boot_id.write_text("22222222-2222-4222-8222-222222222222\n")
        self.clock_value += 5
        after_boot = Broker(
            config_path=self.config,
            state_dir=Path(self.temporary.name) / "state",
            audit_path=Path(self.temporary.name) / "audit.jsonl",
            preferences_path=Path(self.temporary.name) / "preferences.json",
            boot_id_path=self.boot_id,
            uptime_path=self.uptime,
            runner=self.runner,
            recovery=self.recovery,
            clock=lambda: self.clock_value,
            token_factory=lambda: "c" * 43,
        )
        receipt = after_boot.get_action(result["actionId"])
        self.assertEqual(receipt["state"], "complete")
        self.assertTrue(receipt["reconciled"])
        self.assertEqual(receipt["bootIdAfter"], "22222222-2222-4222-8222-222222222222")

    def test_role_switch_uses_only_the_transactional_root_owned_helper(self):
        self.broker.config["securityLevel"] = "full-root"
        with self.assertRaisesRegex(BrokerError, "standalone or node"):
            self.broker.prepare("role.switch", {"target": "server"}, self.peer)
        request = self.broker.prepare("role.switch", {"target": "node"}, self.peer)
        self.assertTrue(request["requiresApproval"])
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        result = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["role"], "node")
        command = next(command for command in self.runner.commands if "/usr/lib/clawos/clawos-role" in command)
        self.assertEqual(command[-3:], ["/usr/lib/clawos/clawos-role", "switch", "node"])
        self.assertIn("--uid=clawos", command)

    def test_security_level_changes_runtime_and_root_policy_atomically(self):
        self.broker.config["securityLevel"] = "full-root"
        request = self.broker.prepare(
            "security.level.configure", {"level": "user-limited"}, self.peer,
        )
        self.assertTrue(request["requiresApproval"])
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        result = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(result["securityLevel"], "user-limited")
        self.assertFalse(self.sudoers.exists())
        self.assertEqual(json.loads(self.config.read_text())["securityLevel"], "user-limited")
        self.assertIn(
            ["/usr/lib/clawos/clawos-security-mode", "user-limited"],
            self.runner.commands,
        )

        # A privilege increase from an approval-gated level cannot auto-commit.
        self.broker.token_factory = lambda: "z" * 43
        request = self.broker.prepare(
            "security.level.configure", {"level": "full-root"}, self.peer,
        )
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(request["token"], self.peer, authorized=False)
        result = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(result["securityLevel"], "full-root")
        self.assertEqual(self.sudoers.stat().st_mode & 0o777, 0o440)

    def test_gateway_attribution_policy_and_narrow_expiring_task_grant(self):
        root = Path(self.temporary.name)
        configured = json.loads(self.config.read_text())
        configured.update({
            "securityLevel": "full-root",
            "agentPolicies": {
                "requireTrustedAttribution": True,
                "defaultAllow": [],
                "agents": {"main": ["*"]},
            },
            "taskGrants": {
                "grantableActions": ["service.manage", "system.time.configure"],
            },
        })
        self.config.write_text(json.dumps(configured))
        proc_root = root / "proc"
        (proc_root / "4242").mkdir(parents=True)
        (proc_root / "4242" / "cgroup").write_text(
            "0::/user.slice/user-1000.slice/user@1000.service/app.slice/openclaw-gateway.service\n"
        )
        broker = Broker(
            config_path=self.config, state_dir=root / "policy-state",
            audit_path=root / "policy-audit.jsonl", preferences_path=root / "policy-preferences.json",
            boot_id_path=self.boot_id, uptime_path=self.uptime,
            sudoers_path=self.sudoers, full_root_sudoers_path=self.full_root_sudoers,
            proc_root=proc_root, runner=self.runner, recovery=self.recovery,
            clock=lambda: self.clock_value, token_factory=lambda: "g" * 43,
        )
        child = {"agentId": "worker", "sessionKey": "agent:worker:task", "runId": "child-1"}
        with self.assertRaisesRegex(BrokerError, "not allowed"):
            broker.prepare(
                "service.manage", {"service": "sshd.service", "operation": "restart"},
                self.peer, child,
            )
        grant_request = broker.prepare(
            "task.grant.create", {
                "agentId": "worker", "runId": "child-1",
                "actions": ["service.manage"], "expiresSeconds": 60,
            }, self.peer,
            {"agentId": "main", "sessionKey": "agent:main:main", "runId": "parent-1"},
        )
        grant = broker.commit(grant_request["token"], self.peer, authorized=False)
        self.assertEqual(grant["actions"], ["service.manage"])
        child_request = broker.prepare(
            "service.manage", {"service": "sshd.service", "operation": "restart"},
            self.peer, child,
        )
        self.assertEqual(child_request["requester"]["attribution"], "gateway-attested")
        with self.assertRaisesRegex(BrokerError, "not allowed"):
            broker.prepare(
                "system.time.configure", {"timezone": "UTC", "clockFormat": "12h"},
                self.peer, child,
            )
        self.clock_value += 61
        with self.assertRaisesRegex(BrokerError, "not allowed"):
            broker.prepare(
                "service.manage", {"service": "sshd.service", "operation": "restart"},
                self.peer, child,
            )

    def test_configured_agent_policy_rejects_self_reported_identity(self):
        configured = json.loads(self.config.read_text())
        configured["agentPolicies"] = {
            "requireTrustedAttribution": True, "defaultAllow": [], "agents": {"main": ["*"]},
        }
        self.config.write_text(json.dumps(configured))
        broker = Broker(
            config_path=self.config, state_dir=Path(self.temporary.name) / "untrusted-state",
            audit_path=Path(self.temporary.name) / "untrusted-audit.jsonl",
            preferences_path=Path(self.temporary.name) / "untrusted-preferences.json",
            boot_id_path=self.boot_id, uptime_path=self.uptime,
            runner=self.runner, recovery=self.recovery, clock=lambda: self.clock_value,
        )
        with self.assertRaisesRegex(BrokerError, "Trusted Gateway"):
            broker.prepare(
                "service.manage", {"service": "sshd.service", "operation": "restart"},
                self.peer, {"agentId": "main", "sessionKey": "agent:main:main", "runId": "r1"},
            )

    def test_interrupted_service_change_reconciles_verified_final_state(self):
        request = self.broker.prepare(
            "service.manage", {"service": "tailscaled.service", "operation": "stop"}, self.peer,
        )
        path = self.broker._pending_path(request["token"])
        request.update({"state": "executing", "previous": {"activeState": "active"}})
        self.broker._write_json(path, request)
        recovered = Broker(
            config_path=self.config,
            state_dir=Path(self.temporary.name) / "state",
            audit_path=Path(self.temporary.name) / "audit.jsonl",
            preferences_path=Path(self.temporary.name) / "preferences.json",
            boot_id_path=self.boot_id,
            uptime_path=self.uptime,
            runner=self.runner,
            recovery=self.recovery,
            clock=lambda: self.clock_value,
        ).get_action(request["actionId"])
        self.assertEqual(recovered["state"], "complete")
        self.assertTrue(recovered["reconciled"])

    def test_interrupted_service_restart_is_not_inferred_from_active_state(self):
        request = self.broker.prepare(
            "service.manage", {"service": "sshd.service", "operation": "restart"}, self.peer,
        )
        path = self.broker._pending_path(request["token"])
        request.update({"state": "executing", "previous": {"activeState": "active"}})
        self.broker._write_json(path, request)
        recovered = Broker(
            config_path=self.config,
            state_dir=Path(self.temporary.name) / "state",
            audit_path=Path(self.temporary.name) / "audit.jsonl",
            preferences_path=Path(self.temporary.name) / "preferences.json",
            boot_id_path=self.boot_id,
            uptime_path=self.uptime,
            runner=self.runner,
            recovery=self.recovery,
            clock=lambda: self.clock_value,
        ).get_action(request["actionId"])
        self.assertEqual(recovered["state"], "failed")
        self.assertTrue(recovered["reconciled"])
        self.assertIn("could not be verified", recovered["error"])

    def test_openclaw_update_is_exact_approved_and_verified(self):
        with self.assertRaisesRegex(BrokerError, "accepts no parameters"):
            self.broker.prepare("openclaw.update", {"version": "latest"}, self.peer)
        request = self.broker.prepare("openclaw.update", {}, self.peer)
        self.assertIn("2026.8.2", request["summary"])
        # Production verifies the immutable root-owned package.json. Unit tests
        # patch the path constant through a temporary package tree.
        import clawosd_core
        real_path = clawosd_core.Path
        package = Path(self.temporary.name) / "openclaw-package.json"
        package.write_text('{"version":"2026.8.2"}')
        config = Path(self.temporary.name) / ".openclaw" / "openclaw.json"
        config.parent.mkdir()
        config.write_text('{"agents":{"defaults":{"model":{"primary":"ollama-cloud/kimi-k2.5:cloud"}}}}')
        def test_path(value):
            if value == "/usr/lib/node_modules/openclaw/package.json":
                return package
            if value == "/home/clawos":
                return real_path(self.temporary.name)
            return real_path(value)
        clawosd_core.Path = test_path
        try:
            result = self.broker.commit(request["token"], self.peer, authorized=True)
        finally:
            clawosd_core.Path = real_path
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["installedVersion"], "2026.8.2")
        self.assertEqual(self.runner.commands[0][-5:], [
            "/usr/bin/npm", "install", "--global",
            "--allow-scripts=openclaw,@google/genai,tree-sitter-bash,protobufjs",
            "openclaw@2026.8.2"
        ])
        commands = [" ".join(command) for command in self.runner.commands]
        self.assertTrue(any(
            "--machine=clawos@.host --user is-active openclaw-gateway.service" in command
            for command in commands
        ))
        self.assertTrue(any(
            "plugins enable clawos-system --accept-capabilities" in command
            for command in commands
        ))
        self.assertFalse(any("openclaw models set" in command for command in commands))
        self.assertEqual(json.loads(config.read_text())["agents"]["defaults"]["model"]["primary"],
                         "ollama-cloud/kimi-k2.5:cloud")
        self.assertTrue(any(
            "openclaw update repair --yes --accept-capabilities --json --no-restart" in command
            for command in commands
        ))
        self.assertTrue(any(
            command.endswith("/usr/lib/clawos/clawos-refresh-agent-ui")
            for command in commands
        ))

    def test_failed_change_retains_recovery_and_can_stage_rollback(self):
        self.runner.fail = True
        request = self.broker.prepare("package.install", {"package": "tree"}, self.peer)
        failed = self.broker.commit(request["token"], self.peer, authorized=True)
        self.assertEqual(failed["state"], "failed")
        self.assertTrue(failed["rollbackAvailable"])
        self.runner.fail = False
        rollback = self.broker.prepare(
            "recovery.rollback", {"snapshotId": failed["snapshotId"]}, self.peer,
        )
        self.broker.config["securityLevel"] = "full-root"
        with self.assertRaisesRegex(BrokerError, "Polkit"):
            self.broker.commit(rollback["token"], self.peer, authorized=False)
        self.assertEqual(self.recovery.staged, [])
        recovered = self.broker.commit(rollback["token"], self.peer, authorized=True)
        self.assertEqual(recovered["state"], "complete")
        self.assertTrue(recovered["rebootRequired"])
        self.assertEqual(self.recovery.staged, [failed["snapshotId"]])

    def test_audit_never_contains_bearer_token(self):
        request = self.broker.prepare("package.install", {"package": "tree"}, self.peer)
        self.broker.cancel(request["token"], self.peer)
        audit = self.broker.audit_path.read_text()
        self.assertNotIn(request["token"], audit)
        events = [json.loads(line)["event"] for line in audit.splitlines()]
        self.assertEqual(events, ["prepared", "cancelled"])


if __name__ == "__main__":
    unittest.main()
