import pytest
import random
import time
import json


@pytest.fixture(scope="session")
def data_generator():
    return DataGenerator()


class DataGenerator:
    """Generate realistic test data for various scenarios"""

    def __init__(self):
        self.code_keywords = ['function', 'class', 'import', 'return', 'def', 'if', 'for', 'while', 'try', 'except']
        self.text_keywords = ['the', 'and', 'or', 'but', 'however', 'therefore', 'because', 'since', 'when', 'where']
        self.data_keywords = ['data', 'json', 'csv', 'table', 'row', 'column', 'field', 'value', 'record', 'database']
        self.doc_keywords = ['guide', 'documentation', 'tutorial', 'example', 'howto', 'readme', 'manual', 'reference']

    def generate_code_content(self, base_content="", similarity_level=0.8):
        """Generate code-like content with controlled similarity"""
        if not base_content:
            # Create base code content
            functions = ['process_data', 'calculate_result', 'validate_input', 'format_output', 'handle_error']
            variables = ['data', 'result', 'config', 'response', 'params']

            content = f"""
def {random.choice(functions)}({', '.join(random.sample(variables, 2))}):
    '''Process {random.choice(['user input', 'data records', 'configuration', 'response data'])}'''

    {random.choice(variables)} = {random.choice(['{{}}', '[]', 'None', '""'])}

    if {random.choice(variables)}:
        for item in {random.choice(variables)}:
            {random.choice(['print(item)', 'process(item)', 'validate(item)', 'store(item)'])}

    return {random.choice(variables)}

# {random.choice(['Configuration', 'Constants', 'Settings'])}
{random.choice(['CONFIG', 'SETTINGS', 'PARAMS'])} = {{
    '{random.choice(['threshold', 'limit', 'timeout', 'retry'])}': {random.randint(1, 100)},
    '{random.choice(['enabled', 'debug', 'verbose', 'strict'])}': {random.choice(['True', 'False'])},
    '{random.choice(['path', 'url', 'endpoint', 'target'])}': \
"{random.choice(['localhost', 'example.com', '/api/v1', '/data'])}"
}}
"""
        else:
            # Modify existing content based on similarity level
            lines = base_content.strip().split('\n')
            num_changes = int(len(lines) * (1 - similarity_level))

            for _ in range(num_changes):
                if lines:
                    line_idx = random.randint(0, len(lines) - 1)
                    line = lines[line_idx]

                    # Make small modifications
                    if 'def ' in line:
                        line = line.replace('def ', 'def new_')
                    elif '=' in line and not line.strip().startswith('#'):
                        parts = line.split('=')
                        if len(parts) == 2:
                            line = f"{parts[0]}= {random.choice(['modified_value', 'updated_data', 'new_result'])}"
                    elif random.random() < 0.3:
                        line = f"    # Modified: {line.strip()}"

                    lines[line_idx] = line

            content = '\n'.join(lines)

        return content

    def generate_text_content(self, base_content="", similarity_level=0.8):
        """Generate text content with controlled similarity"""
        topics = ['machine learning', 'data analysis', 'software development', 'project management', 'system design']

        if not base_content:
            topic = random.choice(topics)
            content = f"""
# Understanding {topic.title()}

{topic.title()} is a crucial aspect of modern technology that involves \
{random.choice(['analyzing', 'processing', 'managing', 'optimizing'])} \
{random.choice(['data', 'information', 'systems', 'processes'])}.

## Key Concepts

The fundamental principles include:
- {random.choice(['Efficiency', 'Scalability', 'Reliability', 'Maintainability'])}
- {random.choice(['Performance', 'Security', 'Usability', 'Flexibility'])}
- {random.choice(['Integration', 'Testing', 'Documentation', 'Monitoring'])}

## Best Practices

When working with {topic}, it's important to:
1. {random.choice(['Plan carefully', 'Test thoroughly', 'Document everything', 'Monitor continuously'])}
2. {random.choice(['Follow standards', 'Use best practices', 'Consider scalability', 'Ensure security'])}
3. {random.choice(['Optimize performance', 'Maintain quality', 'Handle errors', 'Provide feedback'])}

## Conclusion

{topic.title()} remains an essential skill for \
{random.choice(['developers', 'analysts', 'engineers', 'professionals'])} \
working in {random.choice(['technology', 'business', 'research', 'industry'])}
"""
        else:
            # Modify existing content
            sentences = base_content.replace('\n', ' ').split('.')
            num_changes = int(len(sentences) * (1 - similarity_level))

            for _ in range(num_changes):
                if sentences:
                    idx = random.randint(0, len(sentences) - 1)
                    sentence = sentences[idx].strip()
                    if sentence:
                        # Make modifications
                        words = sentence.split()
                        if len(words) > 3:
                            # Replace some words
                            replace_idx = random.randint(1, len(words) - 2)
                            words[replace_idx] = random.choice(
                                ['improved', 'enhanced', 'optimized', 'advanced', 'modified'])
                        sentences[idx] = ' '.join(words)

            content = '. '.join(sentences)

        return content

    def generate_data_content(self, base_content="", similarity_level=0.8):
        """Generate data-like content"""
        if not base_content:
            fields = ['id', 'name', 'value', 'timestamp', 'status', 'category', 'priority', 'description']
            content = {
                random.choice(fields): random.choice([
                    random.randint(1, 1000),
                    f"item_{random.randint(1, 100)}",
                    random.uniform(0, 100),
                    time.time(),
                    random.choice(['active', 'inactive', 'pending']),
                    random.choice(['high', 'medium', 'low']),
                    f"Description for {random.choice(['data', 'record', 'item', 'entry'])}"
                ]) for _ in range(random.randint(3, 8))
            }
            return json.dumps(content, indent=2)
        else:
            # Modify existing JSON data
            try:
                data = json.loads(base_content)
                if isinstance(data, dict):
                    num_changes = max(1, int(len(data) * (1 - similarity_level)))
                    keys = list(data.keys())
                    for _ in range(num_changes):
                        if keys:
                            key = random.choice(keys)
                            if isinstance(data[key], (int, float)):
                                data[key] = data[key] * random.uniform(0.8, 1.2)
                            elif isinstance(data[key], str):
                                data[key] = f"modified_{data[key]}"
                return json.dumps(data, indent=2)
            except BaseException:
                return base_content

    def generate_documentation_content(self, base_content="", similarity_level=0.8):
        """Generate documentation-like content"""
        if not base_content:
            components = ['API', 'Database', 'Service', 'Module', 'Component']
            component = random.choice(components)

            content = f"""
# {component} Documentation

## Overview
The {component.lower()} provides functionality for \
{random.choice(['data processing', 'user management', 'system integration', 'performance monitoring'])}.

## Installation
```bash
pip install {component.lower()}-package
```

## Usage
```python
from {component.lower()} import {component}

# Initialize
{component.lower()} = {component}()

# Basic usage
result = {component.lower()}.{random.choice(['process', 'execute', 'run', 'handle'])}(data)
```

## Configuration
- `timeout`: {random.randint(5, 60)} seconds
- `retry_count`: {random.randint(1, 5)}
- `debug_mode`: {random.choice(['True', 'False'])}

## Examples
See the examples directory for complete usage examples.
"""
        else:
            # Modify documentation
            lines = base_content.split('\n')
            num_changes = int(len(lines) * (1 - similarity_level))

            for _ in range(num_changes):
                if lines:
                    idx = random.randint(0, len(lines) - 1)
                    line = lines[idx]
                    if '##' in line:
                        lines[idx] = line.replace('##', '### Updated')
                    elif 'pip install' in line:
                        lines[idx] = line.replace('pip install', 'pip install --upgrade')
                    elif random.random() < 0.2:
                        lines[idx] = f"{line} (updated)"

            content = '\n'.join(lines)

        return content

    def generate_test_dataset(self, total_documents=100, duplicate_percentage=30):
        """Generate a complete test dataset with known duplicate patterns"""
        documents = []

        # Calculate how many of each type (ensure we get the exact total)
        per_type = total_documents // 4
        remainder = total_documents % 4
        duplicates_per_type = int(per_type * duplicate_percentage / 100)

        content_generators = [
            ('code', self.generate_code_content),
            ('text', self.generate_text_content),
            ('data', self.generate_data_content),
            ('documentation', self.generate_documentation_content)
        ]

        for idx, (content_type, generator) in enumerate(content_generators):
            # Calculate documents for this type (distribute remainder across first types)
            docs_for_type = per_type + (1 if idx < remainder else 0)

            # Generate base documents
            base_docs = []
            for i in range(docs_for_type - duplicates_per_type):
                content = generator()
                doc = {
                    'content': content,
                    'metadata': {
                        'type': content_type,
                        'source': f'generated_{content_type}_{i}',
                        'timestamp': time.time() - random.randint(0, 86400 * 30),  # Last 30 days
                        'is_duplicate': False,
                        'importance_score': random.uniform(0.3, 0.9)
                    }
                }
                base_docs.append(doc)
                documents.append(doc)

            # Generate duplicates based on existing documents
            for i in range(duplicates_per_type):
                if base_docs:
                    base_doc = random.choice(base_docs)
                    similarity_level = random.uniform(0.85, 0.98)  # High similarity

                    duplicate_content = generator(base_doc['content'], similarity_level)
                    duplicate_doc = {
                        'content': duplicate_content,
                        'metadata': {
                            'type': content_type,
                            'source': f'duplicate_{content_type}_{i}',
                            'timestamp': time.time() - random.randint(0, 86400 * 7),  # Last 7 days
                            'is_duplicate': True,
                            'duplicate_of': base_doc['metadata']['source'],
                            'similarity_level': similarity_level,
                            'importance_score': random.uniform(0.2, 0.7)
                        }
                    }
                    documents.append(duplicate_doc)

        return documents
