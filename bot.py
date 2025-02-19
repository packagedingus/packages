import requests
import toml
import os
import re

repo_owner = 'packagedingus'
repo_name = 'packages'
bot_token = os.getenv('BOT_TOKEN')
bot_email = os.getenv('BOT_EMAIL', 'packagedingusbot@users.noreply.github.com')

issues_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
pulls_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
labels_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/labels"

headers = {
    'Authorization': f'token {bot_token}',
    'Accept': 'application/vnd.github.v3+json'
}

os.system(f'git config --global user.email "{bot_email}"')
os.system('git config --global user.name "packagedingusbot"')

def fetch_issues():
    response = requests.get(issues_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching issues: {response.status_code}")
        return []

def parse_issue_body(issue_body):
    name_pattern = r"(?i)Name:\s*([^\n]+)"
    version_pattern = r"(?i)Version\s*(latest)?:\s*\"([^\"]+)\""
    url_pattern = r"(?i)url:\s*\"([^\"]+)\""

    name_match = re.search(name_pattern, issue_body)
    version_match = re.search(version_pattern, issue_body)
    url_match = re.search(url_pattern, issue_body)

    if name_match and version_match and url_match:
        name = name_match.group(1).replace(" ", "")
        version = version_match.group(2)
        url = url_match.group(1)
        return name, version, url
    return None, None, None

def create_pull_request(branch_name, package_name, version, url, base_branch="main"):
    commit_message = f"Update {package_name} to version {version}"

    package_data = {
        'name': package_name,
        'vers': version,
        'url': url
    }
    os.makedirs(f"./{branch_name}/packages/{package_name}", exist_ok=True)
    package_toml_path = f"./{branch_name}/packages/{package_name}/package.toml"
    with open(package_toml_path, 'w') as toml_file:
        toml.dump(package_data, toml_file)

    os.system(f"git checkout -b {branch_name}")
    os.system(f"git add {package_toml_path}")
    os.system(f"git commit -m '{commit_message}'")
    os.system(f"git push origin {branch_name}")

    pr_data = {
        "title": commit_message,
        "head": branch_name,
        "base": base_branch,
        "body": f"Automatic update for {package_name} to version {version}."
    }
    response = requests.post(pulls_url, headers=headers, json=pr_data)
    if response.status_code == 201:
        pr_url = response.json()['html_url']
        return pr_url
    else:
        print(f"Error creating PR: {response.status_code}")
        return None

def comment_on_issue(issue_number, comment):
    comment_url = f"{issues_url}/{issue_number}/comments"
    comment_data = {"body": comment}
    response = requests.post(comment_url, headers=headers, json=comment_data)
    if response.status_code == 201:
        print(f"Commented on issue #{issue_number}: {comment}")
    else:
        print(f"Error commenting on issue #{issue_number}: {response.status_code}")

def add_label_to_issue(issue_number, label):
    label_data = {"labels": [label]}
    response = requests.post(f"{issues_url}/{issue_number}/labels", headers=headers, json=label_data)
    if response.status_code == 200:
        print(f"Added label '{label}' to issue #{issue_number}")
    else:
        print(f"Error adding label to issue #{issue_number}: {response.status_code}")

def close_issue(issue_number):
    issue_data = {"state": "closed"}
    response = requests.patch(f"{issues_url}/{issue_number}", headers=headers, json=issue_data)
    if response.status_code == 200:
        print(f"Issue #{issue_number} closed.")
    else:
        print(f"Error closing issue #{issue_number}: {response.status_code}")

def comment_invalid_syntax(issue_number):
    error_message = "Error! Invalid syntax. Please correct it and make a new issue."
    comment_on_issue(issue_number, error_message)

def comment_bot_error(issue_number, error_text):
    error_message = f"Error! {error_text} Please submit an issue in [packagedingus/error](https://github.com/{repo_owner}/{repo_name}/issues)."
    comment_on_issue(issue_number, error_message)

def main():
    issues = fetch_issues()

    if issues:
        for issue in issues:
            if 'pull_request' not in issue:
                issue_number = issue['number']
                issue_author = issue['user']['login']
                
                comment_on_issue(issue_number, "Running checks...")

                name, version, url = parse_issue_body(issue['body'])

                if name and version and url:
                    try:
                        branch_name = f"update-{name}-{version}"
                        pr_url = create_pull_request(branch_name, name, version, url)

                        if pr_url:
                            comment_on_issue(issue_number, f"Success! The update has been submitted in a pull request: {pr_url}")
                            print(f"Pull request created: {pr_url}")
                        else:
                            raise ValueError("Failed to create pull request")
                    except Exception as e:
                        comment_bot_error(issue_number, str(e))
                        add_label_to_issue(issue_number, "invalid")
                        close_issue(issue_number)
                else:
                    comment_invalid_syntax(issue_number)
                    add_label_to_issue(issue_number, "invalid")
                    close_issue(issue_number)

if __name__ == '__main__':
    main()
