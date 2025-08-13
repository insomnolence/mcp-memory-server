# MCP Memory Server Documentation

Welcome to the comprehensive documentation for the Enhanced MCP Memory Server with hierarchical memory management and universal domain configuration.

## 📚 Documentation Index

### 🚀 Getting Started
- **[Main README](../README.md)** - Project overview, quick start, and installation
- **[Client Examples](../client-examples/README.md)** - AI client configuration guides
- **[Quick Start](../client-examples/QUICK_START.md)** - One-command setup instructions

### ⚙️ Configuration
- **[Configuration Guide](configuration.md)** - Complete configuration reference and manual setup
- **[Configuration Wizard](configuration-wizard-enhanced.md)** - Interactive wizard guide and features
- **[Domain Configuration](domain-configuration.md)** - Domain-specific pattern setup and examples
- **[Architecture Overview](architecture.md)** - System design and component interactions

### 📖 Additional Resources
These files contain project development context and future plans:
- **[RESUME_SESSION.md](../RESUME_SESSION.md)** - Development session summaries and status
- **[EMBEDDING_PROVIDERS_ENHANCEMENT.md](../EMBEDDING_PROVIDERS_ENHANCEMENT.md)** - Planned multi-provider embedding support

#### API Reference
The server exposes these MCP tools:
- `add_document` - Store content with automatic importance scoring
- `query_documents` - Multi-collection semantic search with reranking
- `query_permanent_documents` - Search only permanent/critical content
- `get_memory_stats` - System health and collection statistics
- `get_lifecycle_stats` - TTL and aging system metrics
- `get_permanence_stats` - Permanent content statistics

## 🎯 Documentation Quick Reference

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
2. **[Proposal.md](../Proposal.md)** - Technical design and implementation phases
3. **[CLAUDE.md](../CLAUDE.md)** - Development context and patterns

### For Domain Experts
1. **[Universal Domains Guide](UNIVERSAL_DOMAINS_GUIDE.md)** - Create domain-specific configurations
2. **[Configuration Guide](configuration.md)** - Advanced pattern configuration
3. **Domain Examples**: `config/domains/*.json`

## 🔍 Finding Information

| I want to... | Read this |
|---------------|-----------|
| **Set up the server quickly** | [Client Examples Quick Start](../client-examples/QUICK_START.md) |
| **Configure for my domain** | [Configuration Guide](configuration.md) |
| **Understand the architecture** | [Architecture Overview](architecture.md) |
| **Connect my AI client** | [Client Examples](../client-examples/README.md) |
| **Troubleshoot issues** | [Configuration Guide](configuration.md#troubleshooting) |
| **Migrate from old version** | [Configuration Guide](configuration.md#migration-guide) |
| **Create custom domain** | [Domain Configuration](domain-configuration.md) |
| **Deploy in production** | [Configuration Guide](configuration.md#environment-configuration) |

## 🎓 Learning Path

### Beginner
1. **Project Overview** → [Main README](../README.md)
2. **Quick Setup** → [Quick Start](../client-examples/QUICK_START.md)  
3. **Basic Usage** → Try the MCP tools with your AI client

### Intermediate  
1. **Domain Configuration** → [Configuration Guide](configuration.md)
2. **Custom Patterns** → [Domain Configuration](domain-configuration.md)
3. **Performance Tuning** → [Configuration Guide](configuration.md#performance-optimization)

### Advanced
1. **System Architecture** → [Architecture Overview](architecture.md)
2. **Production Deployment** → [Configuration Guide](configuration.md#environment-configuration)
3. **Custom Development** → [CLAUDE.md](../CLAUDE.md) + source code

## 🌟 Key Features Covered

### Universal Domain System
- Configure for **any domain** (business, research, creative writing, cooking, etc.)
- **No code changes required** - just configure keywords
- **Automatic importance scoring** based on domain patterns

### Hierarchical Memory Management
- **5-tier memory system** (short-term, long-term, permanent, consolidated, legacy)
- **TTL-based lifecycle** with automatic cleanup
- **Importance-weighted aging** and scoring

### Professional Architecture
- **Modern Python packaging** with src/ layout
- **Domain/environment separation** for flexible deployment
- **Comprehensive testing** and validation framework
- **Client configuration examples** for multiple AI systems

### Production Ready
- **Performance optimized** with caching and efficient data structures
- **Scalable design** supporting multiple domains and environments
- **Monitoring and statistics** for system health
- **Backup and migration** support

## 💬 Community and Support

- **Issues**: Report bugs and request features on the project repository
- **Discussions**: Share domain configurations and use cases
- **Contributions**: Improve documentation, add domain examples, enhance features

## 📝 Documentation Standards

This documentation follows these principles:
- **Clear examples** with copy-paste commands
- **Progressive complexity** from basic to advanced
- **Real-world scenarios** and use cases
- **Troubleshooting guides** for common issues
- **Visual diagrams** where helpful

## 🔄 Document Status

| Document | Status | Last Updated | Coverage |
|----------|--------|-------------|----------|
| **Main README** | ✅ Current | Latest | Complete project overview |
| **Configuration Guide** | ✅ Current | Latest | Complete system configuration |
| **Architecture Overview** | ✅ Current | Latest | System design and components |
| **Client Examples** | ✅ Current | Latest | AI client configurations |
| **Domain Configuration** | ✅ Current | Latest | Complete domain setup guide |
| **Legacy Documents** | 📚 Preserved | Historical | Development context |

---

**Need help?** Start with the [Configuration Guide](configuration.md) for comprehensive setup instructions, or check the [Quick Start](../client-examples/QUICK_START.md) for immediate setup commands.