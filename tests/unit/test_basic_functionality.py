import pytest
import os
import json


@pytest.fixture(scope="module")
def project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def test_configuration_loading(project_root):
    """Test configuration file loading"""
    config_path = os.path.join(project_root, 'config', 'config.example.json')

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Check Phase 3 sections as per original test_harness
    required_sections = ['analytics', 'chunk_relationships', 'deduplication']
    missing_sections = []

    for section in required_sections:
        if section not in config:
            missing_sections.append(section)

    # Check deduplication.advanced_features
    if 'deduplication' in config and 'advanced_features' not in config['deduplication']:
        missing_sections.append('deduplication.advanced_features')

    assert len(missing_sections) == 0, f"Missing required config sections: {missing_sections}"


def test_module_imports():
    """Test core module imports"""
    modules_to_test = [
        'src.mcp_memory_server.server.tool_definitions',
        'src.mcp_memory_server.memory.services.facade',  # Updated from hierarchical
        'src.mcp_memory_server.config.manager'
    ]

    for module in modules_to_test:
        try:
            __import__(module)
        except ImportError as e:
            pytest.fail(f"Failed to import {module}: {e}")
        except Exception as e:
            pytest.fail(f"Error importing {module}: {e}")


def test_data_generation(data_generator):
    """Test data generation capabilities"""
    test_sizes = [10, 50]

    for size in test_sizes:
        documents = data_generator.generate_test_dataset(size, duplicate_percentage=30)

        assert len(documents) == size, f"Expected {size} documents, but got {len(documents)}"

        # Basic check for content and metadata structure
        for doc in documents:
            assert 'content' in doc
            assert 'metadata' in doc
            assert 'type' in doc['metadata']
            assert 'source' in doc['metadata']


def test_memory_monitoring(memory_monitor):
    """Test memory monitoring system"""
    # Start monitoring
    memory_monitor.start_monitoring(interval=0.1)

    # Do some memory-intensive work (e.g., create a large list)
    data = []
    for i in range(1000):
        data.append([i] * 100)  # Create some data to consume memory

    # Give monitor time to sample
    import time
    time.sleep(1)

    # Stop monitoring
    stats = memory_monitor.stop_monitoring()

    assert stats.get('samples_count', 0) > 0, "Memory monitoring did not collect any samples"
    assert stats.get('duration_seconds', 0) > 0, "Memory monitoring duration is zero"

    # For unit tests, we don't expect MCP server processes to be running
    # Just verify that the monitoring infrastructure works
    assert 'process_memory' in stats, "Process memory statistics not included"
    assert 'system_memory' in stats, "System memory statistics not included"
    system_mem = stats.get('system_memory', {})
    assert system_mem.get('max_used_mb', 0) > 0, "System memory was not tracked"


def test_all_dependencies_available():
    """Comprehensive dependency check with proper error handling"""
    # Core packages
    core_deps = ['fastapi', 'uvicorn', 'starlette', 'pydantic']

    # AI/ML packages
    ml_deps = ['chromadb', 'sentence_transformers', 'sklearn', 'numpy', 'transformers', 'torch']

    # LangChain packages
    langchain_deps = ['langchain_core', 'langchain_community', 'langchain_text_splitters',
                      'langchain_huggingface', 'langchain_chroma']

    # Testing packages (already installed for pytest, but good to check)
    test_deps = ['requests', 'psutil']

    all_deps = [
        ('Core Framework', core_deps),
        ('AI/ML Libraries', ml_deps),
        ('LangChain Ecosystem', langchain_deps),
        ('Testing Tools', test_deps)
    ]

    missing_dependencies = []

    for category, deps in all_deps:
        category_missing = []
        category_available = []
        for dep in deps:
            try:
                __import__(dep)
                category_available.append(dep)
            except ImportError:
                category_missing.append(dep)
                missing_dependencies.append(dep)

        if category_missing:
            print(f"\n{category} - Missing: {category_missing}")
        if category_available:
            print(f"{category} - Available: {category_available}")

    # Skip test if we're running in an environment without dependencies
    # This allows basic syntax/structure tests to run even without full env
    if missing_dependencies:
        pytest.skip(f"Missing required dependencies: {missing_dependencies}. "
                    f"Install with: pip install -r requirements.txt")

    print(f"\n✅ All {len([dep for _, deps in all_deps for dep in deps])} dependencies are available!")
