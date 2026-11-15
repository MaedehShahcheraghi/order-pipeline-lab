#!/usr/bin/env bash
# Run from the EXTRACTED ZIP. Creates a feature branch and pushes it to GitHub.
# Never pushes directly to main or develop. Requires git authentication.
set -euo pipefail
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="https://github.com/MaedehShahcheraghi/order-pipeline-lab.git"
BRANCH="feature/bootstrap-ci"
WORK_DIR="$(mktemp -d)"
TARGET="$WORK_DIR/order-pipeline-lab"

if ! git ls-remote --exit-code --heads "$REPO" develop >/dev/null; then
  echo "ERROR: Remote 'develop' branch not found or no GitHub access. Create develop first." >&2
  exit 1
fi

git clone --branch develop "$REPO" "$TARGET"
git -C "$TARGET" switch -c "$BRANCH"
cp -a "$SOURCE_ROOT/." "$TARGET/"
# No .git directory exists in the ZIP. Existing Git history remains intact.
cd "$TARGET"
git add .
if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi
git commit -m "feat: bootstrap .NET API, tests and automation"
git push -u origin "$BRANCH"
echo "Pushed $BRANCH. Open PR: $BRANCH -> develop"
echo "PR title: feat: bootstrap .NET API, tests and automation"





