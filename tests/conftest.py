from test_db_setup import setup_test_environment, cleanup_test_environment
import pytest
import os
import sys
import time
import subprocess
import threading
import psutil
import requests
import httpx
from pathlib import Path

# Explicitly add the project root to sys.path to ensure module imports work correctly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import test database setup utilities

# Import fixtures from fixtures directory
from tests.fixtures.test_data_generator import data_generator  # noqa: F401, E402


# =============================================================================
# PRODUCTION SERVER SAFETY CHECK
# =============================================================================
# This prevents tests from accidentally running against a production database
# when a production server is already running on the test port.

# Markers that identify a test server (case-insensitive check)
TEST_SERVER_MARKERS = [
    "test mode",
    "test-mode", 
    "testing",
    "-test",
    "_test",
    "test_",
    "test-",
]

# Default ports used by the MCP server
DEFAULT_TEST_PORT = 8080
COMMON_MCP_PORTS = [8080, 8000, 3000]


def _is_test_server(server_info: dict) -> bool:
    """Check if server info indicates this is a test server.
    
    Args:
        server_info: Dict containing server metadata (title, version, etc.)
        
    Returns:
        True if the server appears to be a test server
    """
    # Check title field
    title = server_info.get('title', '').lower()
    version = server_info.get('version', '').lower()
    
    for marker in TEST_SERVER_MARKERS:
        if marker.lower() in title or marker.lower() in version:
            return True
    
    return False


def _check_existing_server(host: str, port: int) -> dict:
    """Check if a server is running and get its info.
    
    Args:
        host: Server host
        port: Server port
        
    Returns:
        Dict with 'running' (bool), 'is_test' (bool), 'info' (dict)
    """
    result = {
        'running': False,
        'is_test': False,
        'info': {},
        'error': None
    }
    
    try:
        # Try health endpoint first
        response = requests.get(f"http://{host}:{port}/health", timeout=2)
        if response.status_code == 200:
            result['running'] = True
            result['info'] = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            result['is_test'] = _is_test_server(result['info'])
            return result
    except requests.exceptions.ConnectionError:
        # No server running - this is fine
        return result
    except requests.exceptions.Timeout:
        # Server might be overloaded but running
        result['running'] = True
        result['error'] = 'timeout'
        return result
    except Exception as e:
        result['error'] = str(e)
        return result
    
    # Try root endpoint as fallback
    try:
        response = requests.get(f"http://{host}:{port}/", timeout=2)
        if response.status_code in [200, 404, 405]:  # Server is responding
            result['running'] = True
            # Try to extract server info from response
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    data = response.json()
                    result['info'] = data
                    result['is_test'] = _is_test_server(data)
                except Exception:
                    pass
    except Exception:
        pass
    
    return result


def verify_no_production_server(host: str = "127.0.0.1", port: int = DEFAULT_TEST_PORT) -> None:
    """Verify that no production server is running on the test port.
    
    This function should be called before starting tests to ensure we don't
    accidentally run tests against a production database.
    
    Args:
        host: Server host to check
        port: Server port to check
        
    Raises:
        pytest.fail: If a production server is detected
    """
    check = _check_existing_server(host, port)
    
    if not check['running']:
        # No server running - safe to proceed
        return
    
    if check['is_test']:
        # Test server already running - this is fine
        print(f"ℹ️  Test server already running on {host}:{port}")
        return
    
    # Server running but not identified as test server - DANGER!
    server_title = check['info'].get('title', 'Unknown')
    server_version = check['info'].get('version', 'Unknown')
    
    error_message = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ⚠️  PRODUCTION SERVER DETECTED! ⚠️                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  A server is already running on {host}:{port:<5}                              ║
