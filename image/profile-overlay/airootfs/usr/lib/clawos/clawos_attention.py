"""Shared, read-only work projection for Waybar and Work and decisions."""
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def read_json(path, default):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else default
    except (OSError, ValueError):
        return default


def seen_path():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "clawos/center-seen.json"


def acknowledge(kind, identifier):
    if kind not in {"taskIds", "noticeIds"} or not identifier:
        return
    destination = seen_path()
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    seen = read_json(destination, {})
    seen[kind] = list(dict.fromkeys([*seen.get(kind, []), identifier]))[-1000:]
    seen["version"] = 1
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w") as target:
            json.dump(seen, target)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def actionable_failure(task):
    detail = task.get("detail") if isinstance(task.get("detail"), dict) else {}
    return task.get("status") in {"failed", "timed_out", "lost"} and not (
        (task.get("runtime") == "cron" or task.get("taskKind") == "automation_run")
        and detail.get("status") == "skipped"
    )


def project(machine, approvals, tasks, interrupted, activity, seen, errors=()):
    active = [task for task in tasks if task.get("status") in {"queued", "running"}]
    failed = [task for task in tasks if actionable_failure(task)
              and (task.get("taskId") or task.get("id")) not in seen.get("taskIds", [])]
    recent = [task for task in tasks if task not in active][:10]
    concrete = len(machine) + len(approvals) + len(failed) + len(interrupted)
    attention = activity.get("attention") or {}
    notice = None
    if attention.get("count") and not concrete:
        identifier = attention.get("id") or hashlib.sha256(json.dumps(attention, sort_keys=True).encode()).hexdigest()
        if identifier not in seen.get("noticeIds", []):
            notice = {"id": identifier, "message": attention.get("message") or "Activity needs attention."}
    count = concrete + bool(notice) + len(errors)
    return {"machine": machine, "approvals": approvals, "tasks": tasks, "interrupted": interrupted,
            "active": active, "failed": failed, "recent": recent, "notice": notice,
            "errors": list(errors), "reviewCount": count}


def query(argv, keys):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=8, check=True)
    payload = json.loads(result.stdout)
    if isinstance(payload, dict):
        payload = next((payload[key] for key in keys if isinstance(payload.get(key), list)), None)
    if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
        raise ValueError("Invalid work response")
    return payload


def collect():
    ctl = os.environ.get("CLAWOS_CTL", "/usr/lib/clawos/clawosctl")
    openclaw = os.environ.get("CLAWOS_OPENCLAW", "/usr/bin/openclaw")
    requests = os.environ.get("CLAWOS_AGENT_REQUEST", "/usr/lib/clawos/clawos-agent-request")
    sources = {
        "machine": ([ctl, "pending"], ("pending", "requests")),
        "approvals": ([openclaw, "approvals", "pending", "--json"], ("pending", "approvals", "items")),
        "tasks": ([openclaw, "tasks", "list", "--json"], ("tasks", "items")),
        "interrupted": ([requests, "list"], ("requests",)),
    }
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    directory = runtime / "clawos"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    cache_path = directory / "work-snapshot.json"
    source_key = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    # Both surfaces share one private snapshot rather than launching duplicate CLIs.
    descriptor = os.open(directory / "work-snapshot.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cache = read_json(cache_path, {})
        if cache.get("sourceKey") == source_key and 0 <= time.monotonic() - cache.get("at", 0) < 5:
            values, errors = cache["values"], cache["errors"]
        else:
            values, errors = {}, []
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                jobs = {key: pool.submit(query, *args) for key, args in sources.items()}
                for key, job in jobs.items():
                    try:
                        values[key] = job.result()
                    except (OSError, ValueError, subprocess.SubprocessError):
                        values[key] = []
                        errors.append(f"Cannot read {key}. Refresh to retry; this is not an empty queue.")
            descriptor, temporary = tempfile.mkstemp(dir=directory)
            try:
                with os.fdopen(descriptor, "w") as target:
                    json.dump({"at": time.monotonic(), "sourceKey": source_key,
                               "values": values, "errors": errors}, target)
                os.replace(temporary, cache_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    activity = read_json(runtime / "clawos/activity.json", {})
    values['tasks'] = list(values['tasks'])
    for path in Path(os.environ.get('CLAWOS_DEPLOY_RECEIPTS_DIR', '/var/lib/clawos/deploy-receipts')).glob('*.json'):
        receipt = read_json(path, {})
        if not receipt.get('targetHash') or receipt.get('delivery') == 'delivered':
            continue
        state = receipt.get('state', 'unknown')
        failed = state in {'failed', 'recovery-required'}
        values['tasks'].append({'id': 'deploy-' + path.stem, 'deployment': True,
            'status': 'failed' if failed else 'running', 'runtime': 'clawos',
            'title': 'Runtime update' if state not in {'complete', 'rolled-back'} else 'Delivering update result',
            'progressSummary': f"Job {path.stem} · {state} · notification {receipt.get('delivery', 'pending')}"})
    return project(**values, activity=activity, seen=read_json(seen_path(), {}), errors=errors)


def bar(snapshot):
    count = snapshot["reviewCount"]
    active = len(snapshot["active"])
    return {
        "text": f"Review {count}" if count else (f"Working {active}" if active else "Work"),
        "class": "attention" if count else "normal",
        "tooltip": (f"{len(snapshot['machine'])} machine · {len(snapshot['approvals'])} approvals · "
                    f"{len(snapshot['failed'])} failed · {len(snapshot['interrupted'])} interrupted · "
                    f"{int(bool(snapshot['notice']))} notice · {len(snapshot['errors'])} unavailable\n"
                    "Open Work and decisions"),
    }


if __name__ == "__main__":
    print(json.dumps(bar(collect())))
