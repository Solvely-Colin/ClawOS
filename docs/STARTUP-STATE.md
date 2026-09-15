# Startup state model

`clawosd` owns the installed machine's startup state. `clawosctl status` and
the D-Bus `GetStatus` method expose the same observation; desktop consumers do
not independently promote configuration files or a successful HTTP request to
machine readiness.

| State | Meaning | Transition trigger |
| --- | --- | --- |
| `startup` | The graphical session or configured Gateway is still starting. | The session service becomes active, setup completes, and the configured Gateway becomes reachable. |
| `locked` | `gtklock` owns the active graphical session. | The lock process exits after successful local unlock. |
| `setup-incomplete` | The desktop is active, but the versioned onboarding checkpoint does not match the configured local or remote mode at stage `complete`. | Onboarding atomically writes its completed checkpoint. |
| `ready` | Setup is complete, the desktop is active, and the configured Gateway or controller is reachable. | Loss of a prerequisite returns to `startup`; locking enters `locked`. |
| `repair-required` | The session service failed or a root-owned repair marker exists. | A verified repair removes the marker or restores the failed service. |

The readiness object reports the observations behind the state: `setup`,
`desktop`, `lock`, `gateway`, and `model`. A selected model is reported as
`configured-unverified`; `ready` therefore means **Gateway reachable, model
inference unverified**. Status does not run an inference request, expose
credentials, or turn broker availability into model readiness.

The owner is `clawosd`; the Sway entry process, onboarding status endpoint,
top-bar status, Agent browser launcher, return-to-setup action, and lock action
consume its result through `clawosctl status`. `clawosd` remains available on
the system bus before the user session, so setup and recovery do not depend on
the Gateway they are diagnosing.

The installed graphical session exclusively owns tty2. Fresh installs mask
`getty@tty2.service`, and runtime deployment reapplies that invariant for older
development installations before restarting Sway. This prevents an automatic
getty from hanging up the desktop during boot.

Runtime deployment also migrates pre-checkpoint installations once: when a
valid local or remote Gateway mode exists but no onboarding checkpoint exists,
it writes an owner-only completed checkpoint marked `legacy-config`. A partial
modern setup already has a checkpoint and is never promoted by this migration.
