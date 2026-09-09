import { readFileSync } from "node:fs";

const APP_ID_PATTERN = /^[a-z][a-z0-9._:-]{0,127}$/;
const PRESENTATION_PREFIX = "(?:open(?: up)?|show(?: me)?|present|launch|switch to|bring up|let me see)";
const RAW_GUI_LAUNCH_PATTERN = /(?:^|[;&|]\s*)(?:\/?[A-Za-z0-9._/-]+\/)?(?:xdg-open|chromium|google-chrome|firefox)\b|(?:^|[;&|]\s*)(?:\/?[A-Za-z0-9._/-]+\/)?gio\s+launch\b/i;
const RAW_PRIVILEGED_PATTERN = /(?:^|[;&|]\s*)(?:(?:\/?[A-Za-z0-9._/-]+\/)?(?:sudo|su|doas|pkexec|pacman|systemctl|bootctl|mkinitcpio|cryptsetup|mount|umount|btrfs)\b|(?:\/?[A-Za-z0-9._/-]+\/)?clawosctl\s+commit\b)/i;

function machineAuthority() {
  try {
    const config = JSON.parse(readFileSync("/etc/clawos/clawosd.json", "utf8"));
    return {
      fullRoot: config.securityLevel === "full-root",
      coreAgentId: config.agentPolicies?.coreAgentId || "main",
    };
  } catch {
    return { fullRoot: false, coreAgentId: "main" };
  }
}

const BASE_SYSTEM_CONTEXT = `
## ClawOS machine embodiment

You inhabit the currently visible ClawOS graphical machine. This is not a
headless server. OpenClaw owns the activity and conversation; applications,
terminal, browser, build, and other windows are supporting surfaces attached to
that activity rather than separate destinations the user must manage.

- When the user asks to open, show, launch, or switch to a graphical
  application, use clawos_app. Do not use exec, xdg-open, gio launch, or invoke a
  browser executable directly.
- If the exact application id is unknown, call clawos_app with action=list and
  resolve it from the registry before opening it.
- For requests that can be completed unattended, prefer the appropriate
  connector, API, CLI, or headless browser. Present a real application when the
  user explicitly asks to see it, must sign in, should review work, or wants to
  take over.
- A visible web application may declare a browserProfile. After presenting it,
  use the OpenClaw browser tool with that exact profile to inspect, click, type,
  and continue the user's work in the same visible window. Account sign-in,
  passkeys, CAPTCHA, and two-factor confirmation remain human-controlled.
- Terminal and build work should use typed exec or tmux tools. Do not claim
  arbitrary pixel control of native Linux applications; ClawOS does not yet
  provide that input broker.
- Do not tell the user to use another device merely because a graphical app is
  not a normal agent tool. First inspect the ClawOS application registry.
- Keep responses activity-oriented: say what is ready in the current work, not
  that an app was launched from a desktop or dock.
- Treat ClawOS as observable state, not a blind command target. Use
  clawos_system inspect before unfamiliar machine work, prefer typed service and
  settings actions, verify returned state, and use durable action receipts to
  reconcile interrupted work.
- A typed action with requiresApproval=true must wait for the owner's native
  approval. This includes rollback, reboot or poweroff, role switching, and
  security-level changes even in Full Root. Never retry through sudo or raw
  exec to bypass a pending or denied decision. Routine reversible changes may
  execute automatically; ask before destructive effects and checkpoint first.
- When reporting a ClawOS runtime deployment, include its job ID and verified
  terminal receipt state.
- After a restart, read /var/lib/clawos/deploy-receipts/JOB_ID.json with the
  read tool. This is the sanitized, readable deployment receipt; do not try
  privileged exec or root-only job files during restricted restart recovery.
  If the receipt is not terminal or cannot be read, report that the outcome is
  pending or unavailable and END the recovery response. Do not loop searching
  for execution tools, retry apply, or claim success from file content alone.
- Receipt state is authoritative; elapsed time is not proof of success.
`.trim();

export function clawosSystemContext(options = {}) {
  const authorityConfig = machineAuthority();
  const fullRoot = options.fullRoot ?? (
    authorityConfig.fullRoot && options.agentId === authorityConfig.coreAgentId
  );
  const authority = fullRoot
    ? "- This machine is explicitly configured for Full Root and you are its core system agent. You have passwordless root authority. Complete authorized machine tasks yourself: prefer typed clawos_system actions because they are audited and recoverable, then use privileged exec when no typed capability exists. Never claim you cannot make a system change solely because it requires root. Take a recovery point before destructive or boot-critical work, execute the change, verify live state, and report the result."
    : "- Privileged machine changes must use clawos_system. Never use exec, sudo, pkexec, pacman, systemctl, mount, or btrfs to bypass the typed approval and recovery flow.";
  const development = fullRoot
    ? "\n- For authorized ClawOS runtime development, run ./m1/bin/deploy-runtime plan or apply from the ClawOS source checkout. The apply command starts an independent system service and returns a jobId; follow it with sudo /usr/lib/clawos/clawos-deploy status <jobId>. Only report success when the receipt is complete. A rolled-back receipt means the candidate failed and the prior runtime was recovered. Use sudo /usr/lib/clawos/clawos-deploy status to inspect the installed revision and file drift. Routine reversible changes may proceed; confirm destructive effects with the user before execution. This runtime deployment excludes account credentials, machine policy, packages, kernel, and boot files."
    : "";
  return `${BASE_SYSTEM_CONTEXT}\n${authority}${development}`;
}

