#!/usr/bin/env python3
import json
import os
import pathlib
import stat
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[2]
SUBMIT = ROOT / "m1/profile-overlay/airootfs/usr/lib/clawos/clawos-agent-submit"
RUNNER = ROOT / "m1/profile-overlay/airootfs/usr/lib/clawos/clawos-agent-run"
REQUEST = ROOT / "m1/profile-overlay/airootfs/usr/lib/clawos/clawos-agent-request"


def executable(path, contents):
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


with tempfile.TemporaryDirectory(prefix="clawos-agent-queue-") as temporary:
    root = pathlib.Path(temporary)
    state = root / "state"
    args_log = root / "systemd-args.json"
    captured = root / "captured-message"
    fake_systemd = root / "systemd-run"
    fake_openclaw = root / "openclaw"
    fake_appctl = root / "appctl"
    fake_systemctl = root / "systemctl"

    executable(
        fake_systemd,
        "#!/usr/bin/env python3\nimport json,os,sys\n"
        "open(os.environ['ARGS_LOG'],'w').write(json.dumps(sys.argv[1:]))\n",
    )
    executable(
        fake_openclaw,
        "#!/usr/bin/env python3\nimport os,pathlib,sys\n"
        "source=sys.argv[sys.argv.index('--message-file')+1]\n"
        "pathlib.Path(os.environ['CAPTURED']).write_text(pathlib.Path(source).read_text())\n",
    )
    executable(
        fake_appctl,
        "#!/usr/bin/env python3\nimport os,pathlib,sys\n"
        "pathlib.Path(os.environ['APPCTL_LOG']).write_text(' '.join(sys.argv[1:]))\n",
    )
    executable(
        fake_systemctl,
        "#!/usr/bin/env python3\nimport sys\n"
        "raise SystemExit(0 if ('clawos-agent-request-' + 'c' * 32) in sys.argv[-1] else 3)\n",
    )

    secret_prompt = "private shelf request that must not enter argv"
    environment = {
        **os.environ,
        "XDG_STATE_HOME": str(state),
        "CLAWOS_SYSTEMD_RUN": str(fake_systemd),
        "CLAWOS_AGENT_RUNNER": str(RUNNER),
        "ARGS_LOG": str(args_log),
    }
    submitted = subprocess.run(
        [str(SUBMIT)], input=secret_prompt, text=True, capture_output=True,
        env=environment, timeout=15, check=True,
    )
    request_id = json.loads(submitted.stdout)["requestId"]
    request = state / "clawos/agent-requests" / f"{request_id}.txt"
    assert request.read_text(encoding="utf-8") == secret_prompt
    assert stat.S_IMODE(request.stat().st_mode) == 0o600
    assert secret_prompt not in args_log.read_text(encoding="utf-8")

    runner_environment = {
        **os.environ,
        "XDG_STATE_HOME": str(state),
        "CLAWOS_OPENCLAW": str(fake_openclaw),
        "CLAWOS_APPCTL": str(fake_appctl),
        "CAPTURED": str(captured),
        "APPCTL_LOG": str(root / "appctl.log"),
    }
    subprocess.run([str(RUNNER), str(request)], env=runner_environment, timeout=15, check=True)
    assert captured.read_text(encoding="utf-8") == secret_prompt
    assert not request.exists()
    receipt = json.loads((state / "clawos/agent-receipts" / f"{request_id}.json").read_text())
    assert receipt["status"] == "completed"
    assert secret_prompt not in json.dumps(receipt)

    failed_id = "f" * 32
    failed_request = state / "clawos/agent-requests" / f"{failed_id}.txt"
    failed_request.write_text("request expected to fail", encoding="utf-8")
    failed_request.chmod(0o600)
    executable(fake_openclaw, "#!/bin/sh\nexit 1\n")
    failed = subprocess.run(
        [str(RUNNER), str(failed_request)], env=runner_environment, timeout=15, check=False,
    )
    assert failed.returncode == 1
    assert not failed_request.exists()
    failed_receipt = json.loads(
        (state / "clawos/agent-receipts" / f"{failed_id}.json").read_text()
    )
    assert failed_receipt["status"] == "failed"
    assert (root / "appctl.log").read_text(encoding="utf-8") == (
        "attention A background Agent request failed"
    )

    wrong_mode_id = "e" * 32
    wrong_mode = state / "clawos/agent-requests" / f"{wrong_mode_id}.txt"
    wrong_mode.write_text("must be rejected", encoding="utf-8")
    wrong_mode.chmod(0o644)
    rejected = subprocess.run(
        [str(RUNNER), str(wrong_mode)], env=runner_environment, timeout=15, check=False,
    )
    assert rejected.returncode == 65
    assert wrong_mode.exists()

    active_id = "c" * 32
    active_request = state / "clawos/agent-requests" / f"{active_id}.txt"
    active_request.write_text("active work", encoding="utf-8")
    active_request.chmod(0o600)
    interrupted_id = "d" * 32
    interrupted_request = state / "clawos/agent-requests" / f"{interrupted_id}.txt"
    interrupted_request.write_text("private interrupted work", encoding="utf-8")
    interrupted_request.chmod(0o600)
    request_environment = {
        **environment,
        "CLAWOS_SYSTEMCTL": str(fake_systemctl),
    }
    listed = subprocess.run(
        [str(REQUEST), "list"], text=True, capture_output=True,
        env=request_environment, timeout=15, check=True,
    )
    interrupted = json.loads(listed.stdout)["requests"]
    assert [item["requestId"] for item in interrupted] == [interrupted_id]
    assert interrupted[0]["summary"] == "private interrupted work"

    subprocess.run(
        [str(REQUEST), "resume", interrupted_id], env=request_environment, timeout=15,
        capture_output=True, text=True, check=True,
    )
    resumed_args = args_log.read_text(encoding="utf-8")
    assert interrupted_id in resumed_args
    assert "private interrupted work" not in resumed_args

    discard_id = "b" * 32
    discard_request = state / "clawos/agent-requests" / f"{discard_id}.txt"
    discard_request.write_text("discard me privately", encoding="utf-8")
    discard_request.chmod(0o600)
    subprocess.run(
        [str(REQUEST), "discard", discard_id], env=request_environment, timeout=15,
        capture_output=True, text=True, check=True,
    )
    assert not discard_request.exists()
    discarded_receipt = json.loads(
        (state / "clawos/agent-receipts" / f"{discard_id}.json").read_text()
    )
    assert discarded_receipt["status"] == "discarded"
    assert "discard me privately" not in json.dumps(discarded_receipt)

print("ClawOS private Agent queue checks passed.")
