import sys
import subprocess

try:
    import mcp
except ImportError:
    print("==> conftest.py: Installing missing dependency 'mcp'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp[cli]>=1.0.0"])
