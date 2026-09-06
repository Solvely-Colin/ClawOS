# Milestone 2: upstream OpenClaw integration

This milestone begins the real ClawOS/OpenClaw integration without patching the
Control UI bundle.

## Current seam

`openclaw-plugin/` is an external OpenClaw plugin that uses the supported
`registerControlUiDescriptor` tab contract. OpenClaw owns the sidebar, routing,
authentication, sessions, and UI lifecycle. The plugin owns only the ClawOS
machine surface served at `/plugins/clawos-system/panel`.

The System panel remains read-only: it reports machine, resource, broker, and
recovery status using Node's operating-system APIs and read-only kernel files.
The plugin also registers three explicit, non-shell tools. `clawos_surface`
controls only the allowlisted Terminal, Browser, and Build inspection surfaces;
`clawos_activity` projects task and attention state into the native panel; and
`clawos_app` lists, opens, focuses, hides, or closes validated registry entries.
All three
talk to a same-user Unix-socket broker and expose no arbitrary command input or
privileged operation.

The plugin also supplies stable ClawOS machine embodiment through OpenClaw's
supported `before_prompt_build` hook. Every run understands that it inhabits a
graphical activity-owned machine. Explicit open/show intent is conservatively
resolved against the sanitized application registry, while a `before_tool_call`
guard rejects raw graphical launches through `exec`. See `EMBODIMENT.md`.

The plugin also projects lifecycle automatically from OpenClaw's supported
`model_call_started`, `agent_end`, `subagent_spawned`, and `subagent_ended`
hooks. `agent_end` is classified by OpenClaw as conversation-capable, so local
onboarding grants this trusted plugin the required hook permission. The ClawOS
handler immediately selects only run id, success, duration, agent, and session
metadata; it never reads, stores, or sends the accompanying messages.

The sandboxed tab uses a random, restart-scoped capability path because iframe
navigations cannot attach the Control UI's Gateway WebSocket bearer token. The
capability is advertised only in the authenticated Gateway hello, rotates on
every Gateway start, and grants access only to this read-only HTML response.

The thin ClawOS top panel shown in the shell prototype is a future native
Wayland/compositor surface. It must not be injected into or wrapped around the
compiled OpenClaw Control UI.

## Development install

```bash
openclaw plugins install --link ./m2/openclaw-plugin
openclaw config set tools.alsoAllow '["clawos_surface","clawos_activity","clawos_app"]' --strict-json
openclaw config set plugins.entries.clawos-system.hooks.allowConversationAccess true --strict-json
openclaw config set plugins.entries.clawos-system.hooks.allowPromptInjection true --strict-json
systemctl --user restart openclaw-gateway.service
```

Then reload the Control UI. The enabled plugin advertises a **System** tab in
OpenClaw's control group. ClawOS onboarding performs the plugin install and
additive tool-policy configuration automatically for a local Gateway.

## Verification

```bash
npm --prefix m2/openclaw-plugin test
openclaw plugins inspect clawos-system --runtime --json
openclaw plugins doctor
```
