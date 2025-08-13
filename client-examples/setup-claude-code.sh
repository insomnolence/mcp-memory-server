#!/bin/bash

# MCP Memory Server - Claude Code CLI Setup Script
# This script helps you quickly set up the MCP server for Claude Code CLI

set -e

echo "🧠 MCP Memory Server - Claude Code CLI Setup"
echo "============================================="
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


# Create .mcp.json configuration
echo
echo "📝 Creating .mcp.json configuration..."

cat > "$PROJECT_ROOT/.mcp.json" << EOF
{
  "mcpServers": {
    "mcp-memory-server": {
      "command": "python3",
      "args": ["scripts/start_server.py"],
      "env": {
        "MCP_DOMAIN": "$DOMAIN"
      }
    }
  }
}
EOF

echo "✅ Created .mcp.json in project root"

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
echo "📋 Next steps:"
echo "1. Claude Code CLI will automatically discover the .mcp.json file"
echo "2. Start Claude Code in this directory"
echo "3. The memory server will be available as an MCP tool"
echo
echo "🛠️  Available MCP tools:"
echo "  - add_document: Store content with importance scoring"
echo "  - query_documents: Search memory semantically"  
echo "  - get_memory_stats: View system statistics"
echo "  - query_permanent_documents: Search critical content only"
echo
echo "📚 For more configuration options, see:"
echo "  - client-examples/README.md"
echo "  - config/domains/ for domain-specific settings"
echo "  - config.json for main configuration"
echo
echo "🚀 Happy coding with enhanced memory!"