#!/usr/bin/env bash
# One-time helper to create the GitHub repo and push this folder.
# Run it from INSIDE the learning-ai-agents folder:  bash push_to_github.sh
#
# Option A (easiest): you have the GitHub CLI 'gh' installed and logged in.
#   - Install: https://cli.github.com  ->  then run:  gh auth login
# Option B (no gh): create an EMPTY repo named learning-ai-agents on github.com
#   first (no README), then run this script — it will use the normal git remote.

set -e
REPO_NAME="learning-ai-agents"
VISIBILITY="public"   # change to "private" if you prefer

git init
git add .
git commit -m "Initial commit: AI agents guide, concept map, and 3-level starter project"
git branch -M main

if command -v gh >/dev/null 2>&1; then
  echo "Using GitHub CLI to create and push the repo..."
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
  echo "Done. Your repo is live."
else
  echo "GitHub CLI ('gh') not found."
  echo "1) Create an EMPTY repo at https://github.com/new named '$REPO_NAME' (no README/license)."
  echo "2) Then run these two lines, replacing YOUR-USERNAME:"
  echo "     git remote add origin https://github.com/YOUR-USERNAME/$REPO_NAME.git"
  echo "     git push -u origin main"
fi
