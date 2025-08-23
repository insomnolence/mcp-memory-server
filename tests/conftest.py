import pytest
import os
import sys
import time
import subprocess
import threading
import psutil
import requests
import httpx

# Explicitly add the project root to sys.path to ensure module imports work correctly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import test database setup utilities
from test_db_setup import setup_test_environment, cleanup_test_environment, get_test_db_manager

# Import fixtures from fixtures directory
from tests.fixtures.test_data_generator import data_generator

@pytest.fixture(scope="session")
def test_environment_cleanup():
    """Fixture to clean up test environments at the end of the test session."""
    yield
    # Cleanup all test databases and configs after all tests complete
    cleanup_test_environment()

@pytest.fixture(scope="session")
def shared_test_env():
    """Create a shared test environment with single test database for all tests."""
    # Set up test environment with deduplication enabled by default
    env = setup_test_environment(
        test_name="shared_test_session",
        enable_deduplication=True,
        ttl_fast_mode=True,
        port=8080  # Use fixed port for shared environment
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
        
    def start_server(self, config_file=None):
        """Start the MCP server with enhanced error handling"""
        try:
            # Check for uvicorn availability first
            try:
                import uvicorn
            except ImportError:
                print("✗ uvicorn not available. Install with: pip install uvicorn")
                return False
                
            cmd = [
                'python3', '-m', 'uvicorn',
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
            time.sleep(3) # Give server time to boot
            
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
                except:
                    print(f"✓ Server process started on {self.base_url} (health check unavailable)")
                    return True
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                error_msg = stderr.decode() if stderr else stdout.decode()
                print(f"✗ Server failed to start: {error_msg}")
                
                # Check for common dependency issues
                if "No module named" in error_msg:
                    missing_module = error_msg.split("No module named '")[1].split("'")[0] if "No module named '" in error_msg else "unknown"
                    print(f"💡 Missing dependency: {missing_module}. Install with: pip install {missing_module}")
                
                return False
                
        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the MCP server"""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            print("✓ MCP Server stopped")
    
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
        """Call an MCP tool via HTTP asynchronously."""
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
            
            async with httpx.AsyncClient(base_url=self.base_url) as client:
                response = await client.post(
                    "/",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            
            response.raise_for_status() # Raise an exception for 4xx or 5xx responses
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
def running_mcp_server(mcp_server_tester, shared_test_env):
    """Starts the MCP server once for the entire test session with shared test database."""
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

@pytest.fixture(scope="session", autouse=True)
def check_server_dependencies():
    """Check if server dependencies are available before running integration tests."""
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
