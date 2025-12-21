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

def get_last_tag():
    try:
        # Get the latest reachable tag
        result = subprocess.run("git describe --tags --abbrev=0", cwd=ROOT_DIR, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return result.stdout.decode().strip()
    except Exception:
        pass
    return None

def get_commits(since_tag):
    range_spec = f"{since_tag}..HEAD" if since_tag else "HEAD"
    cmd = f'git log {range_spec} --pretty=format:"%s"'
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.stdout.decode('utf-8', errors='ignore').splitlines()
    except subprocess.CalledProcessError:
        return []

from collections import defaultdict

COMMIT_TYPES = {
    'feat': 'Feature',
    'fix': 'Bug Fixes',
    'refactor': 'Refactor',
    'chore': 'Chore',
    'docs': 'Documentation',
    'perf': 'Performance',
    'style': 'Style',
    'test': 'Tests',
    'build': 'Build',
    'ci': 'CI'
}

def parse_commits(commits):
    """
    Parses commit messages and groups them based on Conventional Commits.
    """
    groups = defaultdict(list)
    
    # regex for conventional commits: type(scope)!: message or type: message
    # We will be lenient with casing
    regex = r"^(feat|fix|refactor|chore|docs|perf|style|test|build|ci)(\([a-z0-9\-_]+\))?(!)?: (.+)"
    
    for msg in commits:
        if not msg.strip(): continue
        
        match = re.match(regex, msg, re.IGNORECASE)
        if match:
            c_type = match.group(1).lower()
            desc = match.group(4)
            # Optional scope (not used for grouping currently but preserved in description if desired)
            # scope = match.group(2) 
            
            category = COMMIT_TYPES.get(c_type, 'Other')
            groups[category].append(desc)
        else:
            # Fallback for non-conventional
            lower_msg = msg.lower()
            if lower_msg.startswith("refactor"):
                groups['Refactor'].append(msg[8:].strip(": "))
            else:
                groups['Other'].append(msg)
                
    return groups

def update_changelog_file(new_version, groups):
    from datetime import date
    changelog_path = ROOT_DIR / "CHANGELOG.md"
    today = date.today().isoformat()
    
    new_entry = f"## [{new_version}] - {today}\n\n"
    
    has_content = False
    
    # Order of appearance
    priority_order = ['Feature', 'Bug Fixes', 'Performance', 'Refactor', 'Documentation', 'Tests', 'Build', 'CI', 'Chore', 'Other']
    
    for category in priority_order:
        items = groups.get(category, [])
        if items:
            has_content = True
            new_entry += f"### {category}\n"
            for item in items:
                new_entry += f"- {item}\n"
            new_entry += "\n"
    
    if not has_content:
        new_entry += "- No significant changes documented.\n\n"
        
    old_content = ""
    if changelog_path.exists():
        old_content = changelog_path.read_text(encoding='utf-8')
        
    # Prepend new entry
    new_content = "# Changelog\n\n" + new_entry + old_content.replace("# Changelog\n\n", "")
    
    changelog_path.write_text(new_content, encoding='utf-8')
    print(f"Updated CHANGELOG.md for v{new_version}")

def git_automate(new_version):
    tag_name = f"v{new_version}"
    commit_msg = f"chore: bump version to {new_version}"
    
    # Generate Changelog
    print("Generating Changelog...")
    last_tag = get_last_tag()
    print(f"  Last tag: {last_tag or 'None (initial)'}")
    commits = get_commits(last_tag)
    print(f"  Found {len(commits)} commits since last tag")
    
    groups = parse_commits(commits)
    update_changelog_file(new_version, groups)

    print("\nPerforming Git operations...")
    
    # Git Add
    run_command("git add VERSION frontend/package.json CHANGELOG.md")
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
        print("\nSUCCESS! 🚀")
        print(f"Version bumped to {new_version} and tagged.")
        print("Run this to push changes:\n\n    git push && git push --tags\n")
    else:
        print("\nSkipped git operations.")
        print("Remember to commit the changes manually.")

if __name__ == "__main__":
    main()
