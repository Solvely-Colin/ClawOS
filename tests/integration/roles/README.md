# Standalone and remote-node role integration

ClawOS keeps OpenClaw's own Gateway/node protocol as the distributed-system
boundary. It does not introduce a ClawOS relay or a second pairing model.

## Runtime contract

- First-boot setup can enroll either a local Gateway or a `ws://`/`wss://`
  remote Gateway. Gateway credentials stay in the selected role's mode-0600
  OpenClaw `.env` file.
- `clawos-install-node` installs the upstream persistent node-host service,
  verifies that the service is loaded, and verifies that OpenClaw's persistent
  device identity exists. Re-running it does not pass `--node-id`, so it does
  not reset that identity.
- The local ClawOS browser displays the selected controller's upstream Control
  UI. TTY3, the recovery boot entry, `clawosd`, and the native shell remain
  local when the controller is unavailable.
- The `clawos-system` plugin registers the dangerous `clawos.system` node-host
  command and a matching Gateway node-invoke policy. A controller-side copy of
  the same plugin routes `clawos_system` through `api.runtime.nodes.invoke` when
  no local ClawOS broker exists. Multiple matching machines require an explicit
  `targetNode`.
- The controller must explicitly allow the dangerous `clawos.system` command
  in its OpenClaw node command policy. Pairing alone is not treated as
  authorization.
- Standalone and Node configurations and secret references are stored as two
  mode-0600 role profiles. `clawos-role switch` validates the target, changes
  services, and restores the previous config, environment reference, and
  service mode on failure. OpenClaw's shared device identity and agent data are
  not replaced by a role switch.

## Controller installation contract

Until the plugin is published as a signed ClawOS package, a controller uses the
exact plugin directory shipped by the same ClawOS source/release:

```bash
openclaw plugins install --link /path/to/ClawOS/integrations/openclaw
openclaw plugins enable clawos-system --accept-capabilities
openclaw config set gateway.nodes.commands.allow '["clawos.system"]' --strict-json
openclaw gateway restart
```

The command-policy opt-in is deliberate. The plugin's node handler accepts only
the bounded `clawosctl` grammar; it cannot carry an executable or shell string.

## Tests

- `tests/integration/roles/role-switch.sh` proves successful switching and forced-failure
  restoration of config and secret references.
- The plugin tests prove local/remote routing, explicit selection with multiple
  nodes, bounded command parsing, and dangerous node policy registration.
- Final exit requires a fresh installed-VM run against a separate controller,
  including disconnect/reconnect and a typed action receipt.
