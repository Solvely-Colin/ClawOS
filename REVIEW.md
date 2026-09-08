> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# Review of PLAN.md

## Round 4 — 2026-08-25 (Sway / setup-app / clawosd revision)

### Status

This revision applies rounds 2 and 3 almost completely: Sway replaces Cage; Carapace comes from a pinned GitHub tag built with Bun; installer and first-boot are one root-owned loopback setup app; `clawosd` is the single device API with the D-Bus surface expanded to match the System tab; Node-mode System tab requires a controller-side plugin routed via node invocation with capability negotiation; Full Root is post-install only and its sudo/bypass semantics are stated; User Limited is scheduled in M3; coexist-mode caveats (pacman hook, Limine config mechanism, snapshot independence, `Work` subvolume check, no hibernation) are in; fast lane is a second signed allowlisted channel; multi-agent scope is split M2/M3/M5 with the logical-isolation caveat; stale overlay/native-app text is gone.

**Correction to round 3:** `agents.create` does exist — it is a Gateway RPC alongside `agents.list`/`agents.update`/`agents.delete`. The plan's citation is fine.

The plan is now in good shape. What remains is making three "root-owned" claims mechanically true, and tightening what attribution can actually deliver.

### 1. "Root-owned" session config is not root-owned as specified

The plan relies on a root-owned Sway config, a root-owned systemd user-session definition, and a launcher the agent cannot alter. Under Full User + Approvals the agent is the session user, and the default lookup rules let the user override all three:

- **Sway** reads `~/.config/sway/config` *before* `/etc/sway/config`. A same-UID agent can drop a config there and own the compositor (keybindings, `exec` lines, lock behaviour). Fix: launch with an explicit `sway -c /etc/clawos/sway.conf`; an explicit `-c` is not overridden.
- **systemd user units**: `~/.config/systemd/user/` overrides `/etc/systemd/user/` for a unit of the same name, and the user can `systemctl --user mask/edit` anything. Fix: start the session from a **system** unit (`clawos-session.service`, `User=<owner>`, `PAMName=login`, or greetd with autologin) that execs Sway directly. The user manager then hosts only OpenClaw services, which are the things the user is *supposed* to be able to control.
- **Chromium**: the profile directory is user-writable, so kiosk flags alone don't prevent extensions, DevTools, or navigating the kiosk elsewhere. Fix: ship managed policy in `/etc/chromium/policies/managed/` (`URLAllowlist` to the Gateway origin(s), `ExtensionInstallBlocklist: ["*"]`, `DeveloperToolsAvailability: 2`, `IncognitoModeAvailability`, `BrowserSignin: 0`). Root-owned, applied regardless of profile.

These are small, but without them the §2 idle/lock policy and the §3 "shell the agent cannot alter" are true only until an agent edits a dotfile. Add them to §3 and to the M0 checklist.

### 2. Attribution: there is a supported seam, but say what it proves

Round 3 worried that agent identity isn't exposed to plugins. It isn't, but the Gateway RPC `audit.run.inspect` (`operator.read`) can inspect an exact `executionId`, and `audit.activity.list` returns decision receipts. So `clawosd` can hold an operator token (provisioned at first boot, root-only) and verify that an `executionId` presented with a request is real and belongs to agent X. That is the "trusted Gateway-to-broker integration" M3 wants, and it's upstream — good.

Two limits to state explicitly:

- It proves the execution exists, not that *this D-Bus call* came from it. Under Full User + Approvals any same-UID process can read a valid `executionId` and present it. Per-agent broker policy is therefore meaningful only in **User Limited**, where `clawosd` can also check the D-Bus peer UID. Say per-agent policy is a User Limited feature; in Full User + Approvals it is advisory, like the audit log already is.
- In **Node mode** the executions live on the remote controller, so verification means `clawosd` holding an operator token for someone else's Gateway. Scope per-agent attribution to Standalone for MVP, and let Node mode record the controller's node-invocation approval instead.

