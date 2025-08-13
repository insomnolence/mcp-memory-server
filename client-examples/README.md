# MCP Memory Server - Client Configuration Examples

This directory contains configuration examples for connecting various AI clients to the MCP Memory Server.

## 🚀 Quick Start

1. **Choose your AI client** from the configurations below
2. **Copy the appropriate config file** to the correct location
3. **Update the paths** to match your installation
4. **Select your domain** (business, research, creative-writing, etc.)
5. **Start using the memory server** with your AI!

## 📋 Available Configurations

### Claude Code CLI
- **File**: `dot-mcp.json` (rename to `.mcp.json`)
- **Location**: Project root or `~/.config/claude-code/`
- **Usage**: Claude Code automatically discovers `.mcp.json` files

```bash
# Copy to project root (recommended)
cp client-examples/dot-mcp.json .mcp.json

# Or copy to user config directory
cp client-examples/dot-mcp.json ~/.config/claude-code/.mcp.json
```

### Claude Desktop
- **File**: `claude-desktop-config.json`
- **Location**: 
  - macOS: `~/.claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - Linux: `~/.config/claude/claude_desktop_config.json`

### Google Gemini
- **File**: `gemini-mcp-config.json`
- **Usage**: Configure according to your Gemini client's MCP support

### Generic/Other AI Clients
- **File**: `generic-mcp-config.json`
- **Usage**: Template for any MCP-compatible AI client

## ⚙️ Configuration Options

### Domain Selection
Choose the domain that matches your use case:

- **`software-development`** - Code, bugs, solutions, architecture (default)
- **`business-development`** - Revenue, deals, KPIs, market intelligence  
- **`research`** - Academic research, methodology, findings, evidence
- **`creative-writing`** - Characters, plot, dialogue, world-building
- **`cooking`** - Recipes, techniques, ingredients, innovations
- **`personal`** - General personal knowledge and conversations


### Connection Methods

#### STDIO (Recommended)
```json
{
  "command": "python3",
  "args": ["scripts/start_server.py"],
  "env": {
    "MCP_DOMAIN": "your-domain"
  }
}
```

#### HTTP (For remote servers)
```json
{
  "httpUrl": "http://your-server:8081",
  "timeout": 10000
}
```

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
# From the project root
pip install -e .
```

### 2. Choose Your Configuration
```bash
# For Claude Code CLI (most common)
cp client-examples/dot-mcp.json .mcp.json

# Edit the domain in .mcp.json
nano .mcp.json
```

### 3. Update Paths
Edit your chosen config file and update:
- Paths to match your installation directory
- Domain selection for your use case

### 4. Test Connection
```bash
# Test server startup
python3 scripts/start_server.py

# Verify it's working
curl http://127.0.0.1:8081/health
```

## 🎯 Domain-Specific Examples

### For Software Development
```json
{
  "env": {
    "MCP_DOMAIN": "software-development"
  }
}
```
**Best for**: Code snippets, bug reports, architectural decisions, technical documentation

### For Business Use
```json
{
  "env": {
    "MCP_DOMAIN": "business-development"
  }
}
```
**Best for**: Meeting notes, deal information, market research, KPI tracking

### For Research Projects
```json
{
  "env": {
    "MCP_DOMAIN": "research"
  }
}
```
**Best for**: Research findings, methodology notes, literature reviews, data analysis

### For Creative Writing
```json
{
  "env": {
    "MCP_DOMAIN": "creative-writing"
  }
}
```
**Best for**: Character development, plot ideas, world-building, dialogue

## 🔧 Advanced Configuration

### Custom Config File
```json
{
  "env": {
    "MCP_CONFIG_PATH": "/path/to/custom/config.json"
  }
}
```

### Custom Data Directory
```json
{
  "env": {
    "MCP_DATA_PATH": "/path/to/custom/data"
  }
}
```

### Multiple Servers (Different Domains)
```json
{
  "mcpServers": {
    "memory-work": {
      "command": "python3",
      "args": ["scripts/start_server.py"],
      "env": { "MCP_DOMAIN": "business-development" }
    },
    "memory-research": {
      "command": "python3", 
      "args": ["scripts/start_server.py"],
      "env": { "MCP_DOMAIN": "research" }
    }
  }
}
```

## 🚨 Troubleshooting

### Server Won't Start
1. Check Python path: `which python3`
2. Verify dependencies: `pip install -e .`
3. Test manually: `python3 scripts/start_server.py`

### Connection Timeout
1. Increase timeout in config file
2. Check server logs: `tail -f logs/mcp_server.log`
3. Verify port isn't in use: `lsof -i :8081`

### Wrong Domain Scoring
1. Verify `MCP_DOMAIN` environment variable
2. Check domain config exists: `ls config/domains/`
3. Review scoring patterns in domain config

## 📚 Available MCP Tools

Once configured, your AI client will have access to:

- **`add_document`** - Store content with automatic importance scoring
- **`query_documents`** - Search memory with semantic similarity
- **`query_permanent_documents`** - Search only critical/permanent content
- **`get_memory_stats`** - View memory system statistics
- **`get_lifecycle_stats`** - Monitor TTL and aging statistics
- **`get_permanence_stats`** - Check permanent content statistics

## 💡 Tips for Best Results

1. **Choose the right domain** for better content scoring
2. **Use descriptive content** when adding documents
3. **Leverage permanence flags** for critical information
4. **Monitor memory stats** to understand system health
5. **Adjust importance thresholds** in domain configs as needed

## 🆘 Need Help?

- Check the main project README.md
- Review the `/docs` directory for detailed documentation
- Test with the generic config template first
- Verify server functionality before client configuration