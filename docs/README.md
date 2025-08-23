# MCP Memory Server Documentation

Comprehensive documentation for the MCP Memory Server with hierarchical memory management and domain configuration.

## Documentation Index

### Getting Started
- **[Main README](../README.md)** - Project overview, quick start, and installation
- **[Client Examples](../client-examples/README.md)** - AI client configuration guides
- **[Quick Start](../client-examples/QUICK_START.md)** - Setup instructions

### Configuration
- **[Configuration Guide](configuration.md)** - Complete configuration reference and manual setup
- **[Configuration Wizard](configuration-wizard-enhanced.md)** - Interactive wizard guide and features
- **[Domain Configuration](domain-configuration.md)** - Domain-specific pattern setup and examples
- **[Architecture Overview](architecture.md)** - System design and component interactions

### API Reference
The server exposes these MCP tools:
- `add_document` - Store content with automatic importance scoring
- `query_documents` - Multi-collection semantic search with reranking
- `query_permanent_documents` - Search only permanent/critical content
- `get_memory_stats` - System health and collection statistics
- `get_lifecycle_stats` - TTL and aging system metrics
- `get_deduplication_stats` - Deduplication performance metrics
- `cleanup_expired_memories` - Manual cleanup of expired content
- `deduplicate_memories` - Manual deduplication trigger

## Documentation Quick Reference

### For New Users
1. **[Main README](../README.md)** - Understand what this project does
2. **[Client Examples](../client-examples/QUICK_START.md)** - Get connected quickly
3. **[Configuration Guide](configuration.md)** - Customize for your domain

### For System Administrators
1. **[Configuration Guide](configuration.md)** - Complete system configuration
2. **[Architecture Overview](architecture.md)** - Understand the system design
3. **[Client Examples](../client-examples/README.md)** - Deploy for multiple users

### For Developers
1. **[Architecture Overview](architecture.md)** - System components and interactions
2. **[REPORT.md](../REPORT.md)** - Technical analysis and improvement opportunities
3. Source code in `src/mcp_memory_server/`

### For Domain Experts
1. **[Domain Configuration](domain-configuration.md)** - Create domain-specific configurations
2. **[Configuration Guide](configuration.md)** - Advanced pattern configuration
3. Domain examples in `config/domains/*.json`

## Finding Information

| I want to... | Read this |
|---------------|-----------|
| **Set up the server quickly** | [Client Examples Quick Start](../client-examples/QUICK_START.md) |
| **Configure for my domain** | [Configuration Guide](configuration.md) |
| **Understand the architecture** | [Architecture Overview](architecture.md) |
| **Connect my AI client** | [Client Examples](../client-examples/README.md) |
| **Troubleshoot issues** | [Configuration Guide](configuration.md) |
| **Create custom domain** | [Domain Configuration](domain-configuration.md) |
| **Run tests** | [Main README](../README.md#testing) |

## Learning Path

### Beginner
1. **Project Overview** → [Main README](../README.md)
2. **Quick Setup** → [Quick Start](../client-examples/QUICK_START.md)  
3. **Basic Usage** → Try the MCP tools with your AI client

### Intermediate  
1. **Domain Configuration** → [Configuration Guide](configuration.md)
2. **Custom Patterns** → [Domain Configuration](domain-configuration.md)
3. **Performance Monitoring** → Use built-in analytics tools

### Advanced
1. **System Architecture** → [Architecture Overview](architecture.md)
2. **Production Deployment** → [Configuration Guide](configuration.md)
3. **Custom Development** → Study source code structure

## Key Features Covered

### Universal Domain System
- Configure for any domain (business, research, creative writing, technical, etc.)
- No code changes required - just configure keywords
- Automatic importance scoring based on domain patterns

### Hierarchical Memory Management
- Three-tier memory system (short-term, long-term, permanent)
- TTL-based lifecycle with automatic cleanup
- Importance-weighted aging and scoring

### Advanced Features
- Semantic deduplication with domain awareness
- Query performance monitoring and analytics
- Chunk relationship tracking
- Background maintenance processes

### Professional Architecture
- Modern Python packaging with src/ layout
- Domain/environment separation for flexible deployment
- Comprehensive testing framework (111 tests)
- Client configuration examples for multiple AI systems

## Documentation Standards

This documentation follows these principles:
- Clear examples with practical commands
- Progressive complexity from basic to advanced
- Real-world scenarios and use cases
- Troubleshooting guides for common issues

## Document Status

| Document | Status | Coverage |
|----------|--------|----------|
| **Main README** | Current | Complete project overview |
| **Configuration Guide** | Current | Complete system configuration |
| **Architecture Overview** | Current | System design and components |
| **Client Examples** | Current | AI client configurations |
| **Domain Configuration** | Current | Complete domain setup guide |

---

**Need help?** Start with the [Configuration Guide](configuration.md) for comprehensive setup instructions, or check the [Quick Start](../client-examples/QUICK_START.md) for immediate setup commands.