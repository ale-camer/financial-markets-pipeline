# Contributing Guidelines and Workflow

To maintain a clean and organized repository, we use an Issue-based workflow using the GitHub CLI (`gh`).

## Mandatory Workflow

**Never** commit directly to `main` or `develop`. Always create a specific branch for each issue by following these steps:

### 1. Start a New Issue
Before writing any code, link a new branch to the issue you are working on using `gh`:

```bash
gh issue develop <ISSUE_NUMBER> --name "feat/descriptive-name"
```
*Example: `gh issue develop 18 --name "docs/final-readme"`*

### 2. Development
Make your changes and write descriptive commits on that new branch.

```bash
git add .
git commit -m "feat: description of changes (#ISSUE_NUMBER)"
```

### 3. Finish
Push your changes to GitHub:
```bash
git push origin <your-branch-name>
```

Close the issue (or create a Pull Request) leaving a comment:
```bash
gh issue close <ISSUE_NUMBER> --comment "Implemented final resolution."
```
