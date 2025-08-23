# MCP Memory Server - Architecture Overview

## System Architecture

The MCP Memory Server implements a hierarchical memory system with domain-specific configuration, designed for intelligent content management and retrieval.

```
┌─────────────────────────────────────────────────────────┐
│                  MCP Memory Server                      │
├─────────────────────────────────────────────────────────┤
│                   FastAPI Server                       │
│              (JSON-RPC Protocol)                       │
├─────────────────────────────────────────────────────────┤
│                    Tool Registry                       │
│  ┌─────────────┬────────────┬─────────────────────────┐  │
│  │   Document  │   Query    │     Lifecycle/Stats     │  │
│  │    Tools    │   Tools    │        Tools            │  │
│  └─────────────┴────────────┴─────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│              Hierarchical Memory System                │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                Memory Tiers                         │ │
│  │  ┌──────────┬──────────┬──────────────────────────┐ │ │
│  │  │Short-term│Long-term │      Permanent           │ │ │
│  │  │   (TTL)  │(Important)│     (Critical)           │ │ │
│  │  └──────────┴──────────┴──────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│             Importance Scoring Engine                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Semantic Analysis + Recency + Frequency + Domain  │ │
│  └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│              Deduplication System                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Similarity Detection + Content Merging + Analytics│ │
│  └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                ChromaDB Storage                        │
│  ┌─────────────────────────────────────────────────────┐ │
│  │       Vector Embeddings + Metadata + Indices       │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. FastAPI Server Layer
- **JSON-RPC Protocol**: MCP-compliant communication
- **Tool Registry**: Dynamic MCP tool registration and routing  
- **Request Handling**: Async request processing with proper error handling
- **Health Monitoring**: Built-in health checks and status reporting

### 2. Hierarchical Memory System
Central component managing three memory tiers:

#### Short-term Memory
- **Purpose**: Recent interactions and temporary context
- **Storage**: ChromaDB collection with TTL metadata
- **Lifecycle**: Automatic expiration based on importance and age
- **Capacity**: Configurable (default: ~100 documents)

#### Long-term Memory  
- **Purpose**: Important information for extended retention
- **Criteria**: Documents with importance score ≥ 0.7
- **Storage**: Persistent ChromaDB collection
- **Lifecycle**: TTL-based with importance-weighted aging

#### Permanent Memory
- **Purpose**: Critical knowledge preserved indefinitely  
- **Criteria**: Documents with importance score ≥ 0.95 or explicit permanence flags
- **Storage**: Persistent ChromaDB collection with permanence metadata
- **Lifecycle**: No automatic expiration

### 3. Importance Scoring Engine
Multi-factor scoring algorithm:

```python
importance_score = (
    semantic_weight * semantic_score +      # 40% - Content analysis
    recency_weight * recency_score +        # 30% - Time-based decay  
    frequency_weight * frequency_score +    # 20% - Access patterns
    domain_weight * domain_score            # 10% - Domain keywords
)
```

#### Semantic Analysis
- **HuggingFace Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Content Length**: Normalized scoring for document length
- **Keyword Matching**: Domain-specific pattern recognition

#### Recency Weighting
- **Exponential Decay**: Recent documents score higher
- **Configurable Decay**: Domain-specific decay constants
- **Access-based Refresh**: Score boost on retrieval

#### Frequency Analysis
- **Access Count**: Track document retrieval frequency
- **Usage Patterns**: Identify frequently referenced content
- **Temporal Analysis**: Recent access patterns weighted higher

### 4. Deduplication System
Advanced duplicate detection and content merging:

#### Similarity Detection
- **Embedding Comparison**: Cosine similarity on document vectors
- **Configurable Thresholds**: Domain-aware similarity requirements
- **Batch Processing**: Efficient processing of document collections

#### Content Merging
- **Importance Preservation**: Keep higher-importance versions
- **Metadata Combination**: Merge access counts and metadata
- **Relationship Tracking**: Maintain document relationships

#### Domain Awareness
- **Content Type Detection**: Different thresholds for code, text, data
- **Keyword Classification**: Automatic content categorization
- **Adaptive Thresholds**: Dynamic similarity requirements

### 5. Lifecycle Management
Automated document lifecycle with TTL system:

#### TTL Calculation
```python
ttl = base_ttl + jitter + importance_modifier + access_modifier
```

#### Tier Assignment
- **High Frequency**: Documents accessed multiple times recently
- **Medium Frequency**: Moderately accessed content
- **Low Frequency**: Rarely accessed content  
- **Static**: Content marked for long-term retention

#### Background Maintenance
- **Cleanup Processes**: Automated expired document removal
- **Health Monitoring**: System health assessment and reporting
- **Performance Tracking**: Lifecycle effectiveness metrics

### 6. Storage Layer (ChromaDB)
Vector database with metadata support:

#### Collections
- `short_term_memory`: Recent interactions
- `long_term_memory`: Important persistent content
- `permanent_memory`: Critical preserved knowledge

#### Indexing
- **Vector Indices**: Efficient similarity search
- **Metadata Indices**: Fast filtering and retrieval
- **Composite Queries**: Complex search capabilities

## Data Flow

### Document Ingestion
1. **Content Analysis**: Extract text and metadata
2. **Importance Scoring**: Calculate multi-factor score
3. **Deduplication Check**: Detect similar existing content
4. **Tier Assignment**: Route to appropriate memory tier
5. **Storage**: Store in ChromaDB with metadata
6. **Relationship Tracking**: Update document relationships

### Document Retrieval
1. **Query Processing**: Parse search parameters
2. **Multi-tier Search**: Search across relevant collections
3. **Similarity Ranking**: Vector-based relevance scoring
4. **Reranking**: Apply cross-encoder for precision
5. **Access Tracking**: Update access counts and patterns
6. **Response Assembly**: Format results for MCP protocol

### Maintenance Operations
1. **TTL Processing**: Identify expired documents
2. **Cleanup Execution**: Remove expired content
3. **Deduplication**: Periodic similarity analysis
4. **Health Assessment**: System performance evaluation
5. **Statistics Update**: Maintain system metrics

## Configuration Architecture

### Hierarchical Configuration
- **Base Configuration**: Core system settings
- **Domain Overrides**: Domain-specific customizations
- **Environment Variables**: Runtime configuration options

### Domain Patterns
```json
{
  "domain_patterns": {
    "patterns": {
      "technical_content": {
        "keywords": ["function", "error", "implementation"],
        "bonus": 0.3,
        "match_mode": "any"
      }
    }
  }
}
```

## Performance Characteristics

### Scalability
- **Async Processing**: Non-blocking operation handling
- **Batch Operations**: Efficient bulk processing
- **Memory Management**: Controlled resource usage
- **Query Optimization**: Indexed searches and caching

### Reliability
- **Error Handling**: Comprehensive exception management
- **Health Monitoring**: Continuous system health assessment  
- **Graceful Degradation**: Fallback mechanisms for component failures
- **Data Integrity**: Consistent state management

### Monitoring
- **Performance Metrics**: Query latency and throughput
- **Resource Usage**: Memory and storage monitoring
- **System Health**: Component status and availability
- **Analytics**: Usage patterns and effectiveness metrics

## Extension Points

### Custom Tools
- **Tool Registration**: Dynamic MCP tool addition
- **Parameter Validation**: Automatic request validation
- **Response Formatting**: Consistent MCP response structure

### Custom Scorers
- **Pluggable Scoring**: Custom importance algorithms
- **Domain-specific Logic**: Specialized scoring functions
- **Composite Scoring**: Multiple scoring strategy combination

### Storage Backends
- **Database Abstraction**: Pluggable storage implementations
- **Migration Support**: Data migration between storage systems
- **Backup Integration**: Automated backup and restoration

This architecture provides a robust foundation for intelligent memory management while maintaining flexibility for domain-specific customization and future enhancements.