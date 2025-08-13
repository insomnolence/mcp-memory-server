# Quick Start - MCP Memory Server Client Setup

## 🚀 One-Command Setup

### Claude Code CLI (Recommended)
```bash
# Run the setup script
./client-examples/setup-claude-code.sh

# Or manually copy
cp client-examples/dot-mcp.json .mcp.json
```

### Google Gemini CLI
```bash
# Run the setup script
./client-examples/setup-gemini-cli.sh

# Or manually copy and configure
cp client-examples/gemini-cli-mcp.json .mcp.json
```

## 📁 File Guide

| File | Purpose | Use Case |
|------|---------|----------|
| `dot-mcp.json` | **Claude Code CLI** (simple) | Rename to `.mcp.json` in project root |
| `claude-code-mcp.json` | **Claude Code CLI** (detailed) | Full configuration with comments |
| `claude-desktop-config.json` | **Claude Desktop App** | Copy to `~/.claude/claude_desktop_config.json` |
| `gemini-cli-mcp.json` | **Google Gemini CLI** | Use with `--mcp-config` flag |
| `gemini-mcp-config.json` | **Gemini (generic)** | For other Gemini MCP implementations |
| `generic-mcp-config.json` | **Any MCP Client** | Template for other AI systems |

## ⚡ Quick Test

```bash
# 1. Copy config
cp client-examples/dot-mcp.json .mcp.json

# 2. Test server
python3 scripts/start_server.py

# 3. Use with Claude Code CLI
# The .mcp.json file will be auto-discovered
```

## 🎯 Domain Selection

Edit the `MCP_DOMAIN` in your config file:

- `software-development` - Code, bugs, solutions (default)
- `business-development` - Revenue, deals, KPIs  
- `research` - Academic research, findings
- `creative-writing` - Characters, plot, dialogue
- `cooking` - Recipes, techniques
- `personal` - General knowledge

## 💡 Pro Tips

1. **Use setup scripts** for guided configuration
2. **Start with development environment** for testing
3. **Check logs** if connection fails: `tail -f logs/mcp_server.log`
4. **Test manually first**: `python3 scripts/start_server.py`
5. **Multiple domains**: Create separate config files

## 🆘 Troubleshooting

**Server won't start?**
```bash
pip install -e .
python3 scripts/start_server.py
```

**Client can't connect?**
```bash
# Check config file path
ls -la .mcp.json

# Verify server is running
curl http://127.0.0.1:8081/health
```

**Wrong domain scoring?**
```bash
# Check domain setting in your config
grep MCP_DOMAIN .mcp.json

# List available domains
ls config/domains/
```

For detailed setup instructions, see [README.md](README.md)