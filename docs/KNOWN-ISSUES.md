# Current development boundaries

- **Fullscreen/layout:** Windows QEMU has an absolute tablet, but setup-window
  offset/clipping remains under investigation. Scaling is not fully solved.
- **Task context:** supporting-surface prompts can still target the fixed main
  session instead of the conversation owning the terminal/browser/build.
- **Startup:** configuration presence, onboarding completion, model readiness,
  desktop readiness and repair state need a coherent model. Gateway reachability
  is not proof of successful model inference.
- **Recovery:** runtime file rollback works; coordinated root/home/credential/
  database/boot rollback is not proven.
- **Authority:** typed high-impact actions require approval, but Full Root has
  unrestricted passwordless sudo. It is a trusted-agent mode, not containment.
- **Fresh installs:** repeat the full build/install/onboarding/agent-update loop
  on a clean disk. Existing VM state can hide provisioning defects. Offline
  installation and physical T2 hardware need further proof.
- **Compatibility:** the version-checked OpenClaw delivery adapter needs review
  when upgrading that dependency.
- **Design/docs:** plans and prototype guidance include superseded layouts.
  Consolidate the current Carapace adapter and acceptance checklist.
- **Omarchy:** targeted source/runtime checks found no active dependency, but
  do not certify every asset and package's provenance.
- **Public release:** license choice, complete attribution, release artifacts
  and a fresh publication-time credential review remain open.
