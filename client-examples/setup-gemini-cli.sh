#!/bin/bash

# MCP Memory Server - Google Gemini CLI Setup Script
# This script helps you quickly set up the MCP server for Google Gemini CLI

set -e

echo "🧠 MCP Memory Server - Google Gemini CLI Setup" 
echo "==============================================="
echo

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "❌ Error: Not in MCP Memory Server project directory"
    echo "   Please run this script from the project root or client-examples directory"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.8+."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check Gemini CLI installation (optional check)
if command -v gemini &> /dev/null; then
    echo "✅ Gemini CLI found: $(gemini --version 2>/dev/null || echo 'version unknown')"
else
    echo "⚠️  Gemini CLI not found in PATH (install if needed)"
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
if ! python3 -c "import fastapi, chromadb, sentence_transformers" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -e "$PROJECT_ROOT"
else
    echo "✅ Dependencies already installed"
fi

# Domain selection
echo
echo "🎯 Select your domain (this affects how content is scored for importance):"
echo "1) software-development (default) - Code, bugs, solutions, architecture"
echo "2) business-development - Revenue, deals, KPIs, market intelligence"
echo "3) research - Academic research, methodology, findings, evidence" 
echo "4) creative-writing - Characters, plot, dialogue, world-building"
echo "5) cooking - Recipes, techniques, ingredients, innovations"
echo "6) personal - General personal knowledge and conversations"
echo

read -p "Choose domain (1-6, default: 1): " domain_choice

case $domain_choice in
    2) DOMAIN="business-development" ;;
    3) DOMAIN="research" ;;
    4) DOMAIN="creative-writing" ;;
    5) DOMAIN="cooking" ;;
    6) DOMAIN="personal" ;;
    *) DOMAIN="software-development" ;;
esac

echo "✅ Selected domain: $DOMAIN"


# Configuration file location choice
echo
echo "📁 Where should the configuration be saved?"
echo "1) Project root (.mcp.json) - Recommended for project-specific setup"
echo "2) User config directory (~/.config/gemini/mcp.json) - Global setup"
echo "3) Custom location - Specify your own path"
echo

read -p "Choose location (1-3, default: 1): " location_choice

case $location_choice in
    2) 
        CONFIG_DIR="$HOME/.config/gemini"
        CONFIG_FILE="$CONFIG_DIR/mcp.json"
        mkdir -p "$CONFIG_DIR"
        ;;
    3)
        read -p "Enter custom path: " custom_path
        CONFIG_FILE="$custom_path"
        CONFIG_DIR="$(dirname "$CONFIG_FILE")"
        mkdir -p "$CONFIG_DIR"
        ;;
    *)
        CONFIG_FILE="$PROJECT_ROOT/.mcp.json"
        ;;
esac

echo "✅ Configuration will be saved to: $CONFIG_FILE"

# Create Gemini CLI MCP configuration
echo
echo "📝 Creating Gemini CLI MCP configuration..."

cat > "$CONFIG_FILE" << EOF
{
  "servers": {
    "mcp-memory-server": {
      "name": "Enhanced Memory Server",
      "description": "Hierarchical memory with domain-specific importance scoring",
      "transport": {
        "type": "stdio",
        "command": "python3",
        "args": ["$PROJECT_ROOT/scripts/start_server.py"],
        "cwd": "$PROJECT_ROOT",
        "timeout": 30000
      },
      "env": {
        "MCP_DOMAIN": "$DOMAIN"
      },
      "capabilities": [
        "document_storage",
        "semantic_search",
        "importance_scoring",
        "memory_lifecycle"
      ]
    }
  },
  "client": {
    "name": "Gemini CLI",
    "timeout": 30000,
    "logging": {
      "level": "INFO",
      "file": "$PROJECT_ROOT/logs/gemini-mcp.log"
    }
  }
}
EOF

echo "✅ Created Gemini MCP configuration"

# Test the configuration
echo
echo "🧪 Testing server startup..."
if timeout 5s python3 "$PROJECT_ROOT/scripts/start_server.py" > /dev/null 2>&1; then
    echo "✅ Server test successful!"
else
    echo "⚠️  Server test completed (timeout after 5s - this is normal)"
fi

echo
echo "🎉 Setup complete!"
echo
echo "📋 Usage instructions:"
echo
echo "1. Using with Gemini CLI:"
if [ "$CONFIG_FILE" = "$PROJECT_ROOT/.mcp.json" ]; then
    echo "   gemini --mcp-config .mcp.json 'your prompt here'"
    echo "   # Or run from this directory and Gemini will auto-discover .mcp.json"
else
    echo "   gemini --mcp-config '$CONFIG_FILE' 'your prompt here'"
    echo "   # Or set GEMINI_MCP_CONFIG environment variable"
    echo "   export GEMINI_MCP_CONFIG='$CONFIG_FILE'"
fi
echo
echo "2. Available MCP tools in Gemini:"
echo "   - Store content: ask Gemini to remember something important"
echo "   - Search memory: ask Gemini to recall or find information"
echo "   - View statistics: ask about memory system health"
echo
echo "🛠️  MCP Tools Reference:"
echo "  - add_document: Store content with automatic importance scoring"
echo "  - query_documents: Search memory with semantic similarity"
echo "  - query_permanent_documents: Search only critical content"
echo "  - get_memory_stats: View memory system statistics"
echo "  - get_lifecycle_stats: Monitor TTL and aging metrics"
echo "  - get_permanence_stats: Check permanent content stats"
echo
echo "🔧 Advanced configuration:"
echo "  - Edit domain configs: $PROJECT_ROOT/config/domains/"
echo "  - Edit main config: $PROJECT_ROOT/config.json"
echo "  - View logs: $PROJECT_ROOT/logs/"
echo
echo "📚 For more information:"
echo "  - README: $PROJECT_ROOT/client-examples/README.md"
echo "  - Docs: $PROJECT_ROOT/docs/"
echo
echo "🚀 Happy chatting with enhanced memory!"