### 3. Full Root wording

"Gives the OpenClaw service account passwordless sudo" — under Full User + Approvals there is no service account; OpenClaw runs as the human owner, so Full Root means passwordless sudo for the owner's whole session. Under User Limited it means sudo for `claw`. State it per level so nobody reads Full Root as scoped when it isn't.

### 4. Small items

- "Every ClawOS release pins" lists Node.js and browser versions; add **Bun** and the **Carapace tag**, since both are now build inputs.
- Summary still says agents have isolated "runtimes"; per-agent sandbox is upstream, per-agent runtime is not. Drop the word.
- Sway ≥ 1.8 is needed for `ext-session-lock-v1` and `ext-idle-notify-v1`; Arch's is well past that, but note the floor in the manifest.
- M1 now depends on a Bun-built web app running inside the live ISO (Sway + Chromium on the live image too). That's consistent, but it means M1's "minimal bootable base" is no longer minimal — a TUI fallback for the live installer would keep M1 unblocked if the setup app slips.
- Still not a git repo.

### Priority order

1. §1 — explicit `sway -c`, system-unit session launch, Chromium managed policy. Add to §3 and M0.
2. §2 — scope per-agent policy to User Limited and attribution to Standalone; note `audit.run.inspect` as the mechanism.
3. §3–4 wording and manifest additions.

---

## Round 3 — 2026-08-25 (multi-agent revision)

### First: nothing from round 2 was applied

Every round-2 item is still in the plan verbatim: Cage (no session-lock → idle/lock policy unimplementable), `@openclaw/carapace` (not an npm package), Cage in M0/M2, the "independent local recovery overlay" in Assumptions, "native-app launch" in the test plan, undefined System tab in Node mode, Full Root in onboarding, User Limited in no milestone. See round 2 below; item 1 there is still the blocker.

This revision instead **adds** scope: multi-agent operation moves from "not part of v1" to "ships in MVP," and Milestone 2's exit criterion and the test plan grow accordingly.

### 1. The multi-agent section is technically sound

I verified the OpenClaw claims against `concepts/multi-agent`, `gateway/config-agents`, and `tools/subagents`:

- `agents.defaults.systemAgent.agentId` — exists; "owns ambient OpenClaw system work"; resolution order explicit request → `systemAgent.agentId` → legacy default → sole agent. ✔
- `agents.ownership: "explicit"` — exists; stamped when creating a multi-agent fleet; requires bindings/`agentId` targets. ✔
- Per-agent `agentDir`, workspace, SQLite session store, auth profiles. ✔
- Creator provenance (`operator` vs agent-created, operator approval). ✔
- `sessions_spawn` with `subagents.allowAgents`, `requireAgentId`, `maxConcurrent` (8), `maxSpawnDepth` (1), `maxChildrenPerAgent` (5), sandbox inheritance (`sandbox: "require"`). ✔
- `agents.create` as a "typed operation" — **not found** in the docs. Agent creation exists via CLI/onboarding and agent-created-with-approval; verify the actual RPC/CLI name before citing it.

The design choice — OpenClaw is the sole control plane, ClawOS adds no roster/session store/herder — is the right one, and since it is all upstream config it is cheap. Keep that part.

### 2. Three things in the section are not upstream and are not cheap

The section says ClawOS adds no orchestration layer, then specifies three pieces of new infrastructure:

