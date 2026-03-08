---
name: tilt
description: Manage and monitor Tilt dev environment resources. Use when checking build/deploy status, viewing logs, debugging failing resources, triggering rebuilds, or enabling/disabling services. Activates for any Tilt-related development workflow task.
allowed-tools: Bash(tilt *)
---

# Tilt Dev Environment Management

## Overview

This skill calls direct `tilt` CLI commands. All operations use the local `tilt` binary.

For advanced debugging workflows, see [workflows.md](workflows.md).

## Quick Reference

| Operation | Command |
|-----------|---------|
| List resources | `tilt get uiresource -o json` |
| Get logs | `tilt logs <resource>` |
| Describe resource | `tilt describe uiresource <resource>` |
| Trigger rebuild | `tilt trigger <resource>` |
| Enable resources | `tilt enable <resource1> <resource2>` |
| Enable only these | `tilt enable --only <resource1> <resource2>` |
| Disable resources | `tilt disable <resource1> <resource2>` |
| Wait for ready | `tilt wait uiresource/<resource> --for=condition=Ready --timeout=30s` |
| Wait for updated | `tilt wait uiresource/<resource> --for=condition=UpToDate --timeout=30s` |

## Multi-Instance Support

By default, Tilt runs on port 10350. When working on multiple projects on the same dev machine, append `--port {port_number}` to any command to target a different Tilt instance (e.g. `tilt get uiresource -o json --port 10351`).

## Commands in Detail

### List All Resources with Status

```bash
tilt get uiresource -o json
```

Parse the JSON output to get resource status. Key fields per resource:
- `metadata.name` — Resource name
- `status.runtimeStatus` — `ok`, `error`, `pending`, `not_applicable`, `none`
- `status.updateStatus` — `ok`, `error`, `pending`, `in_progress`, `not_applicable`, `none`
- `status.disableStatus.state` — `Enabled` or `Disabled`
- `status.conditions[]` — Array with `type` (Ready/UpToDate), `status` (True/False), `reason`
- `status.buildHistory[0].error` — Latest build error (if any)

**Health status derivation:**
- **healthy**: runtimeStatus=ok AND updateStatus=ok/not_applicable
- **error**: runtimeStatus=error OR updateStatus=error
- **updating**: updateStatus in (in_progress, pending)
- **running**: runtimeStatus in (ok, pending)
- **not_started**: both statuses = "none" (manual trigger mode)
- **disabled**: disableStatus.state = "Disabled"

### Get Resource Logs

```bash
# Last N lines (native --tail flag, no piping needed)
tilt logs <resource> --tail 200

# Show only errors/warnings (native --level flag)
tilt logs <resource> --level error --tail 100

# Logs from last 5 minutes
tilt logs <resource> --since 5m

# Only build logs or only runtime logs
tilt logs <resource> --source build
tilt logs <resource> --source runtime

# Combine native flags with grep for regex filtering
tilt logs <resource> --tail 500 | grep -iE 'exception|traceback'

# Filter by request ID
tilt logs <resource> | grep 'X-Request-Id: abc123'
```

### Describe Resource (Detailed Info)

```bash
tilt describe uiresource <resource>
```

Returns configuration, conditions, build history, and current state.

### Trigger Resource Rebuild

```bash
tilt trigger <resource>
```

Forces a rebuild/update of the resource. Useful for manual-trigger resources or to force a fresh build.

### Enable/Disable Resources

```bash
# Enable specific resources
tilt enable resource1 resource2

# Enable ONLY these (disables all others — saves system resources)
tilt enable --only resource1 resource2

# Disable specific resources
tilt disable resource1 resource2
```

### Wait for Conditions

```bash
# Wait for resource to be ready (most common)
tilt wait uiresource/<resource> --for=condition=Ready --timeout=30s

# Wait for resource to be up-to-date
tilt wait uiresource/<resource> --for=condition=UpToDate --timeout=30s
```

**Valid conditions:** `Ready`, `UpToDate`

**Before waiting**, always pre-check the resource status to avoid waiting on terminal failures:
1. If `disableStatus.state` = "Disabled" → enable it first
2. If `runtimeStatus` = "error" OR `updateStatus` = "error" → investigate the error, don't wait
3. If both statuses = "none" → trigger it first with `tilt trigger`
4. If both statuses = "not_applicable" → resource can't reach the condition

## Best Practices

1. **Always check status before waiting** — saves time on terminal failures
2. **Use `--only` when focusing** — conserves memory/CPU by disabling unused services
3. **Use native log flags first** — `--tail`, `--since`, `--level`, `--source` are more efficient than piping; use `grep` only for regex patterns not covered by native flags
4. **Check build errors first** — `tilt describe uiresource <name>` shows the latest build error at a glance
5. **Use JSON output for parsing** — always use `-o json` when you need to programmatically process resource data
