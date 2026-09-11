#!/usr/bin/env python3
"""Pure, testable core for the ClawOS privileged action broker."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import time
import uuid
from pathlib import Path


API_VERSION = 1
PACKAGE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9@._+\-]{0,63}$")
VERSION_PATTERN = re.compile(r"^[0-9][0-9A-Za-z._+\-]{0,63}$")
USER_PATTERN = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
AGENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
ACTION_TYPES = {
    "openclaw.update", "package.install", "recovery.rollback",
    "power.schedule", "role.switch", "security.level.configure",
    "service.manage", "system.time.configure", "task.grant.create",
}
HIGH_IMPACT_ACTIONS = {
    "recovery.rollback", "power.schedule", "role.switch", "security.level.configure",
}
TIMEZONE_PATTERN = re.compile(r"^[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+){0,3}$")


class BrokerError(RuntimeError):
    pass


def account_uid(name):
    # Resolve root-owned configuration through the OS account database, never
    # through caller context or a caller-supplied numeric UID.
    if not isinstance(name, str) or not USER_PATTERN.fullmatch(name):
        raise BrokerError("Invalid configured broker account.")
    try:
        import pwd
        return pwd.getpwnam(name).pw_uid
    except (ImportError, KeyError) as error:
        raise BrokerError("Configured broker account is unavailable.") from error


class CommandRunner:
    def run(self, argv, timeout=900):
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PATH": "/usr/bin:/usr/sbin", "LANG": "C.UTF-8"},
        )
        if result.returncode:
            message = (result.stderr or result.stdout or "operation failed").strip()
            raise BrokerError(message[-1200:])
        return result.stdout


class BtrfsRecovery:
    def __init__(self, runner=None, snapshot_root="/.snapshots", mount_root="/run/clawosd/btrfs-top"):
        self.runner = runner or CommandRunner()
        self.snapshot_root = Path(snapshot_root)
        self.mount_root = Path(mount_root)

    def create(self, action_id):
        fstype = self.runner.run(["/usr/bin/findmnt", "-n", "-o", "FSTYPE", "/"]).strip()
        if fstype != "btrfs":
            raise BrokerError("A Btrfs recovery point is required before this action.")
        snapshot_id = f"clawosd-{action_id}"
        destination = self.snapshot_root / snapshot_id
        if destination.exists():
            raise BrokerError("Recovery point already exists.")
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        self.runner.run(["/usr/bin/btrfs", "subvolume", "snapshot", "-r", "/", str(destination)])
        return snapshot_id

    def stage(self, snapshot_id):
        if not re.fullmatch(r"clawosd-[0-9a-f-]{36}", snapshot_id or ""):
            raise BrokerError("Invalid recovery point.")
        snapshot = self.snapshot_root / snapshot_id
        if not snapshot.exists():
            raise BrokerError("Recovery point does not exist.")
        source = re.sub(r"\[.*\]$", "", self.runner.run([
            "/usr/bin/findmnt", "-n", "-o", "SOURCE", "/",
        ]).strip())
        if not source.startswith("/"):
            raise BrokerError("Could not resolve the installed Btrfs block device.")
        top = self.mount_root
        top.mkdir(parents=True, exist_ok=True)
        self.runner.run(["/usr/bin/mount", "-t", "btrfs", "-o", "subvolid=5", source, str(top)])
        failed = top / f"@failed-{int(time.time())}"
        try:
            if not (top / "@").exists() or not (top / "@snapshots" / snapshot_id).exists():
                raise BrokerError("The installed ClawOS Btrfs layout is unavailable.")
            os.rename(top / "@", failed)
            try:
                self.runner.run([
                    "/usr/bin/btrfs", "subvolume", "snapshot",
                    str(top / "@snapshots" / snapshot_id), str(top / "@"),
                ])
            except Exception:
                os.rename(failed, top / "@")
                raise
        finally:
            self.runner.run(["/usr/bin/umount", str(top)])
        return {"snapshotId": snapshot_id, "rebootRequired": True, "failedRoot": failed.name}


class Broker:
    def __init__(
        self,
        config_path="/etc/clawos/clawosd.json",
        state_dir="/var/lib/clawosd",
        audit_path="/var/log/clawos/audit.jsonl",
        preferences_path="/etc/clawos/preferences.json",
        boot_id_path="/proc/sys/kernel/random/boot_id",
        uptime_path="/proc/uptime",
        sudoers_path="/etc/sudoers.d/90-clawos-full-root",
        full_root_sudoers_path="/etc/clawos/full-root.sudoers",
        proc_root="/proc",
        runner=None,
        recovery=None,
        clock=None,
        token_factory=None,
    ):
        self.config_path = Path(config_path)
        self.state_dir = Path(state_dir)
        self.pending_dir = self.state_dir / "pending"
        self.grants_dir = self.state_dir / "grants"
        self.audit_path = Path(audit_path)
        self.preferences_path = Path(preferences_path)
        self.boot_id_path = Path(boot_id_path)
        self.uptime_path = Path(uptime_path)
        self.sudoers_path = Path(sudoers_path)
        self.full_root_sudoers_path = Path(full_root_sudoers_path)
        self.proc_root = Path(proc_root)
        self.runner = runner or CommandRunner()
        self.recovery = recovery or BtrfsRecovery(self.runner)
        self.clock = clock or time.time
        self.token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self.config = self._load_config()
        self.pending_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.grants_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._reconcile_interrupted()

    def _load_config(self):
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise BrokerError(f"Invalid root-owned broker configuration: {error}") from error
        if config.get("version") != 1:
            raise BrokerError("Unsupported broker configuration version.")
        if config.get("securityLevel") not in {"full-user-approvals", "full-root", "user-limited"}:
            raise BrokerError("Invalid security level.")
        return config

    def _token_key(self, token):
        if not isinstance(token, str) or len(token) < 32:
            raise BrokerError("Invalid approval token.")
        return hashlib.sha256(token.encode()).hexdigest()

    def _pending_path(self, token):
        return self.pending_dir / f"{self._token_key(token)}.json"

    def _write_json(self, path, value):
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        with open(temporary, "x", encoding="utf-8") as destination:
            os.fchmod(destination.fileno(), 0o600)
            json.dump(value, destination, separators=(",", ":"), sort_keys=True)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)

    def _write_public_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        with open(temporary, "x", encoding="utf-8") as destination:
            os.fchmod(destination.fileno(), 0o644)
            json.dump(value, destination, separators=(",", ":"), sort_keys=True)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)

    def _write_mode_file(self, path, content, mode):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        with open(temporary, "x", encoding="utf-8") as destination:
            os.fchmod(destination.fileno(), mode)
            destination.write(content)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)

    def _audit(self, event, record):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        payload = {
            "version": 1,
            "observedAt": int(self.clock()),
            "event": event,
            **record,
        }
        descriptor = os.open(self.audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
        try:
            os.write(descriptor, (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode())
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _requester(self, peer, context=None):
        context = {} if context is None else context
        if not isinstance(context, dict):
            raise BrokerError("Agent context must be an object.")
        for field, limit in (("agentId", 128), ("sessionKey", 256), ("runId", 128)):
            value = context.get(field, "")
            if not isinstance(value, str) or len(value) > limit:
                raise BrokerError("Invalid agent context field.")
        if context.get("agentId") and not AGENT_PATTERN.fullmatch(context["agentId"]):
            raise BrokerError("Invalid agent identity.")
        attribution = "self-reported" if any(context.values()) else "unavailable"
        uid, pid = int(peer.get("uid", -1)), int(peer.get("pid", -1))
        try:
            cgroup = (self.proc_root / str(pid) / "cgroup").read_text(encoding="utf-8")
            pattern = (rf"0::/user\.slice/user-{uid}\.slice/user@{uid}\.service/"
                       r"(?:[^/\n]+\.slice/)*openclaw-(?:gateway|node)\.service(?:/[^\n]*)?")
            if any(re.fullmatch(pattern, line) for line in cgroup.splitlines()):
                attribution = "gateway-attested"
        except (OSError, ValueError, TypeError):
            pass
        return {
            "peerUid": int(peer.get("uid", -1)),
            "peerPid": int(peer.get("pid", -1)),
            "agentId": str(context.get("agentId", ""))[:128],
            "sessionKey": str(context.get("sessionKey", ""))[:256],
            "runId": str(context.get("runId", ""))[:128],
            "attribution": attribution,
        }

    def _authorize_peer(self, peer):
        requester = self._requester(peer)
        uid = requester["peerUid"]
        owner = account_uid(self.config.get("openclaw", {}).get("ownerUser"))
        if uid in {0, owner}:
            return requester, True
        settings = self.config.get("openclaw", {})
        if (self.config["securityLevel"] == "user-limited" and
                uid == account_uid(settings.get("agentUser", "claw")) and
                requester["attribution"] == "gateway-attested"):
            return requester, False
        raise BrokerError("Caller is not a trusted ClawOS account/runtime.")

    def _grant_is_current(self, path):
        try:
            grant = json.loads(path.read_text(encoding="utf-8"))
            return grant.get("expiresAt", 0) > int(self.clock()) and grant.get("bootId") == self._boot_id()
        except (OSError, ValueError):
            return False

    def _active_grants(self, requester, action=None):
        active = []
        for path in sorted(self.grants_dir.glob("*.json")):
            if not self._grant_is_current(path):
                continue
            grant = json.loads(path.read_text(encoding="utf-8"))
            if grant.get("agentId") != requester.get("agentId") or grant.get("runId") != requester.get("runId"):
                continue
            if action is not None and action not in grant.get("actions", []):
                continue
            active.append(grant)
        return active

    def _enforce_agent_policy(self, requester, action):
        policy = self.config.get("agentPolicies")
        if requester.get("attribution") == "gateway-attested" and (
                not requester.get("agentId") or not isinstance(policy, dict)):
            raise BrokerError("Gateway actions require an explicit agent identity and policy.")
        if not isinstance(policy, dict) or not requester.get("agentId"):
            return
        if policy.get("requireTrustedAttribution", True) and requester.get("attribution") != "gateway-attested":
            raise BrokerError("Trusted Gateway execution attribution is required for agent system actions.")
        agents = policy.get("agents", {}) if isinstance(policy.get("agents"), dict) else {}
        allowed = agents.get(requester["agentId"], policy.get("defaultAllow", []))
        if not isinstance(allowed, list):
            allowed = []
        if "*" in allowed or action in allowed or self._active_grants(requester, action):
            return
        raise BrokerError(f"Agent {requester['agentId']} is not allowed to request {action}.")

    def status(self):
        return {
            "apiVersion": API_VERSION,
            "securityLevel": self.config["securityLevel"],
            # Answering D-Bus proves only broker availability. It does not
            # establish completed setup, an unlocked desktop, Gateway health,
            # or successful inference. Keep those observations explicit until
            # the shared startup-state collector supplies them.
            "state": "unknown",
            "brokerState": "ready",
            "readiness": {
                "setup": "unverified",
                "desktop": "unverified",
                "lock": "unverified",
                "gateway": "unverified",
                "model": "unverified",
            },
            "pendingCount": len(self.list_pending(include_tokens=False)),
            "activeGrantCount": sum(1 for path in self.grants_dir.glob("*.json") if self._grant_is_current(path)),
            "capabilities": sorted(ACTION_TYPES),
        }

    def _service_state(self, service):
        state = self.runner.run([
            "/usr/bin/systemctl", "show", "--property=ActiveState", "--value", service,
        ]).strip()
        return state if state in {"active", "activating", "deactivating", "failed", "inactive"} else "unknown"

    def _boot_id(self):
        try:
            value = self.boot_id_path.read_text(encoding="utf-8").strip()
            return str(uuid.UUID(value))
        except (OSError, ValueError, AttributeError, TypeError):
            return "unavailable"

    def _network_state(self):
        try:
            state = self.runner.run([
                "/usr/bin/nmcli", "--terse", "--fields", "STATE", "general",
            ]).strip()[:80]
            raw_devices = self.runner.run([
                "/usr/bin/nmcli", "--terse", "--fields", "DEVICE,TYPE,STATE", "device", "status",
            ])
            devices = []
            for line in raw_devices.splitlines()[:64]:
                parts = line.split(":", 2)
                if len(parts) == 3:
                    devices.append({"device": parts[0][:64], "type": parts[1][:32], "state": parts[2][:80]})
            return {"manager": "NetworkManager", "state": state or "unknown", "devices": devices}
        except BrokerError as error:
            return {"manager": "NetworkManager", "state": "unavailable", "devices": [], "error": str(error)[:240]}

    def _reconcile_interrupted(self):
        for path in sorted(self.pending_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if record.get("state") not in {"executing", "scheduled"}:
                    continue
                action = record.get("action")
                recovered = False
                deferred = False
                if action == "service.manage":
                    operation = record["parameters"]["operation"]
                    # A running service proves a completed start, and an
                    # inactive service proves a completed stop. It cannot
                    # prove that a restart crossed the stop/start boundary.
                    if operation in {"start", "stop"}:
                        expected = "inactive" if operation == "stop" else "active"
                        observed = self._service_state(record["parameters"]["service"])
                        if observed == expected:
                            record.update({"state": "complete", "activeState": observed, "reconciled": True})
                            recovered = True
                elif action == "system.time.configure":
                    timezone = self.runner.run([
                        "/usr/bin/timedatectl", "show", "--property=Timezone", "--value",
                    ]).strip()
                    try:
                        clock_format = json.loads(
                            self.preferences_path.read_text(encoding="utf-8")
                        ).get("clockFormat")
                    except (OSError, ValueError):
                        clock_format = None
                    if timezone == record["parameters"]["timezone"] and clock_format == record["parameters"]["clockFormat"]:
                        record.update({
                            "state": "complete", "timezone": timezone,
                            "clockFormat": clock_format, "reconciled": True,
                        })
                        recovered = True
                elif action == "power.schedule":
                    if self._boot_id() != record.get("bootIdBefore"):
                        record.update({"state": "complete", "reconciled": True, "bootIdAfter": self._boot_id()})
                        recovered = True
                    elif int(self.clock()) <= int(record.get("scheduledAt", 0)) + 60:
                        # The transient systemd timer may still be about to
                        # execute. Preserve the scheduled receipt until either
                        # a new boot proves success or the grace window expires.
                        deferred = True
                if deferred:
                    continue
                if recovered:
                    record["completedAt"] = int(self.clock())
                    self._write_json(path, record)
                    self._audit("reconciled-complete", {key: value for key, value in record.items() if key != "token"})
                    continue
                record.update({
                    "state": "failed",
                    "failedAt": int(self.clock()),
                    "error": "Action was interrupted and its requested final state could not be verified.",
                    "rollbackAvailable": bool(record.get("snapshotId")),
                    "reconciled": True,
                })
                self._write_json(path, record)
                self._audit("reconciled-failed", {key: value for key, value in record.items() if key != "token"})
            except Exception as error:
                # A malformed record must not prevent the root broker from
                # starting. It remains on disk for recovery inspection.
                self._audit("reconcile-error", {"path": path.name, "error": str(error)[:400]})

    def inspect(self):
        services = {
            service: self._service_state(service)
            for service in self.config.get("services", {}).get("allow", [])
        }
        try:
            preferences = json.loads(self.preferences_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            preferences = {}
        try:
            boot_id = self._boot_id()
            uptime_seconds = int(float(self.uptime_path.read_text(encoding="utf-8").split()[0]))
        except (OSError, ValueError, IndexError):
            boot_id, uptime_seconds = "unavailable", None
        return {
            "apiVersion": API_VERSION,
            "hostname": self.runner.run(["/usr/bin/hostnamectl", "--static"]).strip(),
            "kernel": self.runner.run(["/usr/bin/uname", "-r"]).strip(),
            "timezone": self.runner.run([
                "/usr/bin/timedatectl", "show", "--property=Timezone", "--value",
            ]).strip(),
            "clockFormat": preferences.get("clockFormat", "12h"),
            "securityLevel": self.config["securityLevel"],
            "bootId": boot_id,
            "uptimeSeconds": uptime_seconds,
            "services": services,
            "network": self._network_state(),
            "pendingCount": len(self.list_pending(include_tokens=False)),
            "observedAt": int(self.clock()),
        }

    def get_action(self, action_id):
        try:
            normalized_id = str(uuid.UUID(str(action_id)))
        except (ValueError, AttributeError, TypeError) as error:
            raise BrokerError("Invalid action ID.") from error
        for path in self.pending_dir.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if record.get("actionId") == normalized_id:
                record.pop("token", None)
                return record
        raise BrokerError("Action receipt is unavailable.")

    def requires_approval(self, action):
        return self.config["securityLevel"] != "full-root" or action in HIGH_IMPACT_ACTIONS

    def capabilities(self):
        requires_approval = self.config["securityLevel"] != "full-root"
        return {
            "apiVersion": API_VERSION,
            "actions": {
                "package.install": {
                    "parameters": {"package": "allowlisted package name"},
                    "targets": list(self.config.get("packages", {}).get("allow", [])),
                    "requiresApproval": requires_approval,
                    "recovery": "read-only Btrfs root snapshot",
                },
                "openclaw.update": {
                    "parameters": {},
                    "targetVersion": self.config.get("openclaw", {}).get("promotedVersion"),
                    "requiresApproval": requires_approval,
                    "recovery": "read-only Btrfs root snapshot",
                },
                "recovery.rollback": {
                    "parameters": {"snapshotId": "broker-issued recovery point"},
                    "requiresApproval": self.requires_approval("recovery.rollback"),
                    "recovery": "staged for next boot",
                },
                "system.time.configure": {
                    "parameters": {
                        "timezone": "IANA timezone, for example America/New_York",
                        "clockFormat": "12h or 24h",
                    },
                    "requiresApproval": requires_approval,
                    "recovery": "previous timezone and clock format recorded for reversal",
                },
                "service.manage": {
                    "parameters": {
                        "service": "root-owned allowlisted systemd service",
                        "operation": "start, stop, or restart",
                    },
                    "targets": list(self.config.get("services", {}).get("allow", [])),
                    "requiresApproval": requires_approval,
                    "recovery": "previous service active state recorded for reversal",
                },
                "power.schedule": {
                    "parameters": {"operation": "reboot or poweroff"},
                    "requiresApproval": self.requires_approval("power.schedule"),
                    "recovery": "scheduled asynchronously; receipt reconciled against the next boot identity",
                },
                "role.switch": {
                    "parameters": {"target": "standalone or node"},
                    "requiresApproval": self.requires_approval("role.switch"),
                    "recovery": "transaction restores the previous OpenClaw profile and services on failure",
                },
                "security.level.configure": {
                    "parameters": {"level": "full-root, full-user-approvals, or user-limited"},
                    "requiresApproval": self.requires_approval("security.level.configure"),
                    "recovery": "runtime identity and prior root policy are restored if activation fails",
                },
                "task.grant.create": {
                    "parameters": {
                        "agentId": "child agent id", "runId": "child run id",
                        "actions": "narrow typed-action list", "expiresSeconds": "60-3600",
                    },
                    "targets": list(self.config.get("taskGrants", {}).get("grantableActions", [])),
                    "requiresApproval": requires_approval,
                    "recovery": "expires automatically and never survives a reboot",
                },
            },
        }

    def _normalize(self, action, parameters):
        if action not in ACTION_TYPES or not isinstance(parameters, dict):
            raise BrokerError("Unknown typed action.")
        if action == "package.install":
            if set(parameters) != {"package"}:
                raise BrokerError("package.install accepts only package.")
            package = parameters.get("package")
            allowed = set(self.config.get("packages", {}).get("allow", []))
            if not isinstance(package, str) or not PACKAGE_PATTERN.fullmatch(package) or package not in allowed:
                raise BrokerError("Package is not in the root-owned ClawOS allowlist.")
            return {"package": package}
        if action == "openclaw.update":
            if parameters:
                raise BrokerError("openclaw.update accepts no parameters.")
            settings = self.config.get("openclaw", {})
            target = settings.get("promotedVersion")
            owner = settings.get("ownerUser")
            if not isinstance(target, str) or not VERSION_PATTERN.fullmatch(target):
                raise BrokerError("No valid OpenClaw release is promoted by this ClawOS build.")
            if not isinstance(owner, str) or not USER_PATTERN.fullmatch(owner):
                raise BrokerError("The OpenClaw owner account is invalid.")
            return {"targetVersion": target, "ownerUser": owner}
        if action == "system.time.configure":
            if set(parameters) != {"timezone", "clockFormat"}:
                raise BrokerError("system.time.configure accepts only timezone and clockFormat.")
            timezone = parameters.get("timezone")
            clock_format = parameters.get("clockFormat")
            if not isinstance(timezone, str) or not TIMEZONE_PATTERN.fullmatch(timezone):
                raise BrokerError("Timezone must be a valid IANA timezone name.")
            zoneinfo_root = Path("/usr/share/zoneinfo").resolve()
            zoneinfo_path = (zoneinfo_root / timezone).resolve()
            if zoneinfo_root not in zoneinfo_path.parents or not zoneinfo_path.is_file():
                raise BrokerError("Timezone is not installed on this ClawOS system.")
            if clock_format not in {"12h", "24h"}:
                raise BrokerError("clockFormat must be 12h or 24h.")
            return {"timezone": timezone, "clockFormat": clock_format}
        if action == "service.manage":
            if set(parameters) != {"service", "operation"}:
                raise BrokerError("service.manage accepts only service and operation.")
            service = parameters.get("service")
            operation = parameters.get("operation")
            allowed = set(self.config.get("services", {}).get("allow", []))
            if not isinstance(service, str) or service not in allowed:
                raise BrokerError("Service is not in the root-owned ClawOS allowlist.")
            if operation not in {"start", "stop", "restart"}:
                raise BrokerError("Service operation must be start, stop, or restart.")
            return {"service": service, "operation": operation}
        if action == "power.schedule":
            if set(parameters) != {"operation"}:
                raise BrokerError("power.schedule accepts only operation.")
            operation = parameters.get("operation")
            if operation not in {"reboot", "poweroff"}:
                raise BrokerError("Power operation must be reboot or poweroff.")
            return {"operation": operation}
        if action == "role.switch":
            if set(parameters) != {"target"}:
                raise BrokerError("role.switch accepts only target.")
            target = parameters.get("target")
            if target not in {"standalone", "node"}:
                raise BrokerError("Role target must be standalone or node.")
            return {"target": target}
        if action == "security.level.configure":
            if set(parameters) != {"level"}:
                raise BrokerError("security.level.configure accepts only level.")
            level = parameters.get("level")
            if level not in {"full-root", "full-user-approvals", "user-limited"}:
                raise BrokerError("Unknown ClawOS security level.")
            return {"level": level}
        if action == "task.grant.create":
            if set(parameters) != {"agentId", "runId", "actions", "expiresSeconds"}:
                raise BrokerError("task.grant.create accepts only agentId, runId, actions, and expiresSeconds.")
            agent_id, run_id = parameters.get("agentId"), parameters.get("runId")
            actions, expires_seconds = parameters.get("actions"), parameters.get("expiresSeconds")
            grantable = set(self.config.get("taskGrants", {}).get("grantableActions", []))
            if not isinstance(agent_id, str) or not AGENT_PATTERN.fullmatch(agent_id):
                raise BrokerError("Invalid task-grant agent ID.")
            if not isinstance(run_id, str) or not AGENT_PATTERN.fullmatch(run_id):
                raise BrokerError("Invalid task-grant run ID.")
            if not isinstance(actions, list) or not actions or len(actions) > 8:
                raise BrokerError("A narrow non-empty task-grant action list is required.")
            if any(not isinstance(item, str) or item not in grantable for item in actions):
                raise BrokerError("Task grant includes an action outside the root-owned grantable set.")
            if not isinstance(expires_seconds, int) or not 60 <= expires_seconds <= 3600:
                raise BrokerError("Task grant expiry must be between 60 and 3600 seconds.")
            return {
                "agentId": agent_id, "runId": run_id,
                "actions": sorted(set(actions)), "expiresSeconds": expires_seconds,
            }
        if set(parameters) != {"snapshotId"}:
            raise BrokerError("recovery.rollback accepts only snapshotId.")
        snapshot_id = parameters.get("snapshotId")
        if not re.fullmatch(r"clawosd-[0-9a-f-]{36}", snapshot_id or ""):
            raise BrokerError("Invalid recovery point.")
        return {"snapshotId": snapshot_id}

    def prepare(self, action, parameters, peer, context=None):
        self._authorize_peer(peer)
        normalized = self._normalize(action, parameters)
        requester = self._requester(peer, context)
        self._enforce_agent_policy(requester, action)
        token = self.token_factory()
        action_id = str(uuid.uuid4())
        now = int(self.clock())
        expires = now + min(max(int(self.config.get("approvalExpiresSeconds", 120)), 30), 300)
        if action == "package.install":
            package = normalized["package"]
            summary = f"Install signed Arch package {package}"
            effects = [f"Run pacman --needed -S {package}", "May change system files and services"]
            recovery_text = "Create a read-only Btrfs root snapshot before installation"
        elif action == "openclaw.update":
            target = normalized["targetVersion"]
            summary = f"Update OpenClaw to ClawOS-promoted release {target}"
            effects = [
                f"Replace the root-owned OpenClaw package with version {target}",
                "Verify the installed version and restart the local Gateway",
            ]
            recovery_text = "Create a read-only Btrfs root snapshot before replacing OpenClaw"
        elif action == "recovery.rollback":
            summary = f"Restore recovery point {normalized['snapshotId']} on next boot"
            effects = ["Replace the next-boot root subvolume", "Require a restart"]
            recovery_text = "Keep the current root as a failed-root recovery subvolume"
        elif action == "system.time.configure":
            summary = f"Set system timezone to {normalized['timezone']} and use a {normalized['clockFormat']} clock"
            effects = [
                f"Set the system timezone to {normalized['timezone']}",
                f"Change the ClawOS shell clock to {normalized['clockFormat']}",
            ]
            recovery_text = "Record the previous timezone and clock format in the audit receipt"
        elif action == "service.manage":
            summary = f"{normalized['operation'].capitalize()} system service {normalized['service']}"
            effects = [
                f"Run systemctl {normalized['operation']} {normalized['service']}",
                "Verify the resulting systemd active state",
            ]
            recovery_text = "Record the previous service active state in the audit receipt"
        elif action == "role.switch":
            summary = f"Switch this machine to {normalized['target'].capitalize()} role"
            effects = [
                "Activate the separately enrolled OpenClaw role profile",
                "Stop the previous Gateway or node service and verify the target service",
            ]
            recovery_text = "Restore the previous profile and services if target validation fails"
        elif action == "security.level.configure":
            summary = f"Change machine security level to {normalized['level']}"
            effects = [
                "Select the OpenClaw runtime identity and machine authority ceiling",
                "Install or remove the passwordless-root policy as required",
            ]
            recovery_text = "Restore the previous runtime identity and authority policy if activation fails"
        elif action == "task.grant.create":
            summary = f"Grant {normalized['agentId']} temporary task-scoped machine actions"
            effects = [
                f"Allow only: {', '.join(normalized['actions'])}",
                f"Bind the grant to run {normalized['runId']} for {normalized['expiresSeconds']} seconds",
            ]
            recovery_text = "Grant expires automatically and is invalid after reboot"
        else:
            summary = "Restart ClawOS" if normalized["operation"] == "reboot" else "Shut down ClawOS"
            effects = [
                f"Schedule systemctl {normalized['operation']} after returning this receipt",
                "End all running local work and the graphical session",
            ]
            recovery_text = "Reconcile the receipt against the next boot identity"
        record = {
            "actionId": action_id,
            "token": token,
            "action": action,
            "parameters": normalized,
            "summary": summary,
            "effects": effects,
            "recovery": recovery_text,
            "createdAt": now,
            "bootId": self._boot_id(),
            "expiresAt": expires,
            "state": "pending",
            "requiresApproval": self.requires_approval(action),
            "impact": "high" if action in HIGH_IMPACT_ACTIONS else "routine",
            "requester": requester,
        }
        self._write_json(self._pending_path(token), record)
        self._audit("prepared", {key: value for key, value in record.items() if key != "token"})
        return record

    def list_pending(self, include_tokens=True):
        records = []
        for path in sorted(self.pending_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                if record.get("state") != "pending":
                    continue
                if (record.get("expiresAt", 0) <= int(self.clock()) or
                        record.get("bootId") != self._boot_id()):
                    record["state"] = "expired"
                    self._write_json(path, record)
                    self._audit("expired", {key: value for key, value in record.items() if key != "token"})
                    continue
                if not include_tokens:
                    record.pop("token", None)
                records.append(record)
            except (OSError, ValueError):
                continue
        return records

    def _check_record_access(self, record, requester, administrator):
        issuer = record.get("requester")
        uid = issuer.get("peerUid") if isinstance(issuer, dict) else None
        settings = self.config.get("openclaw", {})
        issuers = {0, account_uid(settings.get("ownerUser"))}
        if self.config["securityLevel"] == "user-limited":
            issuers.add(account_uid(settings.get("agentUser", "claw")))
        if type(uid) is not int or uid not in issuers:
            raise BrokerError("Approval request has no trusted requester binding.")
        if not administrator and uid != requester["peerUid"]:
            raise BrokerError("Approval request belongs to another account.")

    def pending_for_peer(self, token, peer, *, enforce_policy=True):
        requester, administrator = self._authorize_peer(peer)
        path = self._pending_path(token)
        if not path.exists():
            raise BrokerError("Approval token is unavailable or already used.")
        record = json.loads(path.read_text(encoding="utf-8"))
        self._check_record_access(record, requester, administrator)
        if (self._boot_id() == "unavailable" or record.get("bootId") != self._boot_id() or
                record.get("state") != "pending" or record.get("expiresAt", 0) <= int(self.clock())):
            raise BrokerError("Approval token expired, was already used, or belongs to another boot.")
        # A grant can expire or policy can change while approval is pending.
        if enforce_policy:
            self._enforce_agent_policy(record["requester"], record["action"])
        return record

    def list_pending_for_peer(self, peer):
        requester, administrator = self._authorize_peer(peer)
        visible = []
        for record in self.list_pending():
            try:
                self._check_record_access(record, requester, administrator)
            except BrokerError:
                continue
            visible.append(record)
        return visible

    def cancel(self, token, peer):
        record = self.pending_for_peer(token, peer, enforce_policy=False)
        path = self._pending_path(token)
        record["state"] = "cancelled"
        record["cancelledBy"] = self._requester(peer)
        self._write_json(path, record)
        self._audit("cancelled", {key: value for key, value in record.items() if key != "token"})
        return {"actionId": record["actionId"], "state": "cancelled"}

    def commit(self, token, peer, authorized=False):
        record = self.pending_for_peer(token, peer)
        path = self._pending_path(token)
        public = {key: value for key, value in record.items() if key != "token"}
        if record.get("state") != "pending" or record.get("expiresAt", 0) <= int(self.clock()):
            self._audit("commit-rejected", {**public, "reason": "expired-or-used"})
            raise BrokerError("Approval token expired or was already used.")
        if self.requires_approval(record["action"]) and not authorized:
            self._audit("commit-rejected", {**public, "reason": "polkit-authorization-required"})
            raise BrokerError("Local Polkit authorization is required.")
        record["state"] = "executing"
        record["committedBy"] = self._requester(peer)
        self._write_json(path, record)
        snapshot_id = None
        try:
            if record["action"] == "package.install":
                snapshot_id = self.recovery.create(record["actionId"])
                record["snapshotId"] = snapshot_id
                self._write_json(path, record)
                self.runner.run([
                    "/usr/bin/pacman", "--noconfirm", "--needed", "-S",
                    record["parameters"]["package"],
                ])
                result = {"state": "complete", "rebootRequired": False, "snapshotId": snapshot_id}
            elif record["action"] == "openclaw.update":
                snapshot_id = self.recovery.create(record["actionId"])
                record["snapshotId"] = snapshot_id
                self._write_json(path, record)
                target = record["parameters"]["targetVersion"]
                owner = record["parameters"]["ownerUser"]
                update_unit = f"clawos-openclaw-update-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", "--collect",
                    "--service-type=exec", f"--unit={update_unit}",
                    "/usr/bin/npm", "install", "--global",
                    "--allow-scripts=openclaw,@google/genai,tree-sitter-bash,protobufjs",
                    f"openclaw@{target}",
                ], timeout=1800)
                package_json = Path("/usr/lib/node_modules/openclaw/package.json")
                try:
                    installed = json.loads(package_json.read_text(encoding="utf-8")).get("version")
                except (OSError, ValueError) as error:
                    raise BrokerError(f"Could not verify the OpenClaw package: {error}") from error
                if installed != target:
                    raise BrokerError(
                        f"OpenClaw version verification failed: expected {target}, got {str(installed)[:160]}"
                    )
                uid = self.runner.run(["/usr/bin/id", "-u", owner]).strip()
                if not uid.isdigit():
                    raise BrokerError("Could not resolve the OpenClaw owner account.")
                passwd = self.runner.run(["/usr/bin/getent", "passwd", owner]).strip().split(":")
                if len(passwd) != 7 or not passwd[5].startswith("/"):
                    raise BrokerError("Could not resolve the OpenClaw owner home directory.")
                owner_home = passwd[5]
                gateway_scope = f"{owner}@.host"
                self.runner.run([
                    "/usr/bin/systemctl", f"--machine={gateway_scope}", "--user",
                    "stop", "openclaw-gateway.service",
                ], timeout=120)
                # Provider/model selection belongs to the user and OpenClaw setup.
                # Runtime updates must never silently replace that selection.
                consent_unit = f"clawos-openclaw-consent-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", "--collect",
                    "--service-type=exec", f"--uid={owner}", f"--setenv=HOME={owner_home}",
                    f"--unit={consent_unit}", "/usr/bin/openclaw", "plugins", "enable",
                    "clawos-system", "--accept-capabilities",
                ], timeout=300)
                repair_unit = f"clawos-openclaw-repair-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", "--collect",
                    "--service-type=exec", f"--uid={owner}", f"--setenv=HOME={owner_home}",
                    "--setenv=OPENCLAW_SERVICE_REPAIR_POLICY=external", f"--unit={repair_unit}",
                    "/usr/bin/openclaw", "update", "repair", "--yes",
                    "--accept-capabilities", "--json", "--no-restart",
                ], timeout=1800)
                self.runner.run([
                    "/usr/bin/systemctl", f"--machine={gateway_scope}", "--user",
                    "restart", "openclaw-gateway.service",
                ], timeout=120)
                active = self.runner.run([
                    "/usr/bin/systemctl", f"--machine={gateway_scope}", "--user",
                    "is-active", "openclaw-gateway.service",
                ], timeout=120).strip()
                if active != "active":
                    raise BrokerError(f"OpenClaw Gateway did not become active: {active[:160]}")
                refresh_unit = f"clawos-openclaw-ui-refresh-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", "--collect",
                    "--service-type=exec", f"--uid={owner}", f"--unit={refresh_unit}",
                    "/usr/lib/clawos/clawos-refresh-agent-ui",
                ], timeout=120)
                result = {
                    "state": "complete", "rebootRequired": False,
                    "snapshotId": snapshot_id, "installedVersion": target,
                }
            elif record["action"] == "recovery.rollback":
                result = {"state": "complete", **self.recovery.stage(record["parameters"]["snapshotId"])}
            elif record["action"] == "system.time.configure":
                previous_timezone = self.runner.run([
                    "/usr/bin/timedatectl", "show", "--property=Timezone", "--value",
                ]).strip() or "UTC"
                try:
                    previous_preferences = json.loads(self.preferences_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    previous_preferences = {}
                previous_clock_format = previous_preferences.get("clockFormat", "12h")
                record["previous"] = {
                    "timezone": previous_timezone,
                    "clockFormat": previous_clock_format,
                }
                self._write_json(path, record)
                timezone = record["parameters"]["timezone"]
                clock_format = record["parameters"]["clockFormat"]
                self.runner.run(["/usr/bin/timedatectl", "set-timezone", timezone])
                preferences = {**previous_preferences, "clockFormat": clock_format}
                self._write_public_json(self.preferences_path, preferences)
                observed_timezone = self.runner.run([
                    "/usr/bin/timedatectl", "show", "--property=Timezone", "--value",
                ]).strip()
                observed_preferences = json.loads(self.preferences_path.read_text(encoding="utf-8"))
                if observed_timezone != timezone or observed_preferences.get("clockFormat") != clock_format:
                    raise BrokerError("Time preference verification failed after applying the change.")
                result = {
                    "state": "complete",
                    "rebootRequired": False,
                    "timezone": observed_timezone,
                    "clockFormat": clock_format,
                    "previous": {
                        "timezone": previous_timezone,
                        "clockFormat": previous_clock_format,
                    },
                }
            elif record["action"] == "service.manage":
                service = record["parameters"]["service"]
                operation = record["parameters"]["operation"]
                previous_state = self._service_state(service)
                record["previous"] = {"activeState": previous_state}
                self._write_json(path, record)
                self.runner.run(["/usr/bin/systemctl", operation, service], timeout=120)
                observed_state = self._service_state(service)
                expected_state = "inactive" if operation == "stop" else "active"
                if observed_state != expected_state:
                    raise BrokerError(
                        f"Service verification failed: expected {expected_state}, got {observed_state}."
                    )
                result = {
                    "state": "complete",
                    "rebootRequired": False,
                    "service": service,
                    "operation": operation,
                    "activeState": observed_state,
                    "previous": {"activeState": previous_state},
                }
            elif record["action"] == "role.switch":
                openclaw_settings = self.config.get("openclaw", {})
                owner = (
                    openclaw_settings.get("agentUser")
                    if self.config["securityLevel"] == "user-limited"
                    else openclaw_settings.get("ownerUser")
                )
                if not isinstance(owner, str) or not USER_PATTERN.fullmatch(owner):
                    raise BrokerError("The OpenClaw owner account is invalid.")
                passwd = self.runner.run(["/usr/bin/getent", "passwd", owner]).strip().split(":")
                if len(passwd) != 7 or not passwd[5].startswith("/"):
                    raise BrokerError("Could not resolve the OpenClaw owner home directory.")
                if not passwd[2].isdigit():
                    raise BrokerError("Could not resolve the OpenClaw owner runtime directory.")
                runtime_dir = f"/run/user/{passwd[2]}"
                target = record["parameters"]["target"]
                unit = f"clawos-role-switch-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", "--wait", "--pipe", "--collect",
                    "--service-type=exec", f"--uid={owner}", f"--setenv=HOME={passwd[5]}",
                    f"--working-directory={passwd[5]}",
                    f"--setenv=XDG_RUNTIME_DIR={runtime_dir}",
                    f"--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path={runtime_dir}/bus",
                    f"--unit={unit}", "/usr/lib/clawos/clawos-role", "switch", target,
                ], timeout=300)
                result = {
                    "state": "complete", "rebootRequired": False,
                    "role": target, "transactional": True,
                }
            elif record["action"] == "security.level.configure":
                previous_level = self.config["securityLevel"]
                target_level = record["parameters"]["level"]
                record["previous"] = {"securityLevel": previous_level}
                self._write_json(path, record)
                if target_level != previous_level:
                    try:
                        self.runner.run([
                            "/usr/lib/clawos/clawos-security-mode", target_level,
                        ], timeout=600)
                        updated_config = {**self.config, "securityLevel": target_level}
                        self._write_public_json(self.config_path, updated_config)
                        if target_level == "full-root":
                            policy = self.full_root_sudoers_path.read_text(encoding="utf-8")
                            self._write_mode_file(self.sudoers_path, policy, 0o440)
                        else:
                            self.sudoers_path.unlink(missing_ok=True)
                        self.config = updated_config
                    except Exception:
                        try:
                            self.runner.run([
                                "/usr/lib/clawos/clawos-security-mode", previous_level,
                            ], timeout=600)
                        except Exception:
                            pass
                        raise
                result = {
                    "state": "complete", "rebootRequired": False,
                    "securityLevel": target_level,
                    "previous": {"securityLevel": previous_level},
                }
            elif record["action"] == "task.grant.create":
                grant_id = str(uuid.uuid4())
                grant = {
                    "version": 1, "grantId": grant_id,
                    "agentId": record["parameters"]["agentId"],
                    "runId": record["parameters"]["runId"],
                    "actions": record["parameters"]["actions"],
                    "createdAt": int(self.clock()),
                    "expiresAt": int(self.clock()) + record["parameters"]["expiresSeconds"],
                    "bootId": self._boot_id(),
                    "issuedBy": record["requester"],
                }
                self._write_json(self.grants_dir / f"{grant_id}.json", grant)
                result = {
                    "state": "complete", "rebootRequired": False,
                    "grantId": grant_id, "agentId": grant["agentId"],
                    "runId": grant["runId"], "actions": grant["actions"],
                    "expiresAt": grant["expiresAt"],
                }
            else:
                operation = record["parameters"]["operation"]
                record["bootIdBefore"] = self._boot_id()
                record["scheduledAt"] = int(self.clock())
                self._write_json(path, record)
                unit = f"clawos-power-{record['actionId']}"
                self.runner.run([
                    "/usr/bin/systemd-run", "--quiet", f"--unit={unit}",
                    "--on-active=3s", "/usr/bin/systemctl", operation,
                ], timeout=30)
                result = {
                    "state": "scheduled", "operation": operation,
                    "rebootRequired": operation == "reboot",
                    "bootIdBefore": record["bootIdBefore"],
                }
            record.update(result)
            if result["state"] == "scheduled":
                self._write_json(path, record)
                self._audit("scheduled", {key: value for key, value in record.items() if key != "token"})
                return {"actionId": record["actionId"], **result}
            record["completedAt"] = int(self.clock())
            self._write_json(path, record)
            self._audit("completed", {key: value for key, value in record.items() if key != "token"})
            return {"actionId": record["actionId"], **result}
        except Exception as error:
            record.update({
                "state": "failed",
                "error": str(error)[:1200],
                "snapshotId": snapshot_id,
                "rollbackAvailable": bool(snapshot_id),
            })
            self._write_json(path, record)
            self._audit("failed", {key: value for key, value in record.items() if key != "token"})
            return {
                "actionId": record["actionId"], "state": "failed",
                "error": record["error"], "snapshotId": snapshot_id,
                "rollbackAvailable": bool(snapshot_id),
            }
