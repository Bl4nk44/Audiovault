import argparse
import re
from pathlib import Path
import json

ROOT_DIR = Path(__file__).parent.parent
VERSION_FILE = ROOT_DIR / "VERSION"
FRONTEND_PACKAGE_JSON = ROOT_DIR / "frontend" / "package.json"

def get_current_version():
    return VERSION_FILE.read_text().strip()

def bump_version(current_version, part):
    major, minor, patch = map(int, current_version.split('.'))
    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    elif part == 'patch':
        patch += 1
    return f"{major}.{minor}.{patch}"

def update_version_file(new_version):
    VERSION_FILE.write_text(new_version)
    print(f"Updated VERSION to {new_version}")

def update_frontend_package(new_version):
    if not FRONTEND_PACKAGE_JSON.exists():
        print("Frontend package.json not found, skipping.")
        return

    content = json.loads(FRONTEND_PACKAGE_JSON.read_text())
    content['version'] = new_version
    FRONTEND_PACKAGE_JSON.write_text(json.dumps(content, indent=2))
    print(f"Updated frontend package.json to {new_version}")

def main():
    parser = argparse.ArgumentParser(description="Bump application version")
    parser.add_argument('part', choices=['major', 'minor', 'patch'], help="Part of version to bump")
    args = parser.parse_args()

    current_version = get_current_version()
    new_version = bump_version(current_version, args.part)
    
    print(f"Bumping version: {current_version} -> {new_version}")
    
    update_version_file(new_version)
    update_frontend_package(new_version)
    
    print("\nDone! Remember to commit the changes.")

if __name__ == "__main__":
    main()
