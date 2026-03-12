# Private GitLab Heatmap Exporter — AI Setup Guide

This file contains instructions for AI agents helping users configure this project. The project generates a GitHub-style contribution heatmap SVG from a private GitLab instance via a daily GitHub Actions workflow running on a self-hosted runner.

## Prerequisites

The user needs: a GitHub account owning a fork/clone of this repo, access to a private GitLab instance, and a machine with network access to that GitLab (VPN, same network, etc.) to host the runner.

## Setup Sequence

### 1. GitLab Token

The workflow needs a GitLab Personal Access Token with `read_user` scope. Create one via GitLab UI (`/-/user_settings/personal_access_tokens`) or API. If the user has `glab` CLI authenticated, check if the existing token already has `read_user` scope — reuse it instead of creating a new one.

Verify existing token scopes:
```bash
GITLAB_TOKEN=$(glab config get token --host <GITLAB_HOST>)
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://<GITLAB_HOST>/api/v4/personal_access_tokens/self" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('scopes'))"
```

### 2. GitHub Secrets

Set three repository secrets using `gh secret set`:

| Secret | Value | Source |
|--------|-------|--------|
| `GITLAB_URL` | Base URL of the GitLab instance (e.g., `https://gitlab.example.com`) | User provides |
| `GITLAB_TOKEN` | GitLab PAT with `read_user` scope | Step 1 |
| `RUNNER_CHECK_TOKEN` | GitHub token with repo admin read access | `gh auth token` works if user has admin access to the repo |

```bash
gh secret set GITLAB_URL --repo OWNER/REPO --body "https://gitlab.example.com"
gh secret set GITLAB_TOKEN --repo OWNER/REPO --body "$GITLAB_TOKEN"
gh secret set RUNNER_CHECK_TOKEN --repo OWNER/REPO --body "$(gh auth token)"
```

### 3. Self-Hosted Runner

The workflow runs on `self-hosted` because private GitLab instances are not reachable from GitHub-hosted runners. Register a runner on a machine with network access to GitLab.

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -sO -L https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf actions-runner-linux-x64-2.322.0.tar.gz && rm actions-runner-linux-x64-2.322.0.tar.gz
```

Check the latest runner version at `https://github.com/actions/runner/releases` before downloading — the version above may be outdated.

Register and install as a service:
```bash
RUNNER_TOKEN=$(gh api repos/OWNER/REPO/actions/runners/registration-token -X POST --jq '.token')
./config.sh --url https://github.com/OWNER/REPO --token "$RUNNER_TOKEN" --name "$(hostname)" --labels "self-hosted,linux,x64" --unattended --replace
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start
```

Verify the runner is online:
```bash
gh api repos/OWNER/REPO/actions/runners --jq '.runners[] | {name, status}'
```

### 4. Enable and Test

The workflow may be disabled by default. Enable it, trigger a manual run, and verify:

```bash
gh workflow enable update-graph.yml --repo OWNER/REPO
gh workflow run update-graph.yml --repo OWNER/REPO
sleep 10 && gh run list --repo OWNER/REPO --limit 1
```

Watch the run until completion:
```bash
gh run watch $(gh run list --repo OWNER/REPO --limit 1 --json databaseId --jq '.[0].databaseId') --repo OWNER/REPO
```

Verify the commit was made:
```bash
gh api repos/OWNER/REPO/commits --jq '.[0] | {sha: .sha[0:7], message: .commit.message, date: .commit.author.date}'
```

## Constraints

- **VPN/Network**: If GitLab requires VPN, the runner machine must have VPN connected when the workflow fires. The workflow runs daily at 12PM BRT (15:00 UTC) — VPN needs to be active at that time.
- **SAML VPN**: If the VPN uses SAML/browser authentication, it cannot be fully automated via cron. The runner service stays running and picks up jobs whenever VPN happens to be connected.
- **Runner check job**: The workflow's `check-runner` job verifies the self-hosted runner is online before dispatching the build job, preventing stuck workflows when VPN is down.
- **Graceful GitLab failure**: The Python script exits cleanly (exit 0) if GitLab is unreachable, so the workflow won't report failures when network is temporarily unavailable.
