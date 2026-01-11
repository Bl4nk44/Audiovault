import sys
import os
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: update_versions.py <version>")
        sys.exit(1)
        
    version = sys.argv[1]
    print(f"Bumping version to {version}...")
    
    # Update VERSION (root)
    try:
        with open("VERSION", "w") as f:
            f.write(version)
    except Exception as e:
        print(f"Error writing VERSION: {e}")

    # Update backend/VERSION
    try:
        with open("backend/VERSION", "w") as f:
            f.write(version)
    except Exception as e:
         print(f"Error writing backend/VERSION: {e}")
        
    # Update frontend/package.json via npm
    # We use shell=True for Windows compatibility in dev, though CI uses Linux.
    # npm needs to be in PATH.
    frontend_dir = "frontend"
    if os.path.exists(frontend_dir):
        print("Updating frontend package.json...")
        try:
            # On Windows, npm is a .cmd file, requires shell=True. On Linux/CI it works too.
            subprocess.run("npm version " + version + " --no-git-tag-version --allow-same-version", 
                           cwd=frontend_dir, check=True, shell=True)
        except subprocess.CalledProcessError as e:
             print(f"Warning: npm version failed: {e}")
    
    # Git Add files to include them in the release commit
    print("Staging files for commit...")
    files_to_add = ["VERSION", "backend/VERSION", "frontend/package.json"]
    # Only add existing files
    files_to_add = [f for f in files_to_add if os.path.exists(f)]
    
    if files_to_add:
        subprocess.run(["git", "add"] + files_to_add, check=True, shell=False)

if __name__ == "__main__":
    main()
