# Tilt Debugging Workflows

## Debug a Failing Resource

When a resource is in error state, follow this systematic approach:

### Step 1: Get Overview
```bash
tilt get uiresource -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('items', []):
    name = item['metadata']['name']
    s = item.get('status', {})
    rt = s.get('runtimeStatus', '?')
    up = s.get('updateStatus', '?')
    ds = s.get('disableStatus', {}).get('state', '?')
    err = (s.get('buildHistory', [{}])[0] or {}).get('error', '')
    icon = '✓' if rt == 'ok' and up in ('ok','not_applicable') else '✗' if rt == 'error' or up == 'error' else '…'
    line = f'{icon} {name:30s} runtime={rt:15s} update={up:15s} [{ds}]'
    if err: line += f' ERROR: {err[:80]}'
    print(line)
"
```

### Step 2: Inspect the Failing Resource
```bash
# Get detailed description
tilt describe uiresource <resource-name>

# Get recent error logs (native --level flag)
tilt logs <resource-name> --level error --tail 50

# Get last 200 lines for context
tilt logs <resource-name> --tail 200

# For regex filtering beyond error/warn levels, pipe to grep
tilt logs <resource-name> --tail 500 | grep -iE 'exception|traceback|fatal|panic'
```

### Step 3: Common Fixes
- **Build error**: Check Dockerfile, dependencies, syntax errors in code
- **Runtime error**: Check container logs for crash loops, missing env vars, port conflicts
- **Pending forever**: Check if dependencies are healthy, look for resource constraints
- **Not started**: Run `tilt trigger <resource-name>` for manual-trigger resources

### Step 4: After Fixing
```bash
# Trigger rebuild
tilt trigger <resource-name>

# Wait for it to be ready
tilt wait uiresource/<resource-name> --for=condition=Ready --timeout=60s

# Verify
tilt logs <resource-name> --tail 20
```

## Health Check All Resources

Quick health check across the entire dev environment:

```bash
# Summary view
tilt get uiresource -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
healthy = errors = updating = other = 0
error_list = []
for item in data.get('items', []):
    s = item.get('status', {})
    if s.get('disableStatus', {}).get('state') == 'Disabled': continue
    rt, up = s.get('runtimeStatus', '?'), s.get('updateStatus', '?')
    name = item['metadata']['name']
    if rt == 'ok' and up in ('ok', 'not_applicable'): healthy += 1
    elif rt == 'error' or up == 'error': errors += 1; error_list.append(name)
    elif up in ('in_progress', 'pending'): updating += 1
    else: other += 1
print(f'Healthy: {healthy} | Errors: {errors} | Updating: {updating} | Other: {other}')
if error_list: print(f'Failing: {', '.join(error_list)}')
"
```

## Optimize Resource Usage

When you only need certain services running:

```bash
# Enable only what you need (disables everything else)
tilt enable --only backend database redis

# Wait for all to be ready
for r in backend database redis; do
  tilt wait uiresource/$r --for=condition=Ready --timeout=60s
done

# Verify
tilt get uiresource -o json | python3 -c "
import json, sys
for item in json.load(sys.stdin).get('items', []):
    s = item.get('status', {})
    if s.get('disableStatus', {}).get('state') == 'Disabled': continue
    name = item['metadata']['name']
    rt = s.get('runtimeStatus', '?')
    print(f'{name}: {rt}')
"
```

## Analyze Logs for Patterns

Look for recurring errors or performance issues:

```bash
# Count error types (use --tail to limit scope, grep for pattern extraction)
tilt logs <resource> --tail 2000 | grep -ioE '(error|exception|warning|timeout|refused)[^"]*' | sort | uniq -c | sort -rn | head -20

# Find slow requests (if using structured logs)
tilt logs <resource> --since 10m | grep -oE 'duration=[0-9.]+' | sort -t= -k2 -rn | head -10

# Check for restart loops
tilt logs <resource> --source runtime --tail 500 | grep -i 'starting\|started\|listening\|ready'
```

## Troubleshoot Startup Failures

Common startup issues and how to diagnose them:

```bash
# Check for missing env vars
tilt logs <resource> --source runtime --tail 200 | grep -iE 'env|variable|undefined|not set|missing'

# Check for port conflicts
tilt logs <resource> --source runtime --tail 200 | grep -iE 'address already in use|EADDRINUSE|bind'

# Check for dependency issues
tilt logs <resource> --source build --tail 200 | grep -iE 'module not found|import|require|dependency|package'

# Check for memory/resource issues
tilt logs <resource> --level error --tail 200 | grep -iE 'OOM|killed|memory|heap|allocation'
```
