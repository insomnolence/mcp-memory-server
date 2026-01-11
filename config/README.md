# Configuration Directory

This directory contains configuration files for the MCP Memory Server.

## Structure

```
config/
├── README.md                           # This file
├── config.example.json                 # Main configuration template
├── example.*.json                      # Domain-specific example configs
└── domains/                            # Your project-specific configs (gitignored)
    └── {your-project}.json
```

## Example Files

The `example.*.json` files are templates showing different domain configurations:

- `example.business-development.json` - Business/sales focused memory patterns
- `example.cooking.json` - Culinary/recipe memory patterns  
- `example.creative-writing.json` - Creative writing memory patterns
- `example.research.json` - Research/academic memory patterns

## Creating Your Own Domain Config

1. Copy an example file that matches your use case:
   ```bash
   cp config/example.research.json config/domains/my-project.json
   ```

2. Edit the config to match your project's needs

3. Start the server with your domain:
   ```bash
   python -m mcp_memory_server --domain my-project
   ```

## Configuration Loading

The server loads configuration in this order:

1. If `--config` flag is provided, use that specific file
2. If `--domain` flag is provided, load from `config/domains/{domain}.json`
3. Otherwise, fall back to `config.json` in the project root

Domain configs are merged with the base `config.json` if it exists, allowing you to override only specific settings.

## Note

Files in `config/domains/` are gitignored to keep project-specific configurations local. Only the example files and this README are tracked in version control.
