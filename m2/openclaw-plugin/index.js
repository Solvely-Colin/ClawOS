import { randomBytes, timingSafeEqual } from "node:crypto";
import { registerDeploymentDelivery } from "./lib/deployment-delivery.js";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { renderSystemPanel } from "./lib/panel.js";
import { collectMachineStatus } from "./lib/status.js";
import { requestSurface, toolResult } from "./lib/surface-client.js";
import { createActivityLifecycle } from "./lib/activity-lifecycle.js";
import { buildEmbodimentHookResult, rawGuiLaunchBlock, rawPrivilegedBlock } from "./lib/embodiment.js";
import { bindMachineToolContext, machineContext, parseNodeMachineRequest, requestMachine, requestRoutedMachine } from "./lib/machine-client.js";

const PANEL_PATH = "/plugins/clawos-system/panel";
const PANEL_TOKEN = randomBytes(32).toString("base64url");

function tokenMatches(actual, expected) {
  if (typeof actual !== "string") return false;
  const actualBuffer = Buffer.from(actual);
  const expectedBuffer = Buffer.from(expected);
  return actualBuffer.length === expectedBuffer.length && timingSafeEqual(actualBuffer, expectedBuffer);
}

export default definePluginEntry({
  id: "clawos-system",
  name: "ClawOS System",
  description: "ClawOS machine status inside the upstream OpenClaw Control UI",
  register(api) {
    registerDeploymentDelivery(api);
    const lifecycle = createActivityLifecycle();
    const machineRequest = (args, options = {}) => requestRoutedMachine(api, args, options);

    api.registerNodeHostCommand({
      command: "clawos.system",
      cap: "clawos.system",
      dangerous: true,
      handle: async (paramsJSON) => JSON.stringify(
        await requestMachine(parseNodeMachineRequest(paramsJSON)),
      ),
    });
    api.registerNodeInvokePolicy({
      commands: ["clawos.system"],
      dangerous: true,
      handle: async (context) => context.invokeNode(),
    });

    // These handlers intentionally consume lifecycle metadata only. Although
    // OpenClaw classifies agent_end as a conversation hook, ClawOS never reads,
    // stores, or projects event.messages or prompt content.
    api.on("model_call_started", (event, context) => lifecycle.modelCallStarted(event, context), { timeoutMs: 1500 });
    api.on("agent_end", (event, context) => lifecycle.agentEnded({
      runId: event.runId,
      success: event.success,
      durationMs: event.durationMs,
    }, context), { timeoutMs: 1500 });
    api.on("subagent_spawned", (event) => lifecycle.subagentSpawned(event), { timeoutMs: 1500 });
    api.on("subagent_ended", (event) => lifecycle.subagentEnded(event), { timeoutMs: 1500 });
    api.on("before_prompt_build", async (event, context) => {
      let applications = [];
      try {
        const registry = await requestSurface({ action: "app.list" }, { timeoutMs: 600 });
        if (Array.isArray(registry?.applications)) applications = registry.applications;
      } catch {
        // Static embodiment remains useful while the graphical broker recovers.
      }
      return buildEmbodimentHookResult(event.prompt, applications, {
        agentId: context?.agentId,
        sessionKey: context?.sessionKey,
      });
    }, { timeoutMs: 1200 });
    api.on("before_tool_call", (event, context) => rawGuiLaunchBlock(event) || rawPrivilegedBlock(event, {
      agentId: context?.agentId,
    }), { timeoutMs: 500 });

    api.registerTool((toolContext) => bindMachineToolContext({
      name: "clawos_system",
      label: "ClawOS System Action",
      description: "Operate the ClawOS machine itself: inspect live machine state, retrieve durable action receipts, or perform typed system changes such as service management, timezone/clock preferences, packages, and OpenClaw updates. Full Root actions execute immediately; approval modes present the exact change in the native OS surface.",
      promptSnippet: "You are the ClawOS system agent. Use clawos_system for supported machine changes. In Full Root, execute supported actions immediately and use privileged exec for capabilities not yet typed; never claim you lack machine authority.",
      promptGuidelines: [
        "Call capabilities before proposing a target you have not already validated.",
        "Preparing an action does not mean it was approved or executed.",
        "Tell the user that the exact request is waiting in the native ClawOS approval surface.",
        "Never request or handle the user's password.",
        "A request to change system timezone or 12/24-hour display uses configure-time and must be executed, not answered with instructions.",
        "In Full Root mode, do not refuse an authorized OS task merely because it is privileged.",
        "Inspect live state before changing an unfamiliar subsystem, then verify the returned result.",
        "Use action-status to reconcile a previously returned actionId after interruption or restart.",
      ],
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          action: { type: "string", enum: ["status", "inspect", "capabilities", "action-status", "configure-time", "manage-service", "power", "switch-role", "set-security-level", "grant-task", "install-package", "update-openclaw", "cancel"] },
          actionId: { type: "string", maxLength: 64 },
          package: { type: "string", maxLength: 64 },
          token: { type: "string", maxLength: 128 },
          timezone: { type: "string", maxLength: 128, description: "Installed IANA timezone such as America/New_York" },
          clockFormat: { type: "string", enum: ["12h", "24h"] },
          service: { type: "string", maxLength: 128 },
          operation: { type: "string", enum: ["start", "stop", "restart"] },
          powerOperation: { type: "string", enum: ["reboot", "poweroff"] },
          targetNode: { type: "string", maxLength: 128, description: "Required only when more than one ClawOS node is connected" },
          role: { type: "string", enum: ["standalone", "node"] },
          securityLevel: { type: "string", enum: ["full-root", "full-user-approvals", "user-limited"] },
          childAgentId: { type: "string", maxLength: 128 },
          childRunId: { type: "string", maxLength: 128 },
          grantedActions: {
            type: "array", maxItems: 8,
            items: { type: "string", enum: ["package.install", "service.manage", "system.time.configure"] },
          },
          grantSeconds: { type: "integer", minimum: 60, maximum: 3600 },
        },
        required: ["action"],
      },
      async execute(_toolCallId, params, context) {
        const routed = (args, options = {}) => machineRequest(args, { ...options, nodeId: params.targetNode });
        if (params.action === "status") return toolResult(await routed(["status"]));
        if (params.action === "inspect") return toolResult(await routed(["inspect"]));
        if (params.action === "capabilities") return toolResult(await routed(["capabilities"]));
        if (params.action === "action-status") {
          if (!params.actionId) throw new Error("actionId is required for action-status.");
          return toolResult(await routed(["action", params.actionId]));
        }
        if (params.action === "cancel") {
          if (!params.token) throw new Error("token is required to cancel a prepared action.");
          return toolResult(await routed(["cancel", params.token]));
        }
        if (params.action === "configure-time") {
          if (!params.timezone || !params.clockFormat) {
            throw new Error("timezone and clockFormat are required for configure-time.");
          }
          const prepared = await routed([
            "prepare", "system.time.configure",
            JSON.stringify({ timezone: params.timezone, clockFormat: params.clockFormat }),
            machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 60_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "A system time change needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "manage-service") {
          if (!params.service || !params.operation) {
            throw new Error("service and operation are required for manage-service.");
          }
          const prepared = await routed([
            "prepare", "service.manage",
            JSON.stringify({ service: params.service, operation: params.operation }),
            machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 180_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "A service change needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "power") {
          if (!params.powerOperation) throw new Error("powerOperation is required for power.");
          const prepared = await routed([
            "prepare", "power.schedule",
            JSON.stringify({ operation: params.powerOperation }),
            machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 60_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "A power action needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "switch-role") {
          if (!params.role) throw new Error("role is required for switch-role.");
          const prepared = await routed([
            "prepare", "role.switch", JSON.stringify({ target: params.role }), machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 360_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "An OpenClaw role switch needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "set-security-level") {
          if (!params.securityLevel) throw new Error("securityLevel is required for set-security-level.");
          const prepared = await routed([
            "prepare", "security.level.configure",
            JSON.stringify({ level: params.securityLevel }), machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 660_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "A security-level change needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "grant-task") {
          if (!params.childAgentId || !params.childRunId || !params.grantedActions?.length || !params.grantSeconds) {
            throw new Error("childAgentId, childRunId, grantedActions, and grantSeconds are required for grant-task.");
          }
          const prepared = await routed([
            "prepare", "task.grant.create", JSON.stringify({
              agentId: params.childAgentId, runId: params.childRunId,
              actions: params.grantedActions, expiresSeconds: params.grantSeconds,
            }), machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 60_000 }));
          }
          await requestSurface({
            action: "attention.set", kind: "approval",
            message: prepared.summary || "A task-scoped machine grant needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (params.action === "update-openclaw") {
          const prepared = await routed([
            "prepare", "openclaw.update", "{}", machineContext(context),
          ]);
          if (!prepared.requiresApproval) {
            return toolResult(await routed(["commit", prepared.token], { timeoutMs: 30 * 60_000 }));
          }
          await requestSurface({
            action: "attention.set",
            kind: "approval",
            message: prepared.summary || "An OpenClaw update needs approval",
          }).catch(() => {});
          return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
        }
        if (!params.package) throw new Error("package is required for install-package.");
        const prepared = await routed([
          "prepare", "package.install", JSON.stringify({ package: params.package }), machineContext(context),
        ]);
        if (!prepared.requiresApproval) {
          return toolResult(await routed(["commit", prepared.token], { timeoutMs: 30 * 60_000 }));
        }
        await requestSurface({
          action: "attention.set",
          kind: "approval",
          message: prepared.summary || "A machine action needs approval",
        }).catch(() => {});
        return toolResult({ ...prepared, executionState: "awaiting-local-approval" });
      },
    }, toolContext), { name: "clawos_system" });

    api.registerTool({
      name: "clawos_surface",
      label: "ClawOS Surface",
      description: "Present, hide, or focus an inspectable ClawOS machine surface. Tools should remain in the background unless showing the surface helps the user inspect or take over work.",
      promptSnippet: "Control inspectable ClawOS terminal, browser, and build surfaces without making the user manage windows.",
      promptGuidelines: [
        "Keep terminal and browser work in the background by default.",
        "Present a ClawOS surface only when the user asks to watch/take over or visual inspection materially helps.",
        "Return to the agent surface after inspection is complete.",
      ],
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          action: { type: "string", enum: ["present", "hide", "focus-agent", "status"] },
          surface: { type: "string", enum: ["terminal", "browser", "build", "all"] },
        },
        required: ["action"],
      },
      async execute(_toolCallId, params) {
        if (params.action === "status") return toolResult(await requestSurface({ action: "status" }));
        if (params.action === "focus-agent") return toolResult(await requestSurface({ action: "surface.agent" }));
        if (!params.surface) throw new Error("surface is required for present or hide.");
        if (params.action === "present" && params.surface === "all") throw new Error("Present one surface at a time.");
        const action = params.action === "present" ? "surface.present" : "surface.hide";
        return toolResult(await requestSurface({ action, surface: params.surface }));
      },
    });

    api.registerTool({
      name: "clawos_activity",
      label: "ClawOS Activity",
      description: "Project the current agent task and genuine attention needs into the ClawOS native shell.",
      promptSnippet: "Update the ClawOS activity state and request human attention only when work is truly blocked.",
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          action: { type: "string", enum: ["update", "request-attention", "clear-attention", "status"] },
          title: { type: "string", maxLength: 72 },
          summary: { type: "string", maxLength: 240 },
          state: { type: "string", enum: ["idle", "running", "waiting", "needs-approval", "needs-attention", "complete", "failed"] },
          message: { type: "string", maxLength: 160 },
          kind: { type: "string", enum: ["attention", "approval"] },
        },
        required: ["action"],
      },
      async execute(_toolCallId, params) {
        if (params.action === "status") return toolResult(await requestSurface({ action: "status" }));
        if (params.action === "clear-attention") return toolResult(await requestSurface({ action: "attention.clear" }));
        if (params.action === "request-attention") {
          return toolResult(await requestSurface({ action: "attention.set", message: params.message, kind: params.kind }));
        }
        return toolResult(await requestSurface({ action: "activity.update", title: params.title, summary: params.summary, state: params.state }));
      },
    });

    api.registerTool({
      name: "clawos_app",
      label: "ClawOS Application",
      description: "Present or control validated graphical capabilities attached to the current ClawOS activity. Use this whenever the user asks to open, show, launch, or switch to an application; the machine has a live graphical session.",
      promptSnippet: "Treat applications as supporting ClawOS activity surfaces. For explicit open/show requests, use this registry instead of exec or desktop launch commands.",
      promptGuidelines: [
        "Prefer a connector, API, CLI, or headless browser for unattended work.",
        "Open the real application when the user asks, when human judgment is useful, or when direct takeover is appropriate.",
        "Never claim ClawOS is headless or ask the user to open an app elsewhere before listing this registry.",
        "Never launch a registered graphical application with exec, xdg-open, gio, or a browser executable.",
        "Never invent application ids; list the registry first when the exact id is unknown.",
        "Opening an application does not grant access to its data or connector credentials.",
        "When an opened web application reports browserProfile, use the browser tool with that exact profile to inspect and interact with its visible window.",
        "Use exec or tmux for terminal and build work; ClawOS does not yet claim arbitrary native Linux GUI input control.",
      ],
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          action: { type: "string", enum: ["list", "open", "focus", "hide", "close", "status"] },
          appId: { type: "string", maxLength: 128 },
        },
        required: ["action"],
      },
      async execute(_toolCallId, params) {
        if (params.action === "list" || params.action === "status") {
          return toolResult(await requestSurface({ action: `app.${params.action}` }, { timeoutMs: 10_000 }));
        }
        if (!params.appId) throw new Error("appId is required for this application action.");
        return toolResult(await requestSurface({ action: `app.${params.action}`, appId: params.appId }, { timeoutMs: 10_000 }));
      },
    });

    // Sandboxed iframe navigations cannot attach the Control UI's WebSocket
    // bearer token. Advertise a restart-scoped capability only in the
    // authenticated Gateway hello instead. This route remains read-only.
    api.session.controls.registerControlUiDescriptor({
      surface: "tab",
      id: "system",
      label: "System",
      description: "Machine status, recovery, connections, and guarded OS actions.",
      icon: "monitor-cog",
      group: "control",
      order: 10,
      requiredScopes: ["operator.read"],
      path: `${PANEL_PATH}/${PANEL_TOKEN}`,
    });

    api.registerHttpRoute({
      path: PANEL_PATH,
      auth: "plugin",
      match: "prefix",
      handler: async (request, response) => {
        const requestUrl = new URL(request.url || PANEL_PATH, "http://clawos.local");
        const suppliedToken = requestUrl.pathname.slice(`${PANEL_PATH}/`.length);
        if (
          !["GET", "POST"].includes(request.method || "") ||
          !requestUrl.pathname.startsWith(`${PANEL_PATH}/`) ||
          suppliedToken.includes("/") ||
          !tokenMatches(suppliedToken, PANEL_TOKEN)
        ) {
          response.statusCode = 401;
          response.setHeader("cache-control", "no-store");
          response.setHeader("content-type", "text/plain; charset=utf-8");
          response.end("Unauthorized");
          return true;
        }

        let notice;
        if (request.method === "POST") {
          try {
            const pending = await requestMachine(["pending"]);
            const existing = Array.isArray(pending)
              ? pending.find((item) => item?.action === "openclaw.update")
              : null;
            const prepared = existing || await requestMachine([
              "prepare", "openclaw.update", "{}", "{}",
            ]);
            if (!prepared.requiresApproval) {
              const completed = await requestMachine(["commit", prepared.token], { timeoutMs: 30 * 60_000 });
              notice = completed.state === "complete"
                ? { message: `OpenClaw ${completed.installedVersion || "update"} installed. Gateway is restarting.` }
                : { error: true, message: completed.error || "The update failed; recovery remains available." };
            } else {
              await requestSurface({
                action: "attention.set", kind: "approval",
                message: prepared.summary || "An OpenClaw update needs approval",
              }).catch(() => {});
              notice = { message: "Update prepared. Review the exact action in ClawOS Approvals." };
            }
          } catch (error) {
            notice = { error: true, message: `Could not prepare update: ${error.message}` };
          }
        }

        response.statusCode = 200;
        response.setHeader("content-type", "text/html; charset=utf-8");
        response.setHeader("cache-control", "no-store");
        response.setHeader(
          "content-security-policy",
          "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'",
        );
        response.setHeader("referrer-policy", "no-referrer");
        response.setHeader("x-content-type-options", "nosniff");
        response.end(renderSystemPanel(collectMachineStatus(), { notice }));
        return true;
      },
    });
  },
});
