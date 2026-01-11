#!/usr/bin/env python
"""
Run all backend tests before push.

Usage:
    python tests/run_all.py
    
Or with Docker:
    docker compose exec backend python tests/run_all.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    # Get tests directory
    tests_dir = Path(__file__).parent
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--color=yes",
    ]
    
    print("=" * 60)
    print("🧪 Running Audiovault Backend Tests")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✅ All tests passed! Safe to push.")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ Tests failed! Fix before pushing.")
        print("=" * 60)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
