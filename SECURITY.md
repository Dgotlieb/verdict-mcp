# Security posture

verdict exists partly *because* agents running arbitrary test commands directly on a developer machine is a bad default. This document says exactly what verdict does and does not protect against. Honest boundaries beat implied ones.

## What a check run gets (container mode)

Check runs execute in an ephemeral container (podman preferred — rootless by default — or docker):

- The worktree is mounted **read-only** at `/src` and copied to a writable `/work` inside the container. Your working tree is never written to by a check run.
- Check runs get `--network=none`. Test code cannot exfiltrate or download.
- The container is `--rm` ephemeral: no state survives except the report file written to the artifacts mount.
- Nothing from your host environment is passed in except `VERDICT_ARTIFACTS`.

## Known limitations (v0.1)

- **`setup_cmd` runs with network access.** If you configure on-the-fly dependency installation, that step can reach the network by design. A prebuilt image (`runner.image`) is the tighter posture and the recommended one.
- **Container escape is out of scope.** verdict relies on the runtime's isolation. A kernel/runtime escape defeats it. Rootless podman narrows the blast radius; it does not eliminate it.
- **The local fallback (`prefer = "local"`) is a convenience, not a sandbox.** It protects your worktree (checks run against a temp copy) but test code runs as your user with your environment and network. Use it knowingly.
- **Resource limits are not enforced yet** (fork bombs, disk fill inside the container). Planned: `--memory`, `--pids-limit`, `--cpus` defaults in v0.2.
- **verdict's own history db** (`.verdict/history.db`) is plain SQLite in your repo dir; treat it as local state, don't commit it.

## Reporting

Open a private security advisory on GitHub or email the maintainer. Please do not open public issues for exploitable problems.
