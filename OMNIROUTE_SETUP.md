# OmniRoute + Claude Code Setup Guide

This guide walks you through setting up OmniRoute on your local machine to use your Claude Code API credentials and models (Claude Sonnet 5, Claude Opus, etc.) through a local router with intelligent fallback and circuit breaker support.

## Prerequisites

- Node.js 20+ installed (`node --version`)
- npm (`npm --version`)
- A Claude Code account with API access
- About 5 minutes

## Step 1: Install OmniRoute Globally

```bash
npm install -g omniroute
```

Verify installation:
```bash
omniroute --version
```

## Step 2: Start OmniRoute Server

```bash
omniroute serve
```

This will:
- Start the OmniRoute daemon on port 20128 (default)
- Open your browser to the dashboard at `http://localhost:20128`
- Display an admin API key (save this for reference)

**Note:** Keep this terminal open, or start it as a background daemon with:
```bash
omniroute serve --daemon --no-open
```

## Step 3: Connect Your Claude Code Account via OAuth

In a new terminal:

```bash
omniroute oauth start --provider claude-code
```

This will:
1. Generate an OAuth authorization URL with PKCE security
2. Open your default browser to Claude's login page
3. Ask you to authorize OmniRoute to access your API credentials
4. Automatically exchange the code and save your credentials

**Scopes authorized:**
- `org:create_api_key` – Create API keys for accessing your models
- `user:profile` – Access your account profile
- `user:inference` – Run inference with your subscribed models
- `user:sessions:claude_code` – Manage Claude Code sessions
- `user:mcp_servers` – Configure MCP servers

Once complete, OmniRoute has securely stored your Claude credentials and is ready to route requests.

## Step 4: Launch Claude Code Through OmniRoute

```bash
omniroute launch --api-key $(omniroute admin:get-token) --port 20128
```

Or use the convenience script (see below).

## (Optional) Create a Convenience Script

To make launching easier, create a shell script called `omni-claude` in your system PATH:

**macOS/Linux:**
```bash
cat > /usr/local/bin/omni-claude << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

PORT="${OMNIROUTE_PORT:-20128}"
API_KEY="${OMNIROUTE_API_KEY:-$(omniroute admin:get-token 2>/dev/null || echo '')}"
BASE_URL="http://localhost:${PORT}"

is_up() {
  curl -s -m 3 -o /dev/null -w '%{http_code}' "${BASE_URL}/v1/models" \
    -H "authorization: Bearer ${API_KEY}" 2>/dev/null | grep -q '^200$' || return 1
}

if ! is_up; then
  echo "OmniRoute no responde en ${BASE_URL}, arrancando..." >&2
  omniroute serve --daemon --no-open --port "${PORT}" >&2

  for _ in $(seq 1 30); do
    sleep 1
    is_up && break
  done

  if ! is_up; then
    echo "OmniRoute no llegó a estar listo tras 30s. Revisa 'omniroute status'." >&2
    exit 1
  fi
  echo "OmniRoute listo." >&2
fi

API_KEY="${OMNIROUTE_API_KEY:-$(omniroute admin:get-token 2>/dev/null || echo 'sk-default')}"
exec omniroute launch --api-key "${API_KEY}" --port "${PORT}" "$@"
EOF

chmod +x /usr/local/bin/omni-claude
```

Now you can simply run:
```bash
omni-claude
```

The script will:
1. Check if OmniRoute daemon is running
2. Auto-start it if needed (waits up to 30 seconds)
3. Launch Claude Code through it

## Usage

### Quick Launch
```bash
omniroute launch
```
or with the script:
```bash
omni-claude
```

### Check Status
```bash
omniroute status
```

### View Available Models
```bash
curl -s http://localhost:20128/v1/models \
  -H "authorization: Bearer $(omniroute admin:get-token)"
```

### Use with Claude Code CLI
```bash
omniroute launch --api-key $(omniroute admin:get-token)
```

Or let Claude Code auto-detect OmniRoute:
```bash
omniroute launch
```

## Configuration

### Environment Variables

```bash
# Custom OmniRoute port
export OMNIROUTE_PORT=20128

# Custom API key (optional, auto-detected from admin)
export OMNIROUTE_API_KEY="your-key-here"
```

### Dashboard Access

Open your browser to: `http://localhost:20128`

From here you can:
- View connected providers (your Claude Code account)
- Check model availability and health
- Configure circuit breakers and fallback behavior
- Monitor request logs and performance

## Troubleshooting

### OmniRoute Won't Start
```bash
# Check if port is in use
lsof -i :20128

# Try a different port
omniroute serve --port 20129
```

### OAuth Authorization Failed
- Ensure your Claude Code account has valid API access
- Check your browser console for error messages
- Try: `omniroute oauth start --provider claude-code --force`

### Models Not Available
- Verify the provider is connected: `omniroute status`
- Check health: Dashboard → Providers → Claude Code
- Restart: `omniroute serve --daemon --no-open`

### Claude Code Can't Connect
```bash
# Verify OmniRoute is running and healthy
curl -s http://localhost:20128/v1/models \
  -H "authorization: Bearer $(omniroute admin:get-token)"

# Check firewall/permissions
```

## Security Notes

✅ **What's Secure:**
- Credentials stored locally in `~/.omniroute/` (encrypted)
- OAuth uses PKCE (Proof Key for Code Exchange) – industry standard
- No credentials transmitted to external services
- Communication is local HTTP (no TLS needed for localhost)

⚠️ **Best Practices:**
- Keep your admin API key private (don't share or commit)
- Run OmniRoute on trusted networks only
- Review connected providers in the dashboard periodically
- Use `omniroute serve` in a terminal tab (not always-running daemon) for easy monitoring

## Next Steps

1. **Set up local development:** Configure your IDE to use OmniRoute's endpoint
2. **Create MCP servers:** Use OmniRoute with Claude Code's MCP server features
3. **Monitor usage:** Check the dashboard for quota and performance metrics
4. **Customize fallback:** In the dashboard, configure circuit breakers and model aliases as needed

## Additional Resources

- OmniRoute Docs: https://omniroute.ai/docs
- Claude Code Integration: https://claude.ai/code
- OAuth PKCE Standard: https://tools.ietf.org/html/rfc7636

---

**Last updated:** 2026-09-01  
**OmniRoute version:** 3.8.49+  
**Claude Code models supported:** Claude Sonnet 5, Claude Opus, Claude Haiku, and others in your subscription
