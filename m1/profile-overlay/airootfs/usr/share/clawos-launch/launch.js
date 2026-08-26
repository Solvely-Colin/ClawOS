const launch = document.querySelector("#launch");
const title = document.querySelector("#state-title");
const copy = document.querySelector("#state-copy");
const dialog = document.querySelector("#support-dialog");
const dialogTitle = document.querySelector("#dialog-title");
const dialogCopy = document.querySelector("#dialog-copy");

launch.addEventListener("click", () => {
  launch.disabled = true;
  launch.querySelector("span:first-child").textContent = "Opening OpenClaw";
  title.textContent = "Starting your session";
  copy.textContent = "Handing this machine to the OpenClaw workspace…";

  setTimeout(() => {
    window.location.assign("http://127.0.0.1:18789/");
  }, 650);
});

const support = {
  recovery: {
    title: "Recovery is available",
    copy: "Press Ctrl+Alt+F3 for the independent recovery console. It remains available even when the graphical shell or OpenClaw is unavailable."
  },
  terminal: {
    title: "Terminal access",
    copy: "The full OpenClaw workspace provides the persistent terminal. For emergency local access, use Ctrl+Alt+F3."
  }
};

document.querySelectorAll("[data-panel]").forEach((button) => {
  button.addEventListener("click", () => {
    const panel = support[button.dataset.panel];
    dialogTitle.textContent = panel.title;
    dialogCopy.textContent = panel.copy;
    dialog.showModal();
  });
});