- **Per-agent OS capability policy narrower than the machine ceiling.** OpenClaw has per-agent *tool/sandbox/subagent* policy; it has no concept of ClawOS privileged actions. Mapping agent → allowed `clawosd` action classes is a ClawOS policy engine that must live in `clawosd` (agent identity has to reach root, see next item).
- **Audit attribution of requesting agent, session, task/delegation id.** The docs say the execution-identity context is *not* exposed to plugin APIs ("neither the private identity token nor task text appears in public outputs, transcripts, or plugin APIs"). So `clawos-system` may not be able to learn who is asking with any integrity. Verify what the plugin SDK actually exposes about the calling agent/session before promising these audit fields; otherwise attribution is self-reported by a same-UID process and worth little.
- **"Authority delegated to a durable task remains attached across subagents, restarts, and reboot recovery."** That is a capability-token system surviving Gateway restarts and reboots — OpenClaw's subagent identity is per-run lineage, not durable authority. This is exactly the kind of orchestration layer the section says ClawOS does not build. Either cite the upstream mechanism or own it as ClawOS M3+ work.

None of these are wrong to want. They are M3/M5-sized, and they are currently attached to M2.

### 3. Isolation claims need the same honesty as §5

"Isolated agent identities, workspaces, credentials" — under Full User + Approvals every agent runs as the same UID and can read every other agent's `agentDir`, SQLite store, and auth profiles. Isolation is logical (OpenClaw routing/config), not OS-enforced, for the same reason §5 already admits the approval boundary isn't one. Say so in the multi-agent section, and decide whether User Limited means one `claw` UID for all agents or one UID per agent (the latter is the only real isolation, and it multiplies the ACL/sharing problem).

### 4. Recommended split

- **Keep in M2** (upstream config only): create owner agent, set `systemAgent.agentId`, `ownership: "explicit"` when a second agent exists, `subagents.allowAgents`/`requireAgentId`, System tab shows agent list read-only. Exit criterion: second agent can be created and explicitly routed without state collision — as written.
- **Move to M3**: per-agent OS action policy in `clawosd`, agent/session attribution in the audit log (contingent on what the plugin SDK exposes).
- **Move to post-MVP or drop**: durable delegated authority across restart/reboot, "OS-agent reassignment" flows, audit across agent handoff/crash recovery. Delete the matching test-plan lines or mark them deferred.

### 5. Leftovers

- Summary says "Support OpenClaw-native multi-agent operation … runtimes" — "runtimes" implies per-agent Node/sandbox runtimes; per-agent sandbox is upstream, per-agent *runtime* is not. Trim the word or define it.
- `git init` still not done; `REVIEW.md` and `PLAN.md` are untracked.

### Priority order

1. Apply round 2, item 1 (compositor) — still the only hard blocker.
2. Apply round 2, items 2–3 and 7 (Carapace, installer sprawl, Node-mode System tab, stale text).
3. Split the multi-agent section per §4 above; fix `agents.create`; add the isolation caveat.

---

## Round 2 — 2026-08-25 (revised plan)

### What the revision fixed

Nearly everything from round 1 is addressed and, in several places, addressed better than suggested: the three security levels with an honest statement of what Full User + Approvals does and does not protect; Node-mode auth/pairing/WSS and the "no local terminal" caveat; `OPENCLAW_STATE_DIR` (verified — documented for multi-instance isolation); Milestone 0; shell demoted to a root-owned unit + script; T2 repo mirroring and re-signing; offline pnpm store (verified — upstream uses `pnpm-lock.yaml`); screen lock and idle policy; BlueZ; `mem_sleep_default=deep`; internal-NVMe check; role-switch timeout; browser fast lane; no telemetry.

The remaining issues are mostly new claims introduced by the revision.

### 1. Cage cannot implement the lock/idle policy (blocker)

Cage 0.3.x (Arch: `cage 0.3.1-1`, wlroots 0.20) implements only `xdg-shell`, XWayland, and `idle-inhibit-v1`. Its source tree has no `ext-session-lock-v1`, no `wlr-layer-shell`, and no `ext-idle-notify` — I checked the file list and `meson.build`.

Consequences:

- `swaylock` requires `ext-session-lock-v1`. It will not run under Cage.
- `swayidle` needs `ext-idle-notify` (or the legacy KDE idle protocol). Cage exposes neither.
- No layer-shell means no compositor-level overlay; anything "outside" Chromium is impossible.

