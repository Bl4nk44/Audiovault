import argparse
import json
import urllib.request
import urllib.error
import base64
import os
import sys

def fetch_issues(host, project_key, token):
    # API endpoint for searching issues
    # resolved=false -> only open issues
    # ps=500 -> page size (limit to 500 for now)
    url = f"{host}/api/issues/search?componentKeys={project_key}&resolved=false&ps=500"
    
    # Prepare Basic Auth header
    auth_str = f"{token}:"
    auth_bytes = auth_str.encode("ascii")
    auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
    headers = {"Authorization": f"Basic {auth_b64}"}
    
    print(f"Connecting to {url}...")
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Error: Server returned status {response.status}")
                return []
            data = json.load(response)
            return data.get('issues', [])
    except urllib.error.URLError as e:
        print(f"Connection error: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def save_report(issues, output_file, host, project_key):
    # Sort issues by severity
    severity_order = {"BLOCKER": 0, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}
    issues.sort(key=lambda x: severity_order.get(x.get('severity', 'INFO'), 5))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# SonarQube Report: {project_key}\n\n")
        f.write(f"**Source**: {host}\n")
        f.write(f"**Total Issues**: {len(issues)}\n\n")
        
        if not issues:
            f.write("No issues found! Great job. \n")
            return

        for issue in issues:
            severity = issue.get('severity', 'UNKNOWN')
            message = issue.get('message', '')
            component = issue.get('component', '')
            # Try to extract relative path from component key (usually ProjectKey:Path)
            file_path = component.replace(f"{project_key}:", "")
            
            line = issue.get('line', 0)
            rule = issue.get('rule', '')
            issue_key = issue.get('key', '')
            type_ = issue.get('type', 'CODE_SMELL')
            
            # Emoji for severity
            icon = "🔴" if severity in ["BLOCKER", "CRITICAL"] else "🟠" if severity == "MAJOR" else "🔵"
            
            f.write(f"### {icon} [{severity}] {message}\n")
            f.write(f"- **Type**: {type_}\n")
            f.write(f"- **File**: `{file_path}:{line}`\n")
            f.write(f"- **Rule**: `{rule}`\n")
            f.write(f"- **Link**: [Open in Sonar]({host}/project/issues?id={project_key}&open={issue_key})\n")
            
            # Add simple visualization of text range if available (not fetching file content here though)
            f.write("\n---\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch SonarQube issues report")
    parser.add_argument("--host", default="http://192.168.178.22:9000", help="SonarQube host URL")
    parser.add_argument("--token", required=True, help="User authentication token")
    parser.add_argument("--project", default="SonarQube2137", help="Project Key")
    parser.add_argument("--output", default="sonar_report.md", help="Output markdown file")
    
    args = parser.parse_args()
    
    issues = fetch_issues(args.host, args.project, args.token)
    if issues is not None:
        save_report(issues, args.output, args.host, args.project)
        print(f"Successfully saved {len(issues)} issues to {args.output}")
    else:
        sys.exit(1)
