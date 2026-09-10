# Share the source, not a release promise

## Short announcement

ClawOS is open for contributors: an experimental agent-native OS built on Arch
Linux, with OpenClaw as its primary interface. The goal is an agent that can
inspect and change its own machine, with visible approvals and recovery tools.

We have VM evidence for encrypted and passwordless installs, and a CI-built
image has completed a graphical encrypted install and default onboarding.
There is still substantial work on agent workflows, recovery, installation
testing and the desktop experience. Full Root is trusted-agent mode, not a
sandbox. Physical hardware is unverified.

This is public source, not a supported distribution or downloadable release.
Use a disposable VM and build your own ISO. Small contributions to docs,
tests, accessibility and OS integration are welcome.

- [Repository](https://github.com/Solvely-Colin/ClawOS)
- [Start here](https://github.com/Solvely-Colin/ClawOS/issues/86)
- [Getting started](GETTING-STARTED.md)
- [Known limitations](KNOWN-ISSUES.md)

## Claims to avoid

Do not advertise any-Arch-hardware support, production readiness, automatic
full-system recovery, proven provider inference on the fresh CI image, or
containment of an untrusted root agent. A successful build is not those proofs.
When sharing a screenshot or demo, identify whether it shows the installed OS
or the frozen browser prototype; never present the prototype as runtime proof.
Remove credentials, private messages and machine-specific data before sharing.