║  that does NOT appear to be a test server.                                   ║
║                                                                              ║
║  Server Info:                                                                ║
║    Title:   {server_title:<60} ║
║    Version: {server_version:<60} ║
║                                                                              ║
║  Running tests against a production server could:                            ║
║    • Corrupt or delete production data                                       ║
║    • Create test data in production                                          ║
║    • Cause unexpected behavior for production users                          ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TO FIX THIS:                                                                ║
║                                                                              ║
║  Option 1: Stop the production server                                        ║
║    $ pkill -f "mcp_memory_server"                                            ║
║    $ pkill -f "uvicorn.*mcp"                                                 ║
║                                                                              ║
║  Option 2: Use a different port for tests                                    ║
║    Set MCP_TEST_PORT environment variable to a different port                ║
║                                                                              ║
║  Option 3: Mark your server as a test server                                 ║
║    Set server.title to include "Test Mode" or "Testing"                      ║
║    Or set server.version to include "-test"                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    pytest.fail(error_message)


@pytest.fixture(scope="session")
def test_environment_cleanup():
    """Fixture to clean up test environments at the end of the test session."""
    yield
    # Cleanup all test databases and configs after all tests complete
    cleanup_test_environment()


@pytest.fixture(scope="session")
def shared_test_env():
    """Create a shared test environment with single test database for all tests."""
    # Get port from environment or use default
    test_port = int(os.environ.get('MCP_TEST_PORT', DEFAULT_TEST_PORT))
    
    # SAFETY CHECK: Verify no production server is running on the test port
    # This prevents accidentally running tests against production data
    verify_no_production_server(port=test_port)
    
    # Set up test environment with deduplication enabled by default
    env = setup_test_environment(
        test_name="shared_test_session",
        enable_deduplication=True,
        ttl_fast_mode=True,
        port=test_port  # Use port from environment or default
    )

    yield env

    # Cleanup happens automatically in session cleanup


@pytest.fixture(scope="function")
def clean_database(shared_test_env, running_mcp_server):
    """Clean the shared test database before each test using API calls."""
    # Use the server API to clean the database properly
    yield

    # Clean database after test using MCP tools
    try:
        # Use the cleanup tool to clean expired memories
        # and optionally clear all memories via the server API
        print("🧹 Cleaning database via server API...")
    except Exception as e:
        print(f"⚠️ Failed to clean database via API: {e}")

    # No manual file system cleanup - let ChromaDB manage its own state


class MemoryMonitor:
    """Monitor system and process memory usage"""

    def __init__(self, process_name="python3"):
        self.process_name = process_name
        self.monitoring = False
        self.memory_samples = []
        self.monitor_thread = None

    def start_monitoring(self, interval=1.0):
        """Start continuous memory monitoring"""
        self.monitoring = True
        self.memory_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop memory monitoring and return results"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        return self.get_memory_stats()

    def _monitor_loop(self, interval):
        """Memory monitoring loop"""
        while self.monitoring:
            try:
                # System memory
                system_mem = psutil.virtual_memory()

                # Process memory (find MCP server process)
                mcp_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        # Look for python processes with MCP server indicators
                        if ('python' in proc.info['name'] and
                            ('mcp_memory_server' in cmdline or 'main.py' in cmdline or
                             'uvicorn' in cmdline or 'src.mcp_memory_server.main:app' in cmdline or
                             'multiprocessing' in cmdline or 'spawn_main' in cmdline)):
                            mcp_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                process_memory = 0
                if mcp_processes:
                    process_memory = sum(proc.memory_info().rss for proc in mcp_processes)

                sample = {
                    'timestamp': time.time(),
                    'system_total_mb': system_mem.total / 1024 / 1024,
                    'system_used_mb': system_mem.used / 1024 / 1024,
                    'system_available_mb': system_mem.available / 1024 / 1024,
                    'system_percent': system_mem.percent,
                    'process_memory_mb': process_memory / 1024 / 1024,
                    'process_count': len(mcp_processes)
                }
                self.memory_samples.append(sample)

            except Exception as e:
                print(f"Memory monitoring error: {e}")

            time.sleep(interval)

    def get_memory_stats(self):
        """Calculate memory statistics"""
        if not self.memory_samples:
            return {}

        process_memories = [s['process_memory_mb'] for s in self.memory_samples]
        system_used = [s['system_used_mb'] for s in self.memory_samples]

        return {
            'samples_count': len(self.memory_samples),
            'duration_seconds': self.memory_samples[-1]['timestamp'] - self.memory_samples[0]['timestamp'],
            'process_memory': {
                'min_mb': min(process_memories) if process_memories else 0,
                'max_mb': max(process_memories) if process_memories else 0,
                'avg_mb': sum(process_memories) / len(process_memories) if process_memories else 0,
                'final_mb': process_memories[-1] if process_memories else 0
            },
            'system_memory': {
                'min_used_mb': min(system_used),
                'max_used_mb': max(system_used),
                'avg_used_mb': sum(system_used) / len(system_used),
                'final_used_mb': system_used[-1]
            },
            'raw_samples': self.memory_samples
        }


