#!/usr/bin/env python3
import json
import sys

import dbus


def result(raw):
    payload = json.loads(str(raw))
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "ClawOS broker request failed."))
    return payload["result"]


def main(argv):
    interface = dbus.Interface(
        dbus.SystemBus().get_object("org.clawos.System", "/org/clawos/System"),
        "org.clawos.System1",
    )
    command = argv[1] if len(argv) > 1 else "status"
    if command == "status":
        value = result(interface.GetStatus())
    elif command == "capabilities":
        value = result(interface.GetCapabilities())
    elif command == "inspect":
        value = result(interface.Inspect())
    elif command == "action" and len(argv) == 3:
        value = result(interface.GetAction(argv[2]))
    elif command == "pending":
        value = result(interface.ListPending())
    elif command == "prepare" and len(argv) in {4, 5}:
        context = argv[4] if len(argv) == 5 else "{}"
        value = result(interface.PrepareAction(argv[2], argv[3], context))
    elif command == "cancel" and len(argv) == 3:
        value = result(interface.CancelAction(argv[2]))
    elif command == "commit" and len(argv) == 3:
        # Package and OS transactions legitimately outlive D-Bus's short
        # default method timeout. clawosd remains the authoritative executor.
        value = result(interface.CommitAction(argv[2], timeout=1900))
    else:
        raise RuntimeError("Usage: clawosctl {status|capabilities|inspect|action ID|pending|prepare ACTION JSON [CONTEXT]|cancel TOKEN|commit TOKEN}")
    print(json.dumps(value, separators=(",", ":")))


try:
    main(sys.argv)
except Exception as error:
    print(f"clawosctl: {error}", file=sys.stderr)
    raise SystemExit(1)
