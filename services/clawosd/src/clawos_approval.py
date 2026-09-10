#!/usr/bin/env python3
import fcntl
import json
import os
import re
import subprocess
import threading
import sys

sys.path.insert(0, "/usr/lib/clawos")
from clawos_attention import collect, acknowledge, actionable_failure

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell  # noqa: E402


CTL = os.environ.get("CLAWOS_CTL", "/usr/lib/clawos/clawosctl")
OPENCLAW = os.environ.get("CLAWOS_OPENCLAW", "/usr/bin/openclaw")
APPCTL = os.environ.get("CLAWOS_APPCTL", "/usr/lib/clawos/clawos-appctl")
AGENT_REQUEST = os.environ.get("CLAWOS_AGENT_REQUEST", "/usr/lib/clawos/clawos-agent-request")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
TERMINAL_TASK_STATES = {"completed", "succeeded", "failed", "cancelled", "timed_out", "lost"}
CENTER_CSS = b"""
  * { font-family:'Inter Variable', 'Noto Sans', sans-serif; }
  #center-window { background:transparent; color:@claw_text; }
  #center-scrim { background:alpha(black, 0.64); }
  #center-panel { background:@claw_panel; border:1px solid @claw_line_strong; border-radius:12px; box-shadow:0 24px 70px alpha(black, 0.48); }
  #shell { padding:30px 34px; }
  #eyebrow, #section-label, #meta { color:@claw_quiet; font-family:'GeistMono Nerd Font'; font-size:11px; letter-spacing:1.5px; }
  #eyebrow { color:@claw_coral; }
  #title { font-family:'Inter Variable'; font-size:31px; font-weight:700; color:@claw_text; }
  #subtitle, #muted { color:@claw_muted; }
  #summary-card { background:@claw_surface; border:1px solid @claw_line; border-radius:10px; padding:14px 18px; }
  #summary-number { font-family:'Inter Variable'; font-size:22px; font-weight:700; color:@claw_text; }
  #card { background:@claw_surface; border:1px solid @claw_line_strong; border-radius:9px; padding:18px; }
  #card-title { font-family:'Inter Variable'; font-size:17px; font-weight:600; color:@claw_text; }
  #detail { color:@claw_muted; font-size:13px; }
  #primary { background:@claw_coral; color:@claw_canvas; border-radius:7px; padding:9px 16px; font-weight:700; }
  #quiet { background:transparent; color:@claw_text; border:1px solid @claw_line_strong; border-radius:7px; padding:9px 14px; }
  #quiet:hover { border-color:@claw_coral; }
  #header-icon, #header-back { min-height:34px; background:transparent; background-image:none; box-shadow:none; color:@claw_muted; border:1px solid transparent; border-radius:7px; padding:0 9px; }
  #header-icon { min-width:34px; padding:0; }
  #header-icon:hover, #header-back:hover { color:@claw_text; background:@claw_raised; border-color:@claw_line; }
  #danger { background:transparent; color:@claw_danger; border:1px solid alpha(@claw_danger, 0.45); border-radius:7px; padding:9px 14px; }
  #success { color:@claw_green; }
  #error { color:@claw_danger; }
  separator { background:@claw_line; min-height:1px; }
"""


