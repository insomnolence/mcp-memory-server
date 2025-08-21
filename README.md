> **Note:** This is a personal project that is ongoing.
>

---

# Enhanced MCP Memory Server

A personal project exploring intelligent hierarchical memory management for AI systems through the Model Context Protocol (MCP). Features an interactive configuration wizard, domain-agnostic design, and experimental lifecycle management. Born out of need to have a kind of "memory" for AI agents I was using, this helps keep context and knowlege from session to session.

## Key Features

- **3-Tier Memory Architecture**: Short-term, long-term, and permanent memory collections
- **Configuration Wizard**: Interactive setup wizard with template support and guided configuration
- **Universal Domain Support**: Works with ANY domain - business, research, creative, technical, etc.
- **Intelligent Importance Scoring**: Multi-factor algorithm combining semantic similarity, recency, frequency, and domain patterns
- **Automatic Lifecycle Management**: TTL-based expiration with importance-weighted aging and jitter
- **Permanence System**: Critical knowledge preservation with automatic and explicit permanence triggers
- **Background Maintenance**: Automated cleanup and health monitoring
- **FastAPI Implementation**: Modular architecture with MCP tools API

## Quick Start

### Prerequisites

- Python 3.8+
- pip (requirements.txt provided)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd MCPServer

# Install dependencies
pip install -r requirements.txt

# Run the configuration wizard
python3 scripts/config_wizard.py

# Start the server
python3 scripts/start_server.py
```

### 30-Second Setup (Templates)

```bash
# Quick setup with pre-configured templates
python3 scripts/config_wizard.py template

# Choose from:
# 1. Development (recommended for coding projects)
# 2. Research (extended retention, analysis-focused)  
# 3. Creative (writing, brainstorming)
# 4. Business (meetings, processes)
# 5. Minimal (resource-constrained environments)
# 6. Maximum (extensive retention)
```

## Configuration Options

### Interactive Wizard
```bash
python3 scripts/config_wizard.py              # Full interactive setup
python3 scripts/config_wizard.py --help       # Show usage options
python3 scripts/config_wizard.py --non-interactive  # Automation-friendly
```

The wizard helps configure:
- **Memory retention strategies** (hours to permanent)
- **Server accessibility** (localhost, network, custom)
- **Domain-specific keywords** (custom pattern recognition)
- **Performance preferences** (accuracy vs speed)
- **Storage allocation** (minimal to extensive)
- **Advanced settings** (thresholds, intervals)

### Manual Configuration
Edit `config.json` directly or use domain-specific configs in `config/domains/`:
- `config.business-development.json` - Business operations
- `config.research.json` - Research and analysis
- `config.creative-writing.json` - Creative projects
- `config.cooking.json` - Culinary domain

## Project Structure

```
MCPServer/
├── src/mcp_memory_server/      # Modular server implementation
│   ├── config/                 # Configuration management
│   ├── memory/                 # Hierarchical memory system
│   │   ├── scorer.py          # Importance scoring algorithm
│   │   ├── hierarchical.py    # 4-tier memory architecture
│   │   └── lifecycle.py       # TTL and maintenance
│   ├── server/                # FastAPI MCP server
│   └── tools/                 # MCP tools implementation
├── config/                    # Configuration files
│   ├── domains/              # Domain-specific examples
│   └── example.json          # Configuration template  
├── scripts/                  # Management scripts
│   ├── config_wizard.py     # Professional setup wizard
│   ├── start_server.py      # Server startup
│   └── validate_config.py   # Configuration validation
├── data/memory/             # ChromaDB persistence (auto-created)
├── logs/                    # Server logs (auto-created)
├── client-examples/         # AI client configurations
└── docs/                    # Comprehensive documentation
```

## MCP Tools API

The server exposes comprehensive MCP tools for memory management:

### Document Management
- **`add_document_tool`** - Add content with automatic importance scoring and collection routing
- **`query_documents_tool`** - Multi-collection semantic search with intelligent reranking
- **`query_permanent_documents_tool`** - Search only critical/permanent content

### System Monitoring  
- **`get_memory_stats_tool`** - Collection statistics and system health metrics
- **`get_lifecycle_stats_tool`** - TTL management and aging system status
- **`get_permanence_stats_tool`** - Permanent content analytics

### Lifecycle Management
- **`start_background_maintenance_tool`** - Enable automated maintenance processes
- **`stop_background_maintenance_tool`** - Disable background maintenance

## Memory Architecture

### Four-Tier System
1. **Short-term Memory** - Recent interactions with auto-pruning (default: 100 items)
2. **Long-term Memory** - Important persistent knowledge (importance ≥ 0.7)  
3. **Permanent Memory** - Critical knowledge preserved indefinitely (importance ≥ 0.95)
4. **Consolidated Memory** - Compressed summaries of related memories

### Intelligent Scoring
- **Semantic Analysis** (40%) - Content relevance and similarity
- **Recency Weighting** (30%) - Time-based importance decay
- **Frequency Analysis** (20%) - Access pattern recognition  
- **Explicit Importance** (10%) - User-defined priority

### Lifecycle Management
- **TTL with Jitter** - Prevents mass expiration events
- **Importance-based Aging** - Critical content ages slower
- **Automatic Consolidation** - Related memories compressed into summaries
- **Background Maintenance** - Continuous optimization without blocking operations

## Domain Examples

Configure for **any domain** with custom keywords - no code changes needed:

### Business Intelligence
```json
{
  "domain_patterns": {
    "patterns": {
      "business_metrics": {
        "keywords": ["revenue", "KPI", "ROI", "conversion", "growth"],
        "bonus": 0.35
      }
    }
  }
}
```

### Scientific Research  
```json
{
  "domain_patterns": {
    "patterns": {
      "research_findings": {
        "keywords": ["hypothesis", "methodology", "p-value", "correlation"],
        "bonus": 0.4
      }
    }
  }
}
```

**Works for**: Software development, creative writing, cooking, astronomy, fitness, music, law, medicine, education, and more.

## Upcoming Enhancements

### Universal Embedding Providers (Next Release)
Expanding beyond HuggingFace to support multiple embedding providers:
- **OpenAI** (text-embedding-3-small/large) - High quality, API-based
- **Azure OpenAI** - Enterprise integration with existing Azure infrastructure  
- **Cohere** - Cost-effective alternative with good performance
- **Ollama** - Local deployment for privacy-sensitive environments
- **Migration System** - Seamless upgrades from current HuggingFace setup

This enhancement will provide greater flexibility in deployment scenarios while maintaining backward compatibility.

## Performance Characteristics

- **Storage Efficiency**: Intelligent lifecycle management reduces memory footprint
- **Query Speed**: Fast semantic search with reranking
- **Memory Consolidation**: Automatic clustering to preserve knowledge while saving space
- **Configuration Validation**: Built-in validation to catch configuration issues

## Experimentation & Testing

### Validation
```bash
# Validate configuration  
python3 scripts/validate_config.py

