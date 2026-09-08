> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# ClawOS Application Surfaces

## Product contract

ClawOS is an AI-first operating system, not an agent-only appliance. It must run
the applications people already use for mail, development, communication, and
creative work while keeping OpenClaw as the durable home of intent and activity.
Applications therefore attach to an activity as surfaces; they do not become a
second desktop model or a row of permanent app tabs.

Humans choose work from the native intent palette; an explicit secondary action
can search all installed applications. OpenClaw uses the typed `clawos_app`
capability. Both paths resolve the same registry entry and call the same
same-user broker. A surface covers the activity canvas beneath the ClawOS panel,
can be hidden back to Agent Home without ending its process, and can later be
focused or closed by its stable application id.

## Registry boundary

The registry reads standard XDG `.desktop` files from the user's and system's
application directories. User entries follow freedesktop precedence. Hidden,
`NoDisplay`, malformed, and non-application entries are rejected. A root-owned
ClawOS entry can add a validated stable id, kind, agent capability, persistent
profile, and surface name through `X-ClawOS-*` metadata.

Only ids matching the registry grammar cross the socket. The broker resolves
the id back to a previously discovered absolute desktop file and launches it
with `gio launch` using an argument vector. Neither a model nor the palette can
supply a shell command, executable path, URL, or launch arguments.

ClawOS web apps add a second root-owned manifest boundary. The wrapper accepts
only a manifest id, requires an HTTPS URL and a safe persistent profile name,
then launches Chromium in app mode. Gmail and Outlook are the first proof
entries. Their profiles preserve user sessions across surface hide/show and OS
restarts.

## Agent boundary

`clawos_app` controls presentation, not account authority. Opening Gmail or
Outlook does not expose mailbox contents to OpenClaw and does not grant a Google
or Microsoft connector token. Unattended work should prefer a configured
connector, API, CLI, or browser automation capability; a visible application is
appropriate for human judgment, sign-in, inspection, and takeover.

Future integrations may correlate a surface with a connector capability, but
identity, scopes, approval, and audit remain explicit. A registry label such as
`google-mail` is discovery metadata, never authorization.

## Implemented lifecycle

- `list`: return sanitized application metadata and currently owned surfaces.
- `open`: adopt an existing matching window or launch, mark, size, and focus it.
- `focus`: reveal an owned scratchpad surface and focus it.
- `hide`: preserve the process, hide application surfaces, and return to Agent.
- `close`: terminate the selected surface and return to Agent.
- `status`: report only registered running surfaces and the visible surface id.

Sway marks are deterministic hashes of validated application ids. Registered
`StartupWMClass` metadata lets the broker re-adopt a surviving window after the
broker restarts. The native panel derives activity and lifecycle from the
broker's minimal state projection and keeps the supporting application in its
tooltip. It displays work such as `Main · Ready`, not `Main / Gmail`, so the
application does not become a top-level OS destination.

## Next extension

The next step is activity correlation: each application surface needs an owning
OpenClaw activity id, creation/focus timestamps, and a durable recovery policy.
After that, connector capabilities can be surfaced beside their human app while
remaining independently authorized and auditable.