def runtime_path(name):
    root = os.path.join(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"), "clawos")
    os.makedirs(root, mode=0o700, exist_ok=True)
    return os.path.join(root, name)


def state_path(name):
    root = os.path.join(
        os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state")),
        "clawos",
    )
    os.makedirs(root, mode=0o700, exist_ok=True)
    return os.path.join(root, name)


def claim_instance():
    descriptor = os.open(runtime_path("center.lock"), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        subprocess.run(
            ["/usr/bin/swaymsg", '[title="^ClawOS Center$"] focus'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        os.close(descriptor)
        return None
    return descriptor


def run_json(argv, timeout=8, optional=False):
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        if result.returncode:
            if optional:
                return None
            raise RuntimeError(result.stderr.strip() or "ClawOS request failed.")
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        if optional:
            return None
        raise RuntimeError(str(error)) from error


def run_action(argv, timeout=30):
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(str(error)) from error
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ClawOS action failed.")
    return {"ok": True}


def broker(*args):
    return run_json([CTL, *args], timeout=240)


def openclaw(*args, timeout=8, optional=False):
    return run_json([OPENCLAW, *args], timeout=timeout, optional=optional)


def rows(payload, *keys):
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def clean_text(value, fallback="", limit=600):
    if not isinstance(value, str):
        return fallback
    value = " ".join(value.split())
    return value[:limit] or fallback


def task_id(task):
    value = task.get("taskId") or task.get("id")
    return value if isinstance(value, str) and SAFE_ID.fullmatch(value) else None


def task_title(task):
    return clean_text(
        task.get("title") or task.get("task") or task.get("label") or task.get("kind") or task.get("runtime"),
        "Background work",
        100,
    )


def task_detail(task):
    return clean_text(
        task.get("progressSummary") or task.get("terminalSummary") or task.get("error"),
        "OpenClaw is tracking this work durably.",
    )


def approval_id(request):
    value = request.get("id") or request.get("approvalId")
    return value if isinstance(value, str) and SAFE_ID.fullmatch(value) else None


def approval_detail(request):
    nested = request.get("request") if isinstance(request.get("request"), dict) else {}
    command = nested.get("command") or nested.get("commandText") or request.get("command")
    summary = request.get("summary") or nested.get("summary") or command
    return clean_text(summary, "OpenClaw needs a decision before continuing.")


class CenterWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="ClawOS Center")
        self.set_name("center-window")
        self.set_default_size(1440, 900)
        self.set_resizable(False)
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.RIGHT, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_namespace(self, "clawos-center")
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key)

        provider = Gtk.CssProvider()
        with open("/etc/clawos/design-system.css", "rb") as design:
            provider.load_from_data(design.read() + CENTER_CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        overlay = Gtk.Overlay()
        scrim = Gtk.EventBox()
        scrim.set_name("center-scrim")
        scrim.connect("button-press-event", lambda *_: self.destroy())
        overlay.add(scrim)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.set_name("center-panel")
        screen = self.get_screen()
        panel_width = max(560, min(1040, screen.get_width() - 64))
        panel_height = max(520, min(740, screen.get_height() - 100))
        panel.set_size_request(panel_width, panel_height)
        panel.set_halign(Gtk.Align.CENTER)
        panel.set_valign(Gtk.Align.CENTER)
        overlay.add_overlay(panel)
        self.add(overlay)
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        shell.set_name("shell")
        panel.pack_start(shell, True, True, 0)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        header.set_size_request(-1, 86)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        eyebrow = Gtk.Label(label="CLAWOS · SYSTEM CENTER", xalign=0)
        eyebrow.set_name("eyebrow")
        heading.pack_start(eyebrow, False, False, 0)
        title = Gtk.Label(label="Work and decisions", xalign=0)
        title.set_name("title")
        heading.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(
            label="See what is running, resolve what is blocked, and return to the Agent canvas.", xalign=0,
        )
        subtitle.set_name("subtitle")
        heading.pack_start(subtitle, False, False, 0)
        header.pack_start(heading, True, True, 0)
        refresh = Gtk.Button()
        refresh.set_name("header-icon")
        refresh.set_valign(Gtk.Align.CENTER)
        refresh.add(self.radix_icon("reload.svg"))
        refresh.set_tooltip_text("Refresh work and decisions")
        refresh.get_accessible().set_name("Refresh work and decisions")
        refresh.connect("clicked", lambda *_: self.refresh())
        close = Gtk.Button()
        close.set_name("header-back")
        close.set_valign(Gtk.Align.CENTER)
        close_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        close_content.pack_start(self.radix_icon("arrow-left.svg"), False, False, 0)
        close_content.pack_start(Gtk.Label(label="Back"), False, False, 0)
        close.add(close_content)
        close.set_tooltip_text("Return to the previous work surface")
        close.connect("clicked", lambda *_: self.destroy())
        header.pack_end(close, False, False, 0)
        header.pack_end(refresh, False, False, 0)
        shell.pack_start(header, False, False, 0)

        self.summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        shell.pack_start(self.summary, False, False, 8)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scroller.add(self.content)
        shell.pack_start(scroller, True, True, 0)
        self.message = Gtk.Label(xalign=0)
        shell.pack_start(self.message, False, False, 0)
        self.refresh()

        self.refresh_timer = GLib.timeout_add_seconds(5, self.poll_work)

    def poll_work(self):
        if self.get_sensitive():
            self.refresh()
        return True

    def on_key(self, _window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    @staticmethod
    def clear(container):
        for child in container.get_children():
            container.remove(child)

    @staticmethod
    def label(value, name="muted", wrap=True):
        label = Gtk.Label(label=value, xalign=0)
        label.set_name(name)
        label.set_line_wrap(wrap)
        label.set_selectable(False)
        return label

    @staticmethod
    def radix_icon(name):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                os.path.join("/usr/share/clawos/icons", name), 15, 15, True
            )
            return Gtk.Image.new_from_pixbuf(pixbuf)
        except GLib.Error:
            return Gtk.Image()

    def summary_item(self, number, label):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.set_name("summary-card")
        card.pack_start(self.label(str(number), "summary-number", False), False, False, 0)
        card.pack_start(self.label(label, "muted", False), False, False, 0)
        return card

    def section(self, title):
        self.content.pack_start(Gtk.Separator(), False, False, 8)
        self.content.pack_start(self.label(title.upper(), "section-label", False), False, False, 0)

    def base_card(self, title, detail, meta=""):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_name("card")
        card.pack_start(self.label(title, "card-title"), False, False, 0)
        card.pack_start(self.label(detail, "detail"), False, False, 0)
        if meta:
            card.pack_start(self.label(meta, "meta"), False, False, 0)
        return card

    def machine_card(self, request):
        card = self.base_card(
            clean_text(request.get("summary"), "System action", 160),
            "\n".join(clean_text(effect, limit=180) for effect in request.get("effects", []) if isinstance(effect, str)) or
            "A typed ClawOS machine change is waiting.",
            f"Recovery: {clean_text(request.get('recovery'), 'Not available', 160)}",
        )
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        reject = Gtk.Button(label="Reject")
        reject.set_name("danger")
        reject.connect("clicked", self.machine_decide, request.get("token"), False)
        approve = Gtk.Button(label="Approve exact action")
        approve.set_name("primary")
        approve.connect("clicked", self.machine_decide, request.get("token"), True)
        controls.pack_end(approve, False, False, 0)
        controls.pack_end(reject, False, False, 0)
        card.pack_start(controls, False, False, 2)
        return card

    def openclaw_card(self, request):
        identifier = approval_id(request)
        kind = clean_text(request.get("kind"), "OpenClaw approval", 40)
        card = self.base_card(kind.replace("-", " ").title(), approval_detail(request), "OpenClaw policy decision")
        allowed = request.get("allowedDecisions")
        if not isinstance(allowed, list):
            nested = request.get("request") if isinstance(request.get("request"), dict) else {}
            allowed = nested.get("allowedDecisions", ["allow-once", "deny"])
        allowed = [decision for decision in allowed if decision in {"allow-once", "allow-always", "deny"}]
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for decision, label, style in (
            ("deny", "Deny", "danger"),
            ("allow-always", "Always allow", "quiet"),
            ("allow-once", "Allow once", "primary"),
        ):
            if identifier and decision in allowed:
                button = Gtk.Button(label=label)
                button.set_name(style)
                button.connect("clicked", self.openclaw_decide, identifier, decision)
                controls.pack_end(button, False, False, 0)
        card.pack_start(controls, False, False, 2)
        return card

    def task_card(self, task):
        status = clean_text(task.get("status"), "unknown", 24)
        runtime = clean_text(task.get("runtime") or task.get("kind"), "agent", 30)
        card = self.base_card(task_title(task), task_detail(task), f"{runtime.upper()} · {status.upper()}")
        identifier = task_id(task)
        if identifier and actionable_failure(task):
            reviewed = Gtk.Button(label="Mark reviewed")
            reviewed.set_name("quiet")
            reviewed.connect("clicked", self.review_item, "taskIds", identifier)
            card.pack_start(reviewed, False, False, 2)
        if identifier and status in {"queued", "running"} and not task.get("deployment"):
            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cancel = Gtk.Button(label="Stop work")
            cancel.set_name("danger")
            cancel.connect("clicked", self.cancel_task, identifier)
            controls.pack_end(cancel, False, False, 0)
            card.pack_start(controls, False, False, 2)
        return card

    def interrupted_card(self, request):
        identifier = request.get("requestId")
        card = self.base_card(
            "Interrupted Agent request",
            clean_text(request.get("summary"), "The request content is still private on this machine.", 180),
            "RESTART RECOVERY · REVIEW BEFORE RESUMING",
        )
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        discard = Gtk.Button(label="Discard")
        discard.set_name("danger")
        discard.connect("clicked", self.recover_request, identifier, "discard")
        resume = Gtk.Button(label="Resume request")
        resume.set_name("primary")
        resume.connect("clicked", self.recover_request, identifier, "resume")
        controls.pack_end(resume, False, False, 0)
        controls.pack_end(discard, False, False, 0)
        card.pack_start(controls, False, False, 2)
        return card

    def load(self):
        return collect()

    def review_item(self, _button, kind, identifier):
        acknowledge(kind, identifier)
        self.refresh()

    def refresh(self):
        if getattr(self, "refreshing", False):
            return
        self.refreshing = True
        self.show_message("Refreshing work…")
        threading.Thread(target=self.refresh_worker, daemon=True).start()

    def refresh_worker(self):
        try:
            GLib.idle_add(self.render_snapshot, self.load(), None)
        except Exception as error:
            GLib.idle_add(self.render_snapshot, None, str(error))

    def render_snapshot(self, snapshot, error):
        self.refreshing = False
        if error:
            self.show_message(error, error=True)
            return False
        if snapshot == getattr(self, "last_snapshot", None):
            self.show_message("")
            return False
        self.last_snapshot = snapshot
        self.clear(self.content)
        self.clear(self.summary)
        try:
            machine, approvals, tasks, interrupted = (snapshot[key] for key in ("machine", "approvals", "tasks", "interrupted"))
            active, recent, failed = (snapshot[key] for key in ("active", "recent", "failed"))
            needs_you = snapshot["reviewCount"]
            self.summary.pack_start(self.summary_item(needs_you, "to review"), True, True, 0)
            self.summary.pack_start(self.summary_item(len(active), "working now"), True, True, 0)
            self.summary.pack_start(self.summary_item(len(recent), "recent work"), True, True, 0)

            self.section("Review")
            if not needs_you:
                self.content.pack_start(self.label("No decisions or failed work are waiting."), False, False, 4)
            for error in snapshot["errors"]:
                self.content.pack_start(self.base_card("Work status unavailable", error, "REFRESH TO RETRY"), False, False, 0)
            if snapshot["notice"]:
                notice = snapshot["notice"]
                card = self.base_card("Agent notice", clean_text(notice["message"]), "ATTENTION")
                dismiss = Gtk.Button(label="Mark reviewed")
                dismiss.set_name("quiet")
                dismiss.connect("clicked", self.review_item, "noticeIds", notice["id"])
                card.pack_start(dismiss, False, False, 2)
                self.content.pack_start(card, False, False, 0)
            for request in interrupted:
                self.content.pack_start(self.interrupted_card(request), False, False, 0)
            for request in machine:
                self.content.pack_start(self.machine_card(request), False, False, 0)
            for request in approvals:
                self.content.pack_start(self.openclaw_card(request), False, False, 0)
            for task in failed:
                self.content.pack_start(self.task_card(task), False, False, 0)

            self.section("Work")
            if not active:
                self.content.pack_start(self.label("No background work is running."), False, False, 4)
            for task in active:
                self.content.pack_start(self.task_card(task), False, False, 0)

            self.section("Recent")
            if not recent:
                self.content.pack_start(self.label("Completed work will appear here."), False, False, 4)
            for task in [item for item in recent if item not in failed]:
                self.content.pack_start(self.task_card(task), False, False, 0)
            self.show_message("")
        except Exception as error:
            self.show_message(str(error), error=True)
        self.summary.show_all()
        self.content.show_all()

    def show_message(self, value, error=False):
        self.message.set_text(value)
        self.message.set_name("error" if error else "success")

    def machine_decide(self, _button, token, approve):
        if not isinstance(token, str) or not token:
            self.show_message("This machine request is no longer valid.", error=True)
            return
        self.set_sensitive(False)
        self.show_message("Applying the exact action…" if approve else "Rejecting the action…")
        threading.Thread(target=self.machine_worker, args=(token, approve), daemon=True).start()

    def machine_worker(self, token, approve):
        try:
            result = broker("commit" if approve else "cancel", token)
            GLib.idle_add(self.decision_finished, result, None)
        except Exception as error:
            GLib.idle_add(self.decision_finished, None, str(error))

    def openclaw_decide(self, _button, identifier, decision):
        self.set_sensitive(False)
        self.show_message("Sending the OpenClaw decision…")
        threading.Thread(target=self.openclaw_worker, args=(identifier, decision), daemon=True).start()

    def openclaw_worker(self, identifier, decision):
        try:
            result = openclaw("approvals", "resolve", identifier, decision, "--json", timeout=30)
            GLib.idle_add(self.decision_finished, result, None)
        except Exception as error:
            GLib.idle_add(self.decision_finished, None, str(error))

    def cancel_task(self, _button, identifier):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Stop this background work?",
        )
        dialog.format_secondary_text("The task remains in OpenClaw history with a cancelled result.")
        dialog.add_button("Keep running", Gtk.ResponseType.CANCEL)
        dialog.add_button("Stop work", Gtk.ResponseType.ACCEPT)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.ACCEPT:
            return
        self.set_sensitive(False)
        self.show_message("Stopping background work…")
        threading.Thread(target=self.cancel_task_worker, args=(identifier,), daemon=True).start()

    def cancel_task_worker(self, identifier):
        try:
            result = run_action([OPENCLAW, "tasks", "cancel", identifier], timeout=30)
            GLib.idle_add(self.decision_finished, result, None)
        except Exception as error:
            GLib.idle_add(self.decision_finished, None, str(error))

    def recover_request(self, _button, identifier, action):
        if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier):
            self.show_message("This interrupted request is no longer valid.", error=True)
            return
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Resume this Agent request?" if action == "resume" else "Discard this Agent request?",
        )
        if action == "resume":
            dialog.format_secondary_text(
                "ClawOS cannot prove where the interrupted run stopped. Resuming may repeat external or machine effects."
            )
            dialog.add_button("Keep paused", Gtk.ResponseType.CANCEL)
            dialog.add_button("Resume request", Gtk.ResponseType.ACCEPT)
        else:
            dialog.format_secondary_text("The private queued prompt will be deleted and recorded as discarded.")
            dialog.add_button("Keep request", Gtk.ResponseType.CANCEL)
            dialog.add_button("Discard", Gtk.ResponseType.ACCEPT)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.ACCEPT:
            return
        self.set_sensitive(False)
        self.show_message("Resuming background work…" if action == "resume" else "Discarding request…")
        threading.Thread(target=self.recover_request_worker, args=(identifier, action), daemon=True).start()

    def recover_request_worker(self, identifier, action):
        try:
            result = run_action([AGENT_REQUEST, action, identifier], timeout=30)
            GLib.idle_add(self.decision_finished, result, None)
        except Exception as error:
            GLib.idle_add(self.decision_finished, None, str(error))

    def decision_finished(self, _result, error):
        self.set_sensitive(True)
        if error:
            self.show_message(error, error=True)
        else:
            self.refresh()
            self.show_message("Updated. ClawOS kept the result in its durable history.")
        return False


if __name__ == "__main__":
    instance_lock = claim_instance()
    if instance_lock is not None:
        window = CenterWindow()
        window.show_all()
        Gtk.main()
