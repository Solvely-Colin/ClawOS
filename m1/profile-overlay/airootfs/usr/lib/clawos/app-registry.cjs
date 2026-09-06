"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const appIdPattern = /^[a-z][a-z0-9._:-]{0,127}$/;
const desktopIdPattern = /^[A-Za-z0-9][A-Za-z0-9._-]{0,191}$/;

function cleanText(value, max = 160) {
  if (typeof value !== "string") return "";
  return value.replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}

function booleanValue(value) {
  return String(value).toLowerCase() === "true";
}

function parseDesktopFile(filePath, desktopId) {
  let contents;
  try { contents = fs.readFileSync(filePath, "utf8"); } catch { return null; }
  const fields = {};
  let inDesktopEntry = false;
  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("[") && line.endsWith("]")) {
      inDesktopEntry = line === "[Desktop Entry]";
      continue;
    }
    if (!inDesktopEntry) continue;
    const equals = line.indexOf("=");
    if (equals < 1) continue;
    const key = line.slice(0, equals);
    if (key.includes("[")) continue;
    fields[key] = line.slice(equals + 1);
  }

  if (
    fields.Type !== "Application" ||
    booleanValue(fields.Hidden) ||
    booleanValue(fields.NoDisplay) ||
    !fields.Name ||
    !fields.Exec
  ) return null;

  const customId = fields["X-ClawOS-AppId"];
  const fallbackId = `desktop:${desktopId.replace(/\.desktop$/i, "")}`.toLowerCase();
  const id = appIdPattern.test(customId || "") ? customId : fallbackId;
  const kind = ["desktop", "web", "surface"].includes(fields["X-ClawOS-Kind"])
    ? fields["X-ClawOS-Kind"]
    : "desktop";

  return {
    id,
    desktopId,
    name: cleanText(fields.Name, 96),
    comment: cleanText(fields.Comment, 200),
    icon: cleanText(fields.Icon, 128),
    kind,
    agentCapability: cleanText(fields["X-ClawOS-AgentCapability"], 96),
    profile: cleanText(fields["X-ClawOS-Profile"], 96),
    browserProfile: cleanText(fields["X-ClawOS-BrowserProfile"], 96),
    surface: cleanText(fields["X-ClawOS-Surface"], 32),
    startupWmClass: cleanText(fields.StartupWMClass, 128),
    filePath,
  };
}

function applicationDirectories(env = process.env) {
  const home = env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
  const shared = (env.XDG_DATA_DIRS || "/usr/local/share:/usr/share")
    .split(":")
    .filter(Boolean);
  return [home, ...shared].map((directory) => path.join(directory, "applications"));
}

function listApplications(options = {}) {
  const env = options.env || process.env;
  const applications = new Map();
  for (const directory of applicationDirectories(env)) {
    let entries;
    try { entries = fs.readdirSync(directory, { withFileTypes: true }); } catch { continue; }
    for (const entry of entries) {
      if (!entry.isFile() || !entry.name.endsWith(".desktop") || applications.has(entry.name)) continue;
      if (!desktopIdPattern.test(entry.name)) continue;
      const parsed = parseDesktopFile(path.join(directory, entry.name), entry.name);
      if (parsed) applications.set(entry.name, parsed);
    }
  }
  return [...applications.values()].sort((left, right) => left.name.localeCompare(right.name));
}

function resolveApplication(query, options = {}) {
  if (!query || typeof query !== "object") return null;
  const normalizedDesktopId = typeof query.desktopId === "string"
    ? (query.desktopId.endsWith(".desktop") ? query.desktopId : `${query.desktopId}.desktop`)
    : "";
  return listApplications(options).find((application) =>
    (typeof query.appId === "string" && application.id === query.appId) ||
    (normalizedDesktopId && application.desktopId === normalizedDesktopId),
  ) || null;
}

function publicApplication(application) {
  const { filePath: _filePath, ...safe } = application;
  return safe;
}

function launchApplication(application, options = {}) {
  if (!application?.filePath || !path.isAbsolute(application.filePath)) throw new Error("Application is not launchable.");
  const child = spawn("/usr/bin/gio", ["launch", application.filePath], {
    detached: true,
    stdio: "ignore",
    env: options.env || process.env,
  });
  child.unref();
}

module.exports = {
  appIdPattern,
  desktopIdPattern,
  listApplications,
  resolveApplication,
  publicApplication,
  launchApplication,
};
