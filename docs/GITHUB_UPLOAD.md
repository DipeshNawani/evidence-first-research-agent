# Publish this project to GitHub

The repository already contains a root [README.md](../README.md). GitHub displays that README automatically on the repository landing page, beneath the file browser. The screenshots under `docs/assets/` use relative paths and are included with the source.

## 1. Create an empty repository

Sign in and open [GitHub's new repository page](https://github.com/new). Use:

**Repository name**

```text
evidence-first-research-agent
```

**Description**

```text
Evidence-first AI research agent with bounded planning, cited findings, FastAPI UI, NVIDIA/OpenAI/Anthropic support, offline fault testing, and traceable evaluation.
```

Choose **Public** for a shareable portfolio repository, or **Private** when the assignment requires restricted access. Leave the options to add a README, .gitignore, license, or other starter content unselected, then click **Create repository**. This project already has local Git history and those starter files would create a second history to reconcile.

Keep the new repository page open and copy its HTTPS URL. The following steps use `YOUR_USERNAME`; replace that placeholder with your actual GitHub username.

## 2. Open the existing project in VS Code

Choose **File → Open Folder**, select `D:\predictionaiproj`, then choose **Terminal → New Terminal**. Use PowerShell:

```powershell
cd D:\predictionaiproj
git status
```

At preparation time, this project already had one commit, branch `master`, a configured Git author, and no remote. You do not need `git init`. Your local application can remain running while you upload its source.

## 3. Check what stays local

The project's `.gitignore` excludes `.env` and local variants, virtual environments, temporary output, runtime traces, caches, and built archives. `.env.example` remains included so other users can configure their own keys.

```powershell
git check-ignore .env .venv/ tmp/ traces/ dist/
git ls-files -- .env .venv tmp traces dist
```

The first command should list the ignored local paths. The second should print nothing; it checks that these paths are not already tracked. Keep actual credentials in the ignored `.env` file.

## 4. Stage and review the project

```powershell
git add .
git diff --cached --name-only
```

This prepares the source, README, screenshots, tests, sample outputs, evaluation records, configuration template, and documentation. Check that `.env`, `.venv/`, `tmp/`, `traces/`, and `dist/` are absent. `samples/*.trace.jsonl` and selected `eval/results/` traces are intentional redacted evidence files, distinct from local runtime `traces/`.

To review the text changes before committing:

```powershell
git diff --cached
```

Press **q** if Git opens a pager. If an unexpected file is staged, remove it from staging with `git restore --staged -- PATH_TO_FILE` and resolve the ignore rule before continuing.

## 5. Commit and name the branch

```powershell
git commit -m "Prepare research agent for GitHub with web demo and documentation"
git branch -m main
```

The commit records the latest approved changes. The branch command renames the current `master` branch to `main` to match the commands below. If `git branch --show-current` already prints `main`, skip the rename.

## 6. Connect the GitHub repository

Replace `YOUR_USERNAME`, then run:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/evidence-first-research-agent.git
git remote -v
```

Both fetch and push entries should show the intended repository. If a remote already exists by the time you follow this guide, inspect `git remote -v` before changing it. The preparation check found no existing remote.

## 7. Push the project

```powershell
git push -u origin main
```

Complete GitHub authentication if prompted. Git for Windows with Git Credential Manager can open a browser sign-in flow and handle two-factor authentication. Use your GitHub login in that flow; application API keys are unrelated to GitHub authentication.

After a successful push, refresh the GitHub repository page. You should see the source directories and the rendered README with the homepage screenshot, setup commands, architecture diagram, and evaluation links.

## 8. Add repository topics and share

In the repository's **About** settings, add relevant topics such as:

```text
ai-agents research-agent fastapi python llm pydantic nvidia-nemotron platform-engineering
```

Confirm that the screenshots render and `.env` is absent. Share the repository's normal web URL with your reviewer. The repository publishes source and documentation; it does not host the running FastAPI service. Localhost links work on a computer where the application is running.

## Upload later changes

From the project folder:

```powershell
git add .
git diff --cached --name-only
git commit -m "Describe the changes made"
git push
```

## If an upload fails

- **Repository not found:** confirm the copied HTTPS URL, signed-in account, and access to the repository.
- **Remote origin already exists:** inspect `git remote -v`. If it points to this repository already, continue to the push step; update it only when you intend to replace the destination.
- **Push rejected because the remote has commits:** stop and inspect the existing GitHub content. The instructions above assume a newly created empty repository. Preserve remote work rather than force-pushing over it.
- **Authentication issue:** follow [GitHub's credential guidance](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git). Do not put access tokens in the remote URL or paste them into this guide.

## Official references

- [Create a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository).
- [Upload existing local code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).
- [Manage remotes](https://docs.github.com/en/get-started/git-basics/managing-remote-repositories).
- [README rendering and relative image paths](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).
