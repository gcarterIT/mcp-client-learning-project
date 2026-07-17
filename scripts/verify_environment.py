"""
verify_environment.py

Purpose
-------
Verify that the Python environment for the MCP Learning Project
is correctly configured before beginning development.

This script intentionally performs only environment checks.
It does NOT connect to an MCP server.

Running this script should become your first troubleshooting step
whenever something appears wrong.

Expected Result
---------------
All checks should report PASS.
"""

from importlib.metadata import version
import platform
import sys

print("=" * 60)
print("MCP Learning Project - Environment Verification")
print("=" * 60)

print(f"Python executable : {sys.executable}")
print(f"Python version    : {platform.python_version()}")
print()

packages = [
    "mcp",
    "pydantic",
    "streamlit",
    "httpx",
    "rich",
]

for package in packages:
    try:
        print(f"[PASS] {package:<12} version {version(package)}")
    except Exception as exc:
        print(f"[FAIL] {package:<12} ({exc})")

print()
print("Environment verification complete.")