So the entire idle/lock paragraph in §2 (lock at 10 min, display off, lock-before-suspend) is unimplementable as written, and lock-before-lid-close is the one that matters for an auto-login encrypted laptop.

Fix: keep a wlroots/Hyprland compositor that supports session-lock, with a **root-owned, minimal config** — no bar, launcher, Super bindings, or themes. The plan's objection to Omarchy is about the workflow layer, not the compositor, and Hyprland is already validated on this exact T2 machine (HiDPI, dual GPU). `hyprlock`/`hypridle` or `swaylock`/`swayidle` both work there. `sway` or `labwc` in a kiosk config are the alternatives. Run Milestone 0 on Hyprland accordingly.

Also verify VT switching (`Ctrl+Alt+F3`) under whichever compositor is chosen before claiming it as the recovery path — it is compositor-handled in wlroots, not guaranteed.

### 2. Carapace: wrong reference, and now three web apps

`@openclaw/carapace` does not exist on npm (404). The real thing is `github.com/openclaw/carapace`: a design system (CSS tokens, themes, primitives, Tailwind adapter) distributed **via immutable GitHub release tags with Bun, not npm**. Fix the reference and add it to the offline-vendoring story — the pnpm store won't cover it.

More importantly, the revision now specifies three separate Carapace UIs: the live installer, the post-reboot first-boot setup, and the System tab. The first two run **before any Gateway exists**, so they need their own local web server + Chromium kiosk — a second shell stack that must be built and maintained alongside the real one. Recommend:

- Merge installer and first-boot setup into one app with two modes.
- Make the M1 installer a TUI. M1's exit criterion is "installs a minimal encrypted system"; a web installer buys nothing there and costs a lot. Move the Carapace installer to M2 or later if it still seems worth it after living in M0.

### 3. The System tab is undefined in Node mode

`clawos-system` is a Gateway plugin. In Node mode there is no local Gateway, so the System tab only exists if the **controller** has the plugin installed, and the plugin must route to this machine via `node.invoke`. The plan says ClawOS commands are "advertised to the controller" but never says the controller must run a node-aware `clawos-system`, or how its version is coupled to the node's ClawOS release.

Recommend making **`clawosd` the single local device API** — Wi-Fi (NM), Bluetooth (BlueZ), brightness, audio, power, idle policy, security level, diagnostics — and having both callers hit it: the plugin's local backend in Standalone, and the node-host command surface in Node. Then the plugin has one node-routed backend, the controller install requirement is explicit, and the D-Bus API in §5 (currently 11 methods) grows to match what the System tab actually needs. Either extend the API listing or mark it illustrative.

### 4. Security-level semantics need one more sentence each

- **Full Root**: "unrestricted root capability" — via what? If it's passwordless sudo for the agent user, then `clawosd` and the approval UI are bypassed entirely in that mode; say so. Also: offering it in the first-boot wizard makes it a one-click choice in practice. Recommend it exists only as a post-install System → Security change, never in onboarding.
- **User Limited** is described as "the mode for a real isolation boundary" but appears in no milestone. Add it (M3 fits) or mark it explicitly deferred.

### 5. Coexist mode — feasible, with Omarchy-specific caveats

Verified on the reference machine: Limine 12.6, ESP at `/boot` (vfat, UUID `C425-184C`), LUKS root via `cryptdevice=PARTUUID=…`, `rootflags=subvol=@`, `resume=` hibernation offset set. So the described layout works. Watch for:

