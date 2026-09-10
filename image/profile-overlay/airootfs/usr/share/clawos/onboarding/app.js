const state = {
  step: "welcome",
  mode: "local",
  access: "full-root",
  lastPayload: null,
};

const stepOrder = ["welcome", "gateway", "agent", "access", "install"];
const steps = [...document.querySelectorAll("[data-step]")];
const progressButtons = [...document.querySelectorAll("[data-step-target]")];

function showStep(name) {
  state.step = name;
  steps.forEach((step) => step.classList.toggle("active", step.dataset.step === name));
  const position = stepOrder.indexOf(name);
  progressButtons.forEach((button, index) => {
    button.classList.toggle("active", index === position);
    button.classList.toggle("complete", index < position);
    if (index === position) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
    button.setAttribute("aria-disabled", String(index > position));
    button.tabIndex = index > position ? -1 : 0;
  });
  const activeStep = document.querySelector(`[data-step="${name}"]`);
  const focusTarget = activeStep?.querySelector(".choice.selected") ||
    activeStep?.querySelector("input:not(:disabled), button");
  focusTarget?.focus();
}

function selectMode(mode) {
  state.mode = mode;
  document.querySelectorAll("[data-mode]").forEach((button) => button.classList.toggle("selected", button.dataset.mode === mode));
  document.querySelector("#local-agent-fields").hidden = mode !== "local";
  document.querySelector("#remote-agent-fields").hidden = mode !== "remote";
}

function selectAccess(access) {
  state.access = access;
  document.querySelectorAll("[data-access]").forEach((button) => button.classList.toggle("selected", button.dataset.access === access));
}

function validateAgent() {
  const error = document.querySelector("#agent-error");
  error.textContent = "";
  if (state.mode === "remote" && !/^wss?:\/\//i.test(document.querySelector("#remote-url").value.trim())) {
    error.textContent = "Enter a Gateway URL beginning with ws:// or wss://.";
    return false;
  }
  return true;
}

function payload() {
  if (state.mode === "local") {
    return {
      mode: "local",
      access: state.access,
      provider: "skip",
    };
  }
  return {
    mode: "remote",
    access: state.access,
    remoteUrl: document.querySelector("#remote-url").value.trim(),
    remoteToken: document.querySelector("#remote-token").value.trim(),
  };
}

async function install() {
  if (!validateAgent()) {
    showStep("agent");
    return;
  }
  state.lastPayload = payload();
  showStep("install");
  document.querySelector("#install-progress").hidden = false;
  document.querySelector("#ready-state").hidden = true;
  document.querySelector("#failed-state").hidden = true;

  const fill = document.querySelector("#install-track-fill");
  const message = document.querySelector("#install-message");
  const messages = [
    [24, "Securing Gateway credentials…"],
    [46, "Installing the OpenClaw service…"],
    [68, "Preparing the Agent workspace…"],
    [84, "Checking the machine connection…"],
  ];
  let index = 0;
  const timer = window.setInterval(() => {
    if (index < messages.length) {
      fill.style.width = `${messages[index][0]}%`;
      message.textContent = messages[index][1];
      document.querySelectorAll(".install-list span").forEach((item, itemIndex) => item.classList.toggle("active", itemIndex === index));
      index += 1;
    }
  }, 2400);

  try {
    const response = await fetch("/api/setup", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(state.lastPayload),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || "Setup failed.");
    fill.style.width = "100%";
    window.setTimeout(() => {
      document.querySelector("#install-progress").hidden = true;
      document.querySelector("#ready-state").hidden = false;
      document.querySelector("#launch-button").focus();
    }, 500);
  } catch (error) {
    document.querySelector("#install-progress").hidden = true;
    document.querySelector("#failed-state").hidden = false;
    document.querySelector("#failure-message").textContent = error instanceof TypeError
      ? "The local setup service stopped responding. Retry, or open the recovery console."
      : error instanceof Error ? error.message : "OpenClaw setup failed.";
  } finally {
    window.clearInterval(timer);
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.mode) selectMode(button.dataset.mode);
  if (button.dataset.access) selectAccess(button.dataset.access);
  if (button.dataset.stepTarget && stepOrder.indexOf(button.dataset.stepTarget) <= stepOrder.indexOf(state.step)) {
    showStep(button.dataset.stepTarget);
  }
  if (button.dataset.back) showStep(button.dataset.back);
  if (button.dataset.next) {
    if (state.step === "agent" && !validateAgent()) return;
    showStep(button.dataset.next);
  }
});