# Test server startup
python3 scripts/start_server.py  # Ctrl+C to stop
```

### Configuration Management
```bash
# Reconfigure anytime
python3 scripts/config_wizard.py

# Check different templates
python3 scripts/config_wizard.py template

# Use environment variables for domains
MCP_DOMAIN=research python3 scripts/start_server.py
```

## Documentation

- **`docs/configuration.md`** - Complete configuration guide and manual setup
- **`docs/configuration-wizard-enhanced.md`** - Configuration wizard features and usage
- **`docs/architecture.md`** - System architecture and design overview  
- **`docs/domain-configuration.md`** - Domain-specific pattern configuration
- **`client-examples/`** - Ready-to-use configurations for Claude Code CLI and other clients
- **`docs/README.md`** - Complete documentation index

## Client Integration

The server works with any MCP-compatible client. Example configurations provided for:
- **Claude Code CLI** - Complete setup scripts included
- **Gemini CLI** - Full integration examples
- **Custom Clients** - Comprehensive MCP protocol implementation

## Advanced Usage

### Different Configurations
```bash
# Default local development
python3 scripts/start_server.py

# Use domain-specific configuration  
MCP_DOMAIN=research python3 scripts/start_server.py

# Custom configuration file
python3 scripts/start_server.py --config custom-config.json
```

### Monitoring Features
- **Configuration Backups** - Automatic backup when changing settings
- **Structured Logging** - Logs saved to `logs/mcp_server.log`  
- **Memory Statistics** - Built-in tools to monitor system usage
- **Validation Tools** - Configuration checking and server health

## Future Enhancements

### Planned Features
- **Memory Consolidation** - Automatic summarization and compression of related memories
- **Advanced Analytics** - Usage patterns and memory effectiveness metrics
- **Multi-Provider Embeddings** - Support for OpenAI, Azure, Cohere embedding models
- **Enhanced Monitoring** - Comprehensive dashboards and alerts

---

*This is a personal experimental project exploring MCP memory systems. The configuration wizard transforms technical parameters into user-friendly questions, making it easier to experiment with different memory strategies.*
