# ClawOS VPS demo path (not for public exposure)

> **Status:** operator notes for a private demo host. Not a supported deployment
> path and not exercised since the key-only sshd change; treat as a checklist,
> not a proof.

The demo must expose the real ClawOS graphical session. It must not create a
second HTML desktop or publish an unauthenticated VNC listener.

## Provider-managed virtual machine

Prefer a VPS provider that supports a custom ISO, UEFI boot, a recovery
console, and browser console access. Install ClawOS through that provider
console, detach the ISO, then cold-boot the installed disk twice before sharing
the demo.

Keep SSH and the provider console as independent recovery paths. Restrict SSH
at the provider firewall to the operator's address or a private Tailnet. Do not
publish the OpenClaw Gateway port or a VNC port to the public Internet.

Password, keyboard-interactive and root SSH logins are refused on every install
(`/etc/ssh/sshd_config.d/00-clawos.conf`). Put the operator's public key in
`/home/clawos/.ssh/authorized_keys` from the provider console or the recovery
TTY before relying on SSH.

## Nested or self-hosted QEMU proof

The repository runner can publish QEMU's framebuffer on loopback only:

```sh
./m1/bin/run-qemu --installed \
  --disk artifacts/m1/disks/clawos-m4-ui.qcow2 \
  --headless-vnc --vnc-display 1
```

On a remote host, tunnel that loopback listener before connecting a VNC client:

```sh
ssh -N -L 5901:127.0.0.1:5901 user@vps
```

If nested KVM is unavailable, add `--software`. TCG is a compatibility path for
validation, not a performance representation of ClawOS.

Browser VNC should be supplied by the provider console for the first private
demo. A ClawOS-owned noVNC bridge is intentionally deferred until it has TLS,
authentication, origin checks, and a reviewed update path; bundling an open
WebSocket proxy would weaken the system to improve a demo.

## Exit checks before uploading

1. Graphical install completes without a terminal.
2. First boot enters graphical onboarding and preserves progress after restart.
3. Standalone mode reaches a connected Gateway and approved local node.
4. Two cold boots return to the same identity, security level, and session.
5. Gateway restart restores a fully styled Agent surface automatically.
6. SSH recovery works without enabling public root/password login.
7. Provider recovery console remains available if networking or the UI fails.
8. All temporary provider keys are rotated before the image is shared.