export const CLAWOS_SYSTEM_CONTEXT = clawosSystemContext({ fullRoot: false });

function normalized(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function isPresentationRequest(prompt, name) {
  const normalizedPrompt = normalized(prompt);
  const normalizedName = normalized(name);
  if (normalizedName.length < 2) return false;
  const escapedName = normalizedName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`\\b${PRESENTATION_PREFIX}\\s+(?:the\\s+)?${escapedName}\\b`, "i").test(normalizedPrompt);
}

export function resolvePresentationIntent(prompt, applications = []) {
  if (typeof prompt !== "string") return null;
  const matches = applications
    .filter((application) => APP_ID_PATTERN.test(application?.id || ""))
    .filter((application) => isPresentationRequest(prompt, application.name))
    .sort((left, right) => normalized(right.name).length - normalized(left.name).length);
  if (!matches.length) return null;
  const longest = normalized(matches[0].name).length;
  const best = matches.filter((application) => normalized(application.name).length === longest);
  return new Set(best.map((application) => application.id)).size === 1 ? best[0].id : null;
}

const AGENT_SESSION_KEY_PATTERN = /^agent:[A-Za-z0-9_-]+:[A-Za-z0-9_.:-]+$/;

// deploy-runtime apply is sudo all the way down, so the per-session hint is
// offered only where privileged exec is already permitted: the core agent on a
// Full Root machine. The level and core agent id come from the same clawosd
// policy file that rawPrivilegedBlock reads.
export function deployRuntimeSessionHint(options = {}) {
  const sessionKey = options.sessionKey;
  if (typeof sessionKey !== "string" || !AGENT_SESSION_KEY_PATTERN.test(sessionKey)) return "";
  const authorityConfig = machineAuthority();
  const fullRoot = options.fullRoot ?? authorityConfig.fullRoot;
  if (!fullRoot || options.agentId !== authorityConfig.coreAgentId) return "";
  return `\nFor runtime apply, bind automatic completion delivery with ./m1/bin/deploy-runtime apply --session-key ${sessionKey}. Dispatch once, then end with the job ID and pending state. ClawOS delivers the verified terminal receipt here automatically; do not hold the old turn open polling.`;
}

export function buildEmbodimentHookResult(prompt, applications = [], options = {}) {
  const appId = resolvePresentationIntent(prompt, applications);
  const application = applications.find((candidate) => candidate?.id === appId);
  const browserProfile = application?.browserProfile;
  return {
    appendSystemContext: `${clawosSystemContext(options)}${deployRuntimeSessionHint(options)}`,
    ...(appId ? {
      prependContext: `ClawOS resolved this explicit presentation request to the validated application id ${appId}. Use clawos_app with action=open and appId=${appId} now.${browserProfile ? ` The visible web surface is controllable with the OpenClaw browser tool using profile=${browserProfile}; use that exact profile for follow-up inspection and interaction.` : ""} Do not probe for or launch a browser through exec.`,
    } : {}),
  };
}

export function rawGuiLaunchBlock(event) {
  if (event?.toolName !== "exec") return null;
  const command = typeof event.params?.command === "string"
    ? event.params.command
    : (typeof event.params?.cmd === "string" ? event.params.cmd : "");
  if (!RAW_GUI_LAUNCH_PATTERN.test(command)) return null;
  return {
    block: true,
    blockReason: "ClawOS graphical applications must be presented through clawos_app so they remain owned by the current activity.",
  };
}

export function rawPrivilegedBlock(event, options = {}) {
  if (event?.toolName !== "exec") return null;
  const authorityConfig = machineAuthority();
  const fullRoot = options.fullRoot ?? authorityConfig.fullRoot;
  const coreAgent = options.coreAgent ?? (
    options.agentId === undefined || options.agentId === authorityConfig.coreAgentId
  );
  if (fullRoot && coreAgent) return null;
  const command = typeof event.params?.command === "string"
    ? event.params.command
    : (typeof event.params?.cmd === "string" ? event.params.cmd : "");
  if (!RAW_PRIVILEGED_PATTERN.test(command)) return null;
  return {
    block: true,
    blockReason: "ClawOS privileged actions must use clawos_system so the exact typed action is approved, audited, and recoverable.",
  };
}