document.querySelector("#install-button").addEventListener("click", install);
document.querySelector("#retry-button").addEventListener("click", install);
document.querySelector("#launch-button").addEventListener("click", async () => {
  const response = await fetch("/api/finish", { method: "POST", headers: {"content-type": "application/json"},
    body: JSON.stringify({allowUnconfigured: document.querySelector("#configure-later").checked}) });
  if (!response.ok) document.querySelector("#provider-error").textContent = (await response.json()).error || "Could not enter the Agent workspace.";
});
document.querySelector("#configure-later").addEventListener("change", refreshProvider);
document.querySelector("#provider-later-button").addEventListener("click", () => {
  document.querySelector("#configure-later").checked = true;
  refreshProvider();
});
document.querySelector("#provider-setup-button").addEventListener("click", async () => {
  try {
    const response = await fetch("/api/provider-setup", {method: "POST"});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    await refreshProvider();
  } catch (error) { document.querySelector("#provider-error").textContent = error.message || "Could not open OpenClaw setup."; }
});

async function refreshProvider() {
  try {
    const response = await fetch("/api/provider-status");
    if (!response.ok) throw new Error("Provider setup status unavailable.");
    const status = await response.json();
    const remote = state.mode === "remote";
    document.querySelector("#provider-description").textContent = remote
      ? "This node uses the provider and model configured on your existing Gateway. Manage those choices there."
      : "Choose your provider and model in the native OpenClaw wizard, then return here. No provider credentials are collected by this page.";
    document.querySelector("#provider-setup-button").hidden = remote;
    document.querySelector("#provider-setup-button").disabled = status.providerSetup.running;
    document.querySelector("#provider-setup-button").textContent = status.selectedModel ? "Change provider or model" : "Choose provider and model";
    document.querySelector("#provider-setup-button").classList.toggle("primary", !status.selectedModel);
    document.querySelector("#provider-setup-button").classList.toggle("quiet", !!status.selectedModel);
    document.querySelector("#provider-later-button").hidden = remote || !!status.selectedModel || document.querySelector("#configure-later").checked;
    document.querySelector("#provider-later-button").disabled = status.providerSetup.running;
    document.querySelector("#model-status").textContent = remote ? "The remote Gateway owns provider and model selection." :
      status.providerSetup.running ? "OpenClaw setup is open. Complete it there, then return here." :
      status.selectedModel ? `Selected model: ${status.selectedModel}` : "No model selected. Continue with OpenClaw or choose to configure later.";
    document.querySelector("#provider-error").textContent = status.providerSetup.error || "";
    document.querySelector("#launch-button").disabled = status.providerSetup.running ||
      (!remote && !status.selectedModel && !document.querySelector("#configure-later").checked);
  } catch {
    document.querySelector("#model-status").textContent = "Model selection status unavailable. Retry when the setup service is ready.";
    document.querySelector("#launch-button").disabled = true;
  }
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/status");
    const status = await response.json();
    document.querySelectorAll("[data-network-dot]").forEach((dot) => dot.classList.toggle("online", status.network));
    document.querySelectorAll("[data-network-label]").forEach((label) => {
      label.textContent = status.network ? "Network connected" : "Network required";
    });
    if (status.mode) selectMode(status.mode);
    if (status.access) selectAccess(status.access);
    if (status.mode && status.setupComplete) {
      showStep("install");
      document.querySelector("#install-progress").hidden = true;
      document.querySelector("#ready-state").hidden = false;
      document.querySelector("#failed-state").hidden = true;
    } else if (status.mode && status.stage !== "start") {
      showStep("install");
      document.querySelector("#install-progress").hidden = true;
      document.querySelector("#ready-state").hidden = true;
      document.querySelector("#failed-state").hidden = false;
      document.querySelector("#failure-message").textContent =
        `Setup was interrupted after ${status.stage}. Review the connection settings, then retry to resume.`;
    }
  } catch {
    document.querySelectorAll("[data-network-label]").forEach((label) => {
      label.textContent = "Setup service unavailable";
    });
  }
}

selectMode("local");
selectAccess("full-root");
refreshStatus();
refreshProvider();
window.setInterval(refreshProvider, 2500);
