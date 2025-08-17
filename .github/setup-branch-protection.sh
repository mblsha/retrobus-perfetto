#!/usr/bin/env bash

# Exit on error, undefined variable, or pipe failure
set -Eeuo pipefail

# Auto-detect repository if not provided
if ! REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null); then
    echo "Error: Unable to detect repository. Make sure you're in a git repository with a remote."
    exit 1
fi

# Auto-detect default branch if not provided
if ! BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null); then
    echo "Error: Unable to detect default branch."
    exit 1
fi

# Parse command line arguments
AUTO_CONFIRM=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_CONFIRM=true
            shift
            ;;
        *)
            echo "Usage: $0 [-y|--yes]"
            echo "  -y, --yes    Auto-confirm branch protection setup"
            exit 1
            ;;
    esac
done

echo "Repository: $REPO"
echo "Branch: $BRANCH"

# List current status checks
echo ""
echo "Current required status checks:"
gh api "repos/$REPO/branches/$BRANCH/protection" 2>/dev/null | \
    jq -r '.required_status_checks.checks[]?.context // "None configured"' 2>/dev/null || echo "Branch protection not configured"

# Prepare branch protection settings
PROTECTION_JSON=$(cat <<EOF
{
  "required_status_checks": {
    "strict": false,
    "checks": [
      {"context": "Python CI / test"},
      {"context": "Python CI / lint"},
      {"context": "Python CI / type-check"},
      {"context": "C++ CI / build (Debug, g++)"},
      {"context": "C++ CI / build (Debug, clang++)"},
      {"context": "C++ CI / build (Release, g++)"},
      {"context": "C++ CI / build (Release, clang++)"}
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
)

# Confirm before applying
if [ "$AUTO_CONFIRM" = false ]; then
    echo ""
    echo "About to set up branch protection for $BRANCH on $REPO"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Apply branch protection (always use PUT for consistency)
echo "Setting up branch protection..."
if gh api --method PUT "repos/$REPO/branches/$BRANCH/protection" \
    --input - <<< "$PROTECTION_JSON"; then
    echo "✅ Branch protection has been set up successfully!"
else
    echo "❌ Failed to set up branch protection"
    exit 1
fi