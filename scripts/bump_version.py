import argparse
import re
from pathlib import Path
import json
import subprocess
import sys

ROOT_DIR = Path(__file__).parent.parent
VERSION_FILE = ROOT_DIR / "VERSION"
FRONTEND_PACKAGE_JSON = ROOT_DIR / "frontend" / "package.json"

def run_command(command, cwd=ROOT_DIR):
    try:
        subprocess.run(command, check=True, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(e.stderr.decode())
        sys.exit(1)

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

def git_automate(new_version):
    tag_name = f"v{new_version}"
    commit_msg = f"chore: bump version to {new_version}"
    
    print(f"\nPerforming Git operations...")
    
    # Git Add
    run_command("git add VERSION frontend/package.json")
    print("- Staged files")
    
    # Git Commit
    run_command(f'git commit -m "{commit_msg}"')
    print(f"- Created commit: {commit_msg}")
    
    # Git Tag
    # Check if tag exists locally
    try:
        subprocess.run(f"git rev-parse {tag_name}", check=True, cwd=ROOT_DIR, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"- Tag {tag_name} already exists. Skipping tag creation.")
    except subprocess.CalledProcessError:
        run_command(f'git tag -a {tag_name} -m "Release {tag_name}"')
        print(f"- Created tag: {tag_name}")

def main():
    parser = argparse.ArgumentParser(description="Bump application version")
    parser.add_argument('part', choices=['major', 'minor', 'patch'], help="Part of version to bump")
    parser.add_argument('--no-git', action='store_true', help="Skip git operations (commit & tag)")
    args = parser.parse_args()

    current_version = get_current_version()
    new_version = bump_version(current_version, args.part)
    
    print(f"Bumping version: {current_version} -> {new_version}")
    
    update_version_file(new_version)
    update_frontend_package(new_version)
    
    if not args.no_git:
        git_automate(new_version)
        print(f"\nSUCCESS! 🚀")
        print(f"Version bumped to {new_version} and tagged.")
        print(f"Run this to push changes:\n\n    git push && git push --tags\n")
    else:
        print("\nSkipped git operations.")
        print("Remember to commit the changes manually.")

if __name__ == "__main__":
    main()
