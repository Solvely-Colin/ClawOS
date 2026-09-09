import { readFileSync } from "node:fs";

const APP_ID_PATTERN = /^[a-z][a-z0-9._:-]{0,127}$/;
const PRESENTATION_PREFIX = "(?:open(?: up)?|show(?: me)?|present|launch|switch to|bring up|let me see)";
const RAW_GUI_LAUNCH_PATTERN = /(?:^|[;&|]\s*)(?:\/?[A-Za-z0-9._/-]+\/)?(?:xdg-open|chromium|google-chrome|firefox)\b|(?:^|[;&|]\s*)(?:\/?[A-Za-z0-9._/-]+\/)?gio\s+launch\b/i;

// Privileged-command rail. Binaries whose appearance as a command word blocks a
// raw `exec` for anyone but the Full Root core agent. Matched case-insensitively
// on the basename, so `/usr/bin/sudo` and `./sudo` count too.
const PRIVILEGED_BINARIES = new Set([
  "sudo", "sudoedit", "su", "doas", "pkexec", "run0",
  "pacman", "systemctl", "bootctl", "mkinitcpio", "cryptsetup", "mount", "umount", "btrfs",
]);
// Shells whose `-c STRING` argument is parsed as a nested command.
const SHELL_INTERPRETERS = new Set(["sh", "bash", "zsh", "dash", "ksh", "ash"]);
// Shell options that consume the following word, so it is not taken as the script.
const SHELL_OPTIONS_WITH_ARGUMENT = new Set(["-o", "+o", "-O", "+O", "--rcfile", "--init-file"]);
// Reserved words that may precede the command word of a simple command.
const SHELL_RESERVED_WORDS = new Set(["{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until", "coproc"]);
// Wrappers that run their trailing words as a command. Each value lists the
// options that consume the following word (so `nice -n 10 sudo` still reaches
// `sudo`); attached forms such as `-n10` or `--interval=5` are one word already.
const COMMAND_WRAPPERS = new Map([
  ["env", ["-u", "--unset", "-C", "--chdir"]],
  ["nice", ["-n", "--adjustment"]],
  ["nohup", []],
  ["time", ["-f", "--format", "-o", "--output"]],
  ["timeout", ["-k", "--kill-after", "-s", "--signal"]],
  ["exec", ["-a"]],
  ["command", []],
  ["builtin", []],
  ["xargs", ["-a", "--arg-file", "-d", "--delimiter", "-E", "-I", "--replace", "-L", "--max-lines", "-n", "--max-args", "-P", "--max-procs", "-s", "--max-chars"]],
  ["stdbuf", ["-i", "--input", "-o", "--output", "-e", "--error"]],
  ["setsid", []],
  ["ionice", ["-c", "--class", "-n", "--classdata", "-p", "--pid", "-P", "--pgid", "-u", "--uid"]],
  ["chrt", ["-p", "--pid"]],
  ["taskset", ["-p", "--pid"]],
  ["watch", ["-n", "--interval"]],
]);
const FIND_EXEC_OPTIONS = new Set(["-exec", "-execdir", "-ok", "-okdir"]);
const ASSIGNMENT_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=/;
// A bare duration, priority or CPU mask positional after a wrapper (`timeout 5`, `chrt 10`, `taskset 0x1`).
const NUMERIC_POSITIONAL_PATTERN = /^(?:\d+(?:\.\d+)?[smhd]?|0x[0-9a-f]+)$/i;
const MAX_SHELL_NESTING = 8;

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