- Omarchy manages `limine.conf` through its own hooks (`limine-mkinitcpio-hook`, snapshot integration). A hand-added `@clawos` entry may be rewritten on the next kernel update; use whatever include mechanism the hook preserves, and test a kernel upgrade on the host after adding the entry.
- Installing `linux-t2` inside `@clawos` will try to write `/boot/vmlinuz-linux-t2` — the same path as the host's. "Separately named kernel/initramfs files" requires a pacman hook in the coexist root that renames on install, or the coexist root must not mount the ESP at all and copy files out-of-band.
- Omarchy's snapshot/rollback tooling knows about `@`, not `@clawos`. Document that host rollbacks don't touch ClawOS and vice-versa.
- `~/Work` (the shared work directory) must be a subvolume or bind mount to be shared; confirm it is (I couldn't without root).
- Hibernation: the plan's idle policy says suspend; the host has `resume=` configured. State explicitly that ClawOS does not hibernate in MVP, or the shared swapfile becomes a cross-install hazard.

### 6. Fast lane vs. manifest-only updates

"Critical browser/certificate/security fixes use an automatic fast lane" contradicts "applies only packages approved by that release manifest" and "no unrestricted rolling updates." Define the fast lane as a **second signed manifest channel** with its own snapshot + rollback, mirrored from the Arch snapshot for `chromium`/`ca-certificates`. Otherwise it is rolling updates by another name.

### 7. Stale text left over from round 1

- Summary: "Allow agents full access as the normal OS user" → should reference the default security level.
- Assumptions: "Node mode displays the controlling Gateway's UI with an independent local recovery overlay" — the overlay was removed; recovery is now TTY + boot entry.
- Test plan: "native-app launch" — the shell no longer launches native apps.
- §3 boot sequence and Milestones 0/2 say Cage; update per item 1.

### 8. Smaller items

- Chromium on Wayland needs `--ozone-platform=wayland` (plus `--enable-features=UseOzonePlatform` on older builds); `--kiosk` alone is not enough. Put the exact validated flag set in the launcher unit, not prose.
- The pre-Gateway setup wizard needs the LUKS passphrase and account password. It runs in a Chromium kiosk served by a local process — make sure that process is root-owned and the page is loopback-only, since this is the one moment secrets cross a web surface.
- `swaylock/swayidle` in the package list should become whatever matches the compositor decision.

### Recommended edits, in priority order

1. Replace Cage with a session-lock-capable compositor (Hyprland, root-owned minimal config) and re-run M0 on it.
2. Fix the Carapace reference; collapse installer + first-boot into one app; make the M1 installer a TUI.
3. Make `clawosd` the single local device API and specify the Node-mode System tab (controller plugin, `node.invoke` routing).
4. Define Full Root mechanically, remove it from onboarding, and schedule User Limited.
5. Add the Limine/kernel-naming/snapshot caveats to coexist mode.
6. Define the fast lane as a second signed channel.
7. Clean up stale text (§7).

---

## Round 1 — 2026-08-25 (original plan)

Kept for history. All items below were addressed in the revision except where round 2 notes otherwise.

1. **Security model contradicted itself** — agent-as-user owned Hyprland config, user units, the Polkit agent, and session secrets, so recovery/approval guarantees weren't real. → Resolved by security levels + honest boundary statement; root-owned session config.
2. **Node mode underspecified** — token, per-device pairing, `wss://`/`allowedOrigins`, Tailscale, no local terminal, `system.run` allowlist. → Resolved.
3. **Standalone details** — loopback still needs auth; `detachedSessionTimeoutSeconds`; npm vendoring. → Resolved.
4. **Scope** — M0 needed; Rust shell premature; "reproducible" → "pinned + hash-verified" with Arch Archive. → Resolved.
5. **Updates** — evaluate mkosi/sysupdate before M5. → Not adopted; still worth evaluating before M5.
6. **T2 specifics** — `mem_sleep_default=deep`; mirror/re-sign `[arch-mact2]` (currently `SigLevel = Never`); `tiny-dfr`/`iwd` untested here; HiDPI and Chromium flags. → Resolved except validation of `tiny-dfr`/`iwd`, still pending.
7. **Smaller** — browser fast lane; internal-NVMe check; role-switch timeout; `git init`. → Resolved except `git init`.
