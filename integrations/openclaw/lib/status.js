import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import os from "node:os";

function readText(path) {
  try {
    return readFileSync(path, "utf8").trim();
  } catch {
    return null;
  }
}

function readOsIdentity() {
  const source = readText("/etc/os-release");
  if (!source) return { id: "linux", name: "Linux", isClawOS: false };

  const values = Object.fromEntries(
    source
      .split("\n")
      .map((line) => line.match(/^([A-Z0-9_]+)=(.*)$/))
      .filter(Boolean)
      .map((match) => [match[1], match[2].replace(/^"|"$/g, "")]),
  );

  const id = (values.ID || "linux").toLowerCase();
  const name = values.PRETTY_NAME || values.NAME || "Linux";
  return { id, name, isClawOS: id === "clawos" };
}

function readBattery() {
  const raw = readText("/sys/class/power_supply/BAT0/capacity");
  const value = raw === null ? Number.NaN : Number(raw);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : null;
}

function readOpenClawVersion() {
  try {
    const output = execFileSync("/usr/bin/openclaw", ["--version"], {
      encoding: "utf8", timeout: 2500, stdio: ["ignore", "pipe", "ignore"],
    });
    return output.match(/OpenClaw\s+([^\s]+)/)?.[1] || null;
  } catch {
    return null;
  }
}

function bytesToGiB(bytes) {
  return Math.round((bytes / 1024 ** 3) * 10) / 10;
}

function readBroker() {
  try {
    const status = JSON.parse(execFileSync("/usr/lib/clawos/clawosctl", ["status"], {
      encoding: "utf8", timeout: 1200, stdio: ["ignore", "pipe", "ignore"],
    }));
    const capabilities = JSON.parse(execFileSync("/usr/lib/clawos/clawosctl", ["capabilities"], {
      encoding: "utf8", timeout: 1200, stdio: ["ignore", "pipe", "ignore"],
    }));
    return {
      available: true,
      state: status.state,
      message: `${status.pendingCount} action${status.pendingCount === 1 ? "" : "s"} waiting for approval`,
      pendingCount: status.pendingCount,
      securityLevel: status.securityLevel,
      apiVersion: status.apiVersion,
      openclawUpdate: capabilities.actions?.["openclaw.update"] || null,
    };
  } catch {
    return {
      available: false,
      state: "unavailable",
      message: "clawosd is unavailable; privileged actions are blocked",
      pendingCount: 0,
      openclawUpdate: null,
    };
  }
}

export function collectMachineStatus() {
  const osIdentity = readOsIdentity();
  const totalMemory = os.totalmem();
  const usedMemory = Math.max(0, totalMemory - os.freemem());
  const load = os.loadavg();

  return {
    apiVersion: 1,
    role: process.env.CLAWOS_ROLE || "standalone",
    securityLevel: process.env.CLAWOS_SECURITY_LEVEL || "full-user-approvals",
    hostname: os.hostname(),
    operatingSystem: osIdentity.name,
    isClawOS: osIdentity.isClawOS,
    kernel: `${os.type()} ${os.release()}`,
    architecture: os.arch(),
    uptimeSeconds: Math.floor(os.uptime()),
    memory: {
      usedGiB: bytesToGiB(usedMemory),
      totalGiB: bytesToGiB(totalMemory),
      percent: totalMemory === 0 ? 0 : Math.round((usedMemory / totalMemory) * 100),
    },
    load: load.map((value) => Math.round(value * 100) / 100),
    batteryPercent: readBattery(),
    broker: readBroker(),
    openclawVersion: readOpenClawVersion(),
    recovery: {
      available: true,
      shortcut: "Ctrl+Alt+F3",
    },
    observedAt: new Date().toISOString(),
  };
}