export function buildEmbodimentHookResult(prompt, applications = [], options = {}) {
  const appId = resolvePresentationIntent(prompt, applications);
  const application = applications.find((candidate) => candidate?.id === appId);
  const browserProfile = application?.browserProfile;
  return {
    appendSystemContext: clawosSystemContext(options),
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

// Splits a shell command line into simple commands, each a list of words with
// quotes and backslashes removed. Separators are newlines, `;`, `&`, `|`, `(`,
// `)`, backticks and `$(`, all recognised only outside single quotes (command
// substitution is also recognised inside double quotes, as the shell does).
// Redirections become their own words flagged `redirect`; `#` comments are
// skipped because the shell never executes them. Heredoc bodies are skipped as
// commands, but a body whose delimiter was unquoted still expands `$(...)` and
// backticks, so those bodies are returned in `segments.heredocBodies` for a
// substitution scan. Unterminated quotes fall back to a second pass that treats
// quotes as ordinary characters, so a broken command line fails closed rather
// than open.
function splitSimpleCommands(command, respectQuotes = true) {
  const segments = [];
  segments.heredocBodies = [];
  let words = [];
  let word = null;
  const stack = [];
  let inBackquote = false;
  const heredocs = [];
  let pendingHeredoc = null;
  let index = 0;

  const top = () => stack[stack.length - 1];
  const startWord = () => { if (!word) word = { text: "", redirect: false, quoted: false }; };
  const append = (text) => { startWord(); word.text += text; };
  const endWord = () => {
    if (!word) return;
    if (pendingHeredoc) {
      heredocs.push({ terminator: word.text, stripTabs: pendingHeredoc.stripTabs, expand: !word.quoted });
      pendingHeredoc = null;
    } else if (word.heredoc) {
      const terminator = word.text.slice(word.targetStart);
      if (terminator) heredocs.push({ terminator, stripTabs: word.heredoc.stripTabs, expand: !word.quoted });
      else pendingHeredoc = word.heredoc;
    }
    words.push(word);
    word = null;
  };
  const endSegment = () => { endWord(); segments.push(words); words = []; };
  const toggleBackquote = () => {
    if (inBackquote) while (stack.length && stack.pop() !== "bq");
    else stack.push("bq");
    inBackquote = !inBackquote;
    endSegment();
  };
  const skipHeredocBodies = () => {
    for (const { terminator, stripTabs, expand } of heredocs) {
      const bodyStart = index;
      let bodyEnd = command.length;
      while (index < command.length) {
        const lineStart = index;
        const lineEnd = command.indexOf("\n", index);
        const line = command.slice(lineStart, lineEnd === -1 ? command.length : lineEnd).replace(/\r$/, "");
        index = lineEnd === -1 ? command.length : lineEnd + 1;
        if ((stripTabs ? line.replace(/^\t+/, "") : line) === terminator) { bodyEnd = lineStart; break; }
      }
      if (expand) segments.heredocBodies.push(command.slice(bodyStart, bodyEnd));
    }
    heredocs.length = 0;
  };
  const readRedirect = () => {
    let operator = "";
    if (command[index] === "&") { operator = "&"; index += 1; }
    while ((command[index] === "<" || command[index] === ">") && operator.replace("&", "").length < 3) {
      operator += command[index];
      index += 1;
    }
    if (operator.endsWith("<<") && command[index] === "-") { operator += "-"; index += 1; }
    else if ((command[index] === "&" || command[index] === "|") && !operator.startsWith("&")) { operator += command[index]; index += 1; }
    if (word && !word.redirect && /^\d+$/.test(word.text)) word.text += operator;
    else { endWord(); word = { text: operator, redirect: false, quoted: false }; }
    word.redirect = true;
    word.targetStart = word.text.length;
    const bare = operator.replace(/^\d*/, "");
    if (bare === "<<" || bare === "<<-") word.heredoc = { stripTabs: bare === "<<-" };
  };

  while (index < command.length) {
    const ch = command[index];
    const next = command[index + 1];
    const context = top();
    if (context === "sq") {
      if (ch === "'") stack.pop(); else append(ch);
      index += 1;
      continue;
    }
    if (context === "dq") {
      if (ch === "\"") { stack.pop(); index += 1; continue; }
      if (ch === "\\" && next !== undefined) {
        if (next === "\n") { index += 2; continue; }
        if ("$`\"\\".includes(next)) { append(next); index += 2; continue; }
        append(ch);
        index += 1;
        continue;
      }
      if (ch === "$" && next === "(") { stack.push("sub"); endSegment(); index += 2; continue; }
      if (ch === "`") { toggleBackquote(); index += 1; continue; }
      append(ch);
      index += 1;
      continue;
    }
    if (ch === "\\") {
      if (next === undefined) { index += 1; continue; }
      if (next === "\n") { index += 2; continue; }
      append(next);
      word.quoted = true;
      index += 2;
      continue;
    }
    if (respectQuotes && (ch === "'" || ch === "\"")) {
      startWord();
      word.quoted = true;
      stack.push(ch === "'" ? "sq" : "dq");
      index += 1;
      continue;
    }
    if (respectQuotes && ch === "$" && (next === "'" || next === "\"")) { index += 1; continue; }
    if (ch === "$" && next === "(") { stack.push("sub"); endSegment(); index += 2; continue; }
    if (ch === "`") { toggleBackquote(); index += 1; continue; }
    if (ch === "(") { stack.push("paren"); endSegment(); index += 1; continue; }
    if (ch === ")") {
      if (top() === "sub" || top() === "paren") stack.pop();
      endSegment();
      index += 1;
      continue;
    }
    if (ch === "\n") {
      endSegment();
      index += 1;
      if (heredocs.length) skipHeredocBodies();
      continue;
    }
    if (ch === ";" || ch === "|" || (ch === "&" && next !== ">")) { endSegment(); index += 1; continue; }
    if (ch === "<" || ch === ">" || ch === "&") { readRedirect(); continue; }
    if (ch === " " || ch === "\t" || ch === "\r" || ch === "\v" || ch === "\f") { endWord(); index += 1; continue; }
    if (ch === "#" && !word) {
      const lineEnd = command.indexOf("\n", index);
      index = lineEnd === -1 ? command.length : lineEnd;
      continue;
    }
    append(ch);
    index += 1;
  }
  endSegment();
  if (respectQuotes && (stack.includes("sq") || stack.includes("dq"))) {
    return splitSimpleCommands(command, false);
  }
  return segments;
}

function basename(text) {
  return text.slice(text.lastIndexOf("/") + 1).toLowerCase();
}

// Number of words a redirection occupies: `>file` and `2>&1` are complete,
// `> file` and `<< EOF` also consume the target word.
function redirectWidth(word) {
  return word.text.length > word.targetStart ? 1 : 2;
}

// `sh -c STRING`: skip shell options, then parse the first positional as a
// command. A first positional without `-c` is a script file, which the rail
// does not read.
function shellDashCRunsPrivileged(words, start, depth) {
  let sawDashC = false;
  let index = start;
  while (index < words.length) {
    const word = words[index];
    if (word.redirect) { index += redirectWidth(word); continue; }
    const text = word.text;
    if (text.length > 1 && (text.startsWith("-") || text.startsWith("+"))) {
      if (/^-[^-]*c/.test(text)) sawDashC = true;
      index += SHELL_OPTIONS_WITH_ARGUMENT.has(text) ? 2 : 1;
      continue;
    }
    return sawDashC && isRawPrivilegedCommand(text, depth + 1);
  }
  return false;
}

function segmentRunsPrivileged(words, depth) {
  let index = 0;
  while (index < words.length) {
    const word = words[index];
    if (word.redirect) { index += redirectWidth(word); continue; }
    const text = word.text;
    if (ASSIGNMENT_PATTERN.test(text) || SHELL_RESERVED_WORDS.has(text)) { index += 1; continue; }
    const base = basename(text);
    if (PRIVILEGED_BINARIES.has(base)) return true;
    if (base === "clawosctl") {
      const target = words.slice(index + 1).find((candidate) => !candidate.redirect && !candidate.text.startsWith("-"));
      return target?.text.toLowerCase() === "commit";
    }
    if (base === "eval") {
      return isRawPrivilegedCommand(words.slice(index + 1).map((candidate) => candidate.text).join(" "), depth + 1);
    }
    if (SHELL_INTERPRETERS.has(base)) return shellDashCRunsPrivileged(words, index + 1, depth);
    if (base === "find") {
      return words.some((candidate, position) => position > index
        && FIND_EXEC_OPTIONS.has(candidate.text)
        && segmentRunsPrivileged(words.slice(position + 1), depth));
    }
    const argumentOptions = COMMAND_WRAPPERS.get(base);
    if (argumentOptions === undefined) return false;
    index += 1;
    while (index < words.length) {
      const option = words[index];
      if (option.redirect) { index += redirectWidth(option); continue; }
      const optionText = option.text;
      if (base === "env" && /^(?:-S|--split-string)/.test(optionText)) {
        // `env -S STRING` (also `-SSTRING`, `--split-string=STRING`) splits STRING into a command of its own.
        const inline = optionText.replace(/^(?:-S|--split-string)=?/, "");
        return isRawPrivilegedCommand(inline || words[index + 1]?.text || "", depth + 1);
      }
      if (base === "command" && /^-[^-]*[vV]/.test(optionText)) return false; // `command -v` looks a name up, it runs nothing
      if (optionText.length > 1 && optionText.startsWith("-")) {
        index += argumentOptions.includes(optionText) ? 2 : 1;
        continue;
      }
      if (NUMERIC_POSITIONAL_PATTERN.test(optionText)) { index += 1; continue; }
      break;
    }
  }
  return false;
}

// True when the command line, as a shell would parse it, runs one of the
// privileged binaries as a command word. Catches separators (`;`, `&&`, `||`,
// `|`, `&`, newlines, subshells, `$(...)` and backticks, including inside an
// unquoted heredoc body), leading VAR=value assignments, redirections before
// the command word, path prefixes, quoting and backslash tricks, the wrapper
// allowlist above, `sh/bash/zsh/dash -c STRING`, `eval` and `find -exec`.
//
// This is a guidance rail, not a sandbox. It does not read script files
// (`bash install.sh`, `./install.sh`, `source x`, `curl ... | bash`), does not
// see inside other interpreters (`python -c`, `perl -e`, `node -e`), does not
// resolve variables, aliases, functions defined earlier or command strings that
// are themselves command output (`x=sudo; $x`, `sh -c "$(cat cmd)"`), does not
// know wrappers missing from COMMAND_WRAPPERS (`chroot`, `nsenter`,
// `ssh localhost`, `make`), and only ever sees the `exec` tool: a file written
// with another tool and run later, or any non-exec route to root, passes it.
// The `uncaught` table in test/embodiment.test.js states these limits.
export function isRawPrivilegedCommand(command, depth = 0) {
  if (typeof command !== "string" || command.trim() === "") return false;
  if (depth > MAX_SHELL_NESTING) return true;
  const segments = splitSimpleCommands(command);
  return segments.some((words) => segmentRunsPrivileged(words, depth))
    || segments.heredocBodies.some((body) => commandSubstitutions(body)
      .some((inner) => isRawPrivilegedCommand(inner, depth + 1)));
}

// The `$(...)` and backtick bodies inside expanding text (an unquoted heredoc).
function commandSubstitutions(text) {
  const found = [];
  let index = 0;
  while (index < text.length) {
    if (text[index] === "\\") { index += 2; continue; }
    if (text.startsWith("$(", index)) {
      let depth = 1;
      let end = index + 2;
      while (end < text.length && depth > 0) {
        if (text[end] === "(") depth += 1;
        else if (text[end] === ")") depth -= 1;
        end += 1;
      }
      found.push(text.slice(index + 2, depth === 0 ? end - 1 : end));
      index = end;
      continue;
    }
    if (text[index] === "`") {
      const end = text.indexOf("`", index + 1);
      found.push(text.slice(index + 1, end === -1 ? text.length : end));
      index = end === -1 ? text.length : end + 1;
      continue;
    }
    index += 1;
  }
  return found;
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
  if (!isRawPrivilegedCommand(command)) return null;
  return {
    block: true,
    blockReason: "ClawOS privileged actions must use clawos_system so the exact typed action is approved, audited, and recoverable.",
  };
}