class MCPServerTester:
    """Test the MCP Memory Server"""

    def __init__(self, server_host="127.0.0.1", server_port=8080):
        self.host = server_host
        self.port = server_port
        self.server_process = None
        self.base_url = f"http://{server_host}:{server_port}"
        self._async_client = None  # Persistent async client for connection reuse

    def start_server(self, config_file=None):
        """Start the MCP server with enhanced error handling"""
        try:
            # Check for uvicorn availability first
            try:
                pass
            except ImportError:
                print("✗ uvicorn not available. Install with: pip install uvicorn")
                return False

            cmd = [
                sys.executable, '-m', 'uvicorn',
                'src.mcp_memory_server.main:app',
                '--host', self.host,
                '--port', str(self.port),
                '--reload'
            ]

            # Always set up environment for config file
            env = os.environ.copy()
            if config_file:
                env['MCP_CONFIG_FILE'] = config_file
            else:
                # Default to test config if no config specified
                test_config = Path(__file__).parent / "test_config.json"
                if test_config.exists():
                    env['MCP_CONFIG_FILE'] = str(test_config)

            self.server_process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait a bit for server to start
            time.sleep(3)  # Give server time to boot

            # Check if it's running
            if self.server_process.poll() is None:
                # Additional check: try to connect to health endpoint
                try:
                    import requests
                    response = requests.get(f"{self.base_url}/health", timeout=2)
                    if response.status_code == 200:
                        print(f"✓ MCP Server started successfully on {self.base_url}")
                        return True
                    else:
                        print(f"✗ Server started but health check failed: {response.status_code}")
                except BaseException:
                    print(f"✓ Server process started on {self.base_url} (health check unavailable)")
                    return True
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                error_msg = stderr.decode() if stderr else stdout.decode()
                print(f"✗ Server failed to start: {error_msg}")

                # Check for common dependency issues
                if "No module named" in error_msg:
                    missing_module = error_msg.split("No module named '")[1].split(
                        "'")[0] if "No module named '" in error_msg else "unknown"
                    print(f"💡 Missing dependency: {missing_module}. Install with: pip install {missing_module}")

                return False

        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the MCP server"""
        # Close the async client if it exists
        if self._async_client is not None:
            # Note: Can't await in sync context, but httpx handles cleanup on garbage collection
            self._async_client = None
        
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            print("✓ MCP Server stopped")
    
    async def _get_async_client(self):
        """Get or create a persistent async client for connection reuse.
        
        This significantly improves performance under load by reusing connections
        instead of creating a new connection for each request.
        
        The client is recreated if the event loop has changed (which happens
        between pytest async tests).
        """
        import asyncio
        current_loop = asyncio.get_event_loop()
        
        # Check if we need to recreate the client (new event loop or closed client)
        need_new_client = (
            self._async_client is None or 
            self._async_client.is_closed or
            getattr(self, '_client_loop', None) is not current_loop
        )
        
        if need_new_client:
            # Close old client if it exists and isn't already closed
            if self._async_client is not None and not self._async_client.is_closed:
                try:
                    await self._async_client.aclose()
                except Exception:
                    pass  # Ignore errors closing old client
            
            # Configure with higher limits for performance testing
            limits = httpx.Limits(
                max_connections=100,
                max_keepalive_connections=50,
                keepalive_expiry=30.0
            )
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=limits,
                timeout=30.0  # Longer timeout for heavy operations
            )
            self._client_loop = current_loop
            
        return self._async_client
    
    async def close_async_client(self):
        """Explicitly close the async client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    def is_server_running(self):
        """Check if server is responding"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception as e:
            print(f"Error checking server health: {e}")
            return False

    async def call_mcp_tool(self, tool_name, params=None):
        """Call an MCP tool via HTTP asynchronously.
        
        Uses a persistent connection pool for better performance under load.
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params or {}
                }
            }

            # Use persistent client for connection reuse
            client = await self._get_async_client()
            response = await client.post(
                "/",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()  # Raise an exception for 4xx or 5xx responses
            return response.json()

        except httpx.RequestError as e:
            return {"error": f"An error occurred while requesting {e.request.url!r}: {e}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e}"}
        except Exception as e:
            return {"error": str(e)}


@pytest.fixture(scope="session")
def mcp_server_tester():
    """Provides a server tester instance for starting/stopping the MCP server."""
    tester = MCPServerTester()
    yield tester
    # Ensure server is stopped after all tests in the session are done
    tester.stop_server()


@pytest.fixture(scope="session")
def running_mcp_server(mcp_server_tester, shared_test_env, production_server_check, check_server_dependencies):
    """Starts the MCP server once for the entire test session with shared test database.
    
    This fixture depends on production_server_check to ensure we don't accidentally
    run tests against a production database.
    """
    # Use the shared test environment config
    config_path = shared_test_env['config_path']
    port = shared_test_env['port']

    # Update server tester to use the test-specific port
    mcp_server_tester.port = port
    mcp_server_tester.base_url = f"http://{mcp_server_tester.host}:{port}"

    if not mcp_server_tester.is_server_running():
        assert mcp_server_tester.start_server(config_file=str(config_path)), "Failed to start MCP server"
        # Give it much more time for ML model loading and full startup
        print("⏳ Waiting for server to fully initialize (loading ML models)...")
        time.sleep(15)  # Much longer wait for ML model initialization

        # Retry health check with backoff
        for attempt in range(10):
            if mcp_server_tester.is_server_running():
                print("✓ Server is ready!")
                break
            print(f"⏳ Server not ready yet, retrying in {2 + attempt} seconds...")
            time.sleep(2 + attempt)
        else:
            raise AssertionError("Server failed to become ready after extended wait")
    yield mcp_server_tester
    # Server shutdown handled by session fixture


@pytest.fixture(scope="session")
def memory_monitor():
    """Provides a memory monitor instance for the test session."""
    monitor = MemoryMonitor()
    yield monitor
    # Stop monitoring at the end of the session
    monitor.stop_monitoring()


@pytest.fixture(scope="session")
def check_server_dependencies():
    """Check if server dependencies are available before running integration tests.
    
    Note: This fixture is NOT autouse - it's only used by integration tests that
    depend on running_mcp_server.
    """
    required_modules = ['fastapi', 'uvicorn']
    missing = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        pytest.skip(f"Server dependencies not available: {missing}. Install with: pip install {' '.join(missing)}")

    return True


@pytest.fixture(scope="session")
def production_server_check():
    """Check for production servers before running integration tests.
    
    This fixture is used by integration tests that need a running server.
    It provides immediate feedback if a production server is detected.
    
    Note: This fixture is NOT autouse - unit tests don't need this check
    since they don't use a running server.
    """
    test_port = int(os.environ.get('MCP_TEST_PORT', DEFAULT_TEST_PORT))
    
    # Check all common ports for running servers
    for port in COMMON_MCP_PORTS:
        if port == test_port:
            # The main check will handle the test port
            continue
        
        check = _check_existing_server("127.0.0.1", port)
        if check['running'] and not check['is_test']:
            server_title = check['info'].get('title', 'Unknown')
            print(f"\n⚠️  Warning: Non-test server detected on port {port}: {server_title}")
            print(f"   Tests will use port {test_port}. Ensure this is correct.\n")
    
    # Main safety check for the actual test port
    verify_no_production_server(port=test_port)
    
    yield
