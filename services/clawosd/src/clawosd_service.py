#!/usr/bin/env python3
"""System D-Bus adapter for the ClawOS broker core."""

import json
import os
import sys

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

sys.path.insert(0, "/usr/lib/clawos/clawosd")
from clawosd_core import Broker, BrokerError  # noqa: E402


BUS_NAME = "org.clawos.System"
OBJECT_PATH = "/org/clawos/System"
INTERFACE = "org.clawos.System1"
POLKIT_ACTION = "org.clawos.system.commit"


class Service(dbus.service.Object):
    def __init__(self, bus):
        self.bus = bus
        self.broker = Broker()
        super().__init__(bus, OBJECT_PATH)

    def peer(self, sender):
        daemon = self.bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
        interface = dbus.Interface(daemon, "org.freedesktop.DBus")
        return {
            "uid": int(interface.GetConnectionUnixUser(sender)),
            "pid": int(interface.GetConnectionUnixProcessID(sender)),
        }

    def authorized(self, sender, record):
        if not self.broker.requires_approval(record["action"]):
            return True
        authority = dbus.Interface(
            self.bus.get_object("org.freedesktop.PolicyKit1", "/org/freedesktop/PolicyKit1/Authority"),
            "org.freedesktop.PolicyKit1.Authority",
        )
        subject = ("system-bus-name", {"name": dbus.String(sender)})
        details = {
            "polkit.message": dbus.String(record.get("summary", "Approve ClawOS system action")),
            "clawos.action-id": dbus.String(record.get("actionId", "")),
        }
        approved, _challenge, _details = authority.CheckAuthorization(
            subject, POLKIT_ACTION, details, dbus.UInt32(1), "", timeout=180,
        )
        return bool(approved)

    def encode(self, callback):
        try:
            return json.dumps({"ok": True, "result": callback()}, separators=(",", ":"))
        except (BrokerError, ValueError, OSError) as error:
            return json.dumps({"ok": False, "error": str(error)[:1200]}, separators=(",", ":"))

    @dbus.service.method(INTERFACE, out_signature="s")
    def GetStatus(self):
        return self.encode(self.broker.status)

    @dbus.service.method(INTERFACE, out_signature="s")
    def GetCapabilities(self):
        return self.encode(self.broker.capabilities)

    @dbus.service.method(INTERFACE, out_signature="s")
    def Inspect(self):
        return self.encode(self.broker.inspect)

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="s")
    def GetAction(self, action_id):
        return self.encode(lambda: self.broker.get_action(str(action_id)))

    @dbus.service.method(INTERFACE, out_signature="s", sender_keyword="sender")
    def ListPending(self, sender=None):
        return self.encode(lambda: self.broker.list_pending_for_peer(self.peer(sender)))

    @dbus.service.method(INTERFACE, in_signature="sss", out_signature="s", sender_keyword="sender")
    def PrepareAction(self, action, parameters_json, context_json, sender=None):
        return self.encode(lambda: self.broker.prepare(
            str(action), json.loads(str(parameters_json)), self.peer(sender), json.loads(str(context_json)),
        ))

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="s", sender_keyword="sender")
    def CancelAction(self, token, sender=None):
        return self.encode(lambda: self.broker.cancel(str(token), self.peer(sender)))

    @dbus.service.method(INTERFACE, in_signature="s", out_signature="s", sender_keyword="sender")
    def CommitAction(self, token, sender=None):
        def commit():
            peer = self.peer(sender)
            # Reject an untrusted caller before even requesting a Polkit dialog.
            record = self.broker.pending_for_peer(str(token), peer)
            return self.broker.commit(str(token), peer, self.authorized(sender, record))

        return self.encode(commit)


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    bus_name = dbus.service.BusName(BUS_NAME, bus, do_not_queue=True)
    service = Service(bus)
    GLib.MainLoop().run()
    return bus_name, service


if __name__ == "__main__":
    os.umask(0o077)
    main()
