import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);
const registry = require("../profile-overlay/airootfs/usr/lib/clawos/app-registry.cjs");

function writeDesktop(directory, name, contents) {
  const applications = path.join(directory, "applications");
  fs.mkdirSync(applications, { recursive: true });
  fs.writeFileSync(path.join(applications, name), contents);
}

test("registry discovers validated desktop and web applications with user precedence", (t) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "clawos-app-registry-"));
  t.after(() => fs.rmSync(temporary, { recursive: true, force: true }));
  const user = path.join(temporary, "user");
  const shared = path.join(temporary, "shared");
  const env = { ...process.env, XDG_DATA_HOME: user, XDG_DATA_DIRS: shared };

  writeDesktop(shared, "mail.desktop", `[Desktop Entry]\nType=Application\nName=Shared Mail\nExec=/usr/bin/true\n`);
  writeDesktop(user, "mail.desktop", `[Desktop Entry]\nType=Application\nName=User Mail\nExec=/usr/bin/true\nX-ClawOS-AppId=web:mail\nX-ClawOS-Kind=web\nX-ClawOS-AgentCapability=mail-api\nX-ClawOS-BrowserProfile=clawos-mail\n`);
  writeDesktop(shared, "hidden.desktop", `[Desktop Entry]\nType=Application\nName=Hidden\nExec=/usr/bin/true\nNoDisplay=true\n`);
  writeDesktop(shared, "terminal.desktop", `[Desktop Entry]\nType=Application\nName=Terminal\nExec=/usr/bin/true\nX-ClawOS-AppId=surface:terminal\nX-ClawOS-Kind=surface\nX-ClawOS-Surface=terminal\n`);

  const applications = registry.listApplications({ env });
  assert.deepEqual(applications.map((application) => application.name), ["Terminal", "User Mail"]);
  assert.equal(applications.find((application) => application.name === "User Mail").id, "web:mail");
  assert.equal(applications.find((application) => application.name === "User Mail").browserProfile, "clawos-mail");
  assert.equal(registry.resolveApplication({ desktopId: "mail" }, { env }).name, "User Mail");
  assert.equal(registry.resolveApplication({ appId: "surface:terminal" }, { env }).surface, "terminal");
  assert.equal(Object.hasOwn(registry.publicApplication(applications[0]), "filePath"), false);
});

test("invalid custom ids cannot become executable input", (t) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "clawos-app-registry-invalid-"));
  t.after(() => fs.rmSync(temporary, { recursive: true, force: true }));
  const emptyShared = path.join(temporary, "empty-shared");
  fs.mkdirSync(emptyShared);
  writeDesktop(temporary, "safe.desktop", `[Desktop Entry]\nType=Application\nName=Safe\nExec=/usr/bin/true\nX-ClawOS-AppId=../../run-me\n`);
  const env = { ...process.env, XDG_DATA_HOME: temporary, XDG_DATA_DIRS: emptyShared };
  const applications = registry.listApplications({ env });
  assert.equal(applications[0].id, "desktop:safe");
  assert.equal(registry.resolveApplication({ appId: "../../run-me" }, { env }), null);
});
