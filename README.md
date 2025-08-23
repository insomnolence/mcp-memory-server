# MCP Memory Server

A hierarchical memory management system for AI agents using the Model Context Protocol (MCP). Provides intelligent storage, retrieval, and lifecycle management of conversational context and knowledge across sessions.

## Features

- **Three-Tier Memory Architecture**: Short-term, long-term, and permanent memory collections
- **Intelligent Document Scoring**: Multi-factor importance calculation based on content, recency, and access patterns
- **Advanced Deduplication**: Semantic similarity detection with configurable thresholds and domain awareness
- **Lifecycle Management**: Automated TTL-based cleanup with importance-weighted aging
- **Query Performance Monitoring**: Real-time metrics and performance analytics
- **Chunk Relationship Tracking**: Maintains relationships between document fragments
- **FastAPI Integration**: RESTful API with comprehensive MCP tools
- **Comprehensive Testing**: Full test suite with pytest integration

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-memory-server

# Install dependencies
pip install -r requirements.txt

# Run configuration wizard
python scripts/config_wizard.py

# Start the server
python scripts/start_server.py
```

### Testing

```bash
# Run all tests
pytest -v

# Run specific test categories
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests only
```

## Configuration

### Interactive Setup
The configuration wizard provides guided setup for common use cases:

```bash
python scripts/config_wizard.py           # Interactive setup
python scripts/config_wizard.py template  # Template-based setup
```

### Manual Configuration
Configuration files are stored in `config/`:
- `config.example.json` - Complete configuration template
- `config/domains/` - Domain-specific configurations

## Architecture

### Memory Tiers
1. **Short-term Memory** - Recent interactions and temporary context
2. **Long-term Memory** - Important information for extended retention
3. **Permanent Memory** - Critical knowledge preserved indefinitely

### Importance Scoring
Documents are scored using multiple factors:
- **Semantic Analysis** - Content relevance and meaning
- **Recency Weighting** - Time-based importance decay
- **Access Patterns** - Frequency of retrieval
- **Domain Patterns** - Configurable keyword matching

### Deduplication System
- **Semantic Similarity Detection** - Prevents duplicate storage
- **Content Merging** - Combines similar documents intelligently
- **Domain-Aware Thresholds** - Different similarity requirements per content type
- **Performance Tracking** - Monitors deduplication effectiveness

## MCP Tools API

### Document Management
- `add_document` - Store content with automatic importance scoring
- `query_documents` - Semantic search with reranking
- `query_permanent_documents` - Search permanent content only

### System Monitoring
- `get_memory_stats` - Collection statistics and health metrics
- `get_lifecycle_stats` - TTL and aging system status
- `get_deduplication_stats` - Deduplication performance metrics
- `get_query_performance` - Query latency and effectiveness
- `get_real_time_metrics` - Live system performance data

### Advanced Features
- `deduplicate_memories` - Manual deduplication trigger
- `cleanup_expired_memories` - Force cleanup of expired content
- `get_chunk_relationships` - Analyze document relationships
- `get_system_health_assessment` - Comprehensive system health

## Project Structure

```
mcp-memory-server/
├── src/mcp_memory_server/      # Core server implementation
│   ├── analytics/              # Intelligence and analytics
│   ├── config/                 # Configuration management  
│   ├── deduplication/          # Duplicate detection system
│   ├── memory/                 # Hierarchical memory management
│   ├── server/                 # FastAPI server and handlers
│   └── tools/                  # MCP tools implementation
├── tests/                      # Comprehensive test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests  
│   └── performance/            # Performance tests
├── config/                     # Configuration files
├── scripts/                    # Management utilities
├── client-examples/            # Client integration examples
└── docs/                       # Documentation
```

## Testing Infrastructure

The project includes a comprehensive testing framework:

- **111 Tests Total**: Full coverage of functionality
- **Unit Tests**: Component-level testing with mocking
- **Integration Tests**: End-to-end functionality validation
- **Performance Tests**: Memory usage and query performance
- **Shared Test Database**: Efficient test execution with proper isolation

## Client Integration

Compatible with any MCP client. Example configurations provided for:
- **Claude Code CLI** - Development environment integration
- **Gemini CLI** - Alternative client support
- **Generic MCP Clients** - Standard protocol implementation

Ready-to-use configuration files available in `client-examples/`.

## Performance Characteristics

- **Memory Efficiency**: Intelligent lifecycle management prevents unbounded growth
- **Query Performance**: Fast semantic search with optional reranking
- **Scalable Architecture**: Modular design supports growth and customization
- **Monitoring**: Built-in performance tracking and health assessment

## Documentation

- `docs/architecture.md` - System design and components
- `docs/configuration.md` - Configuration guide and options
- `docs/domain-configuration.md` - Domain-specific setup
- `client-examples/README.md` - Client integration guide
- `REPORT.md` - Technical analysis and improvement opportunities

## Development

### Running Tests
```bash
# All tests
pytest -v

# Specific test file
pytest tests/integration/test_deduplication_flow.py -v

# With coverage
pytest --cov=src/mcp_memory_server tests/
```

### Configuration Validation
```bash
# Validate configuration
python scripts/validate_config.py

# Test server startup
python scripts/start_server.py --test
```

---

*This project explores intelligent memory management for AI systems through the Model Context Protocol, focusing on practical session persistence and knowledge retention.*