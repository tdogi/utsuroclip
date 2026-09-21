#!/usr/bin/env bash

set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)"

copy_directory_contents() {
    local source="$1"
    local destination="$2"
    mkdir -p "$destination"
    cp -R "$source"/. "$destination"/
}

case "${1:-}" in
    --dev)
        rm -rf .codex .agents
        cp AGENTS.dev.md AGENTS.md
        copy_directory_contents .codex.dev .codex
        echo "Developer setup completed successfully."
        ;;
    "")
        rm -rf .codex .agents
        cp AGENTS.user.md AGENTS.md
        copy_directory_contents .codex.user .codex
        copy_directory_contents .agents.user .agents
        echo "User setup completed successfully."
        ;;
    -h|--help)
        echo "Usage: bash setup.sh [--dev]"
        echo "  (no option)  Install UtsuroClip user-mode Codex settings and skills"
        echo "  --dev        Install UtsuroClip development-mode Codex settings"
        ;;
    *)
        echo "Unknown option: $1" >&2
        echo "Usage: bash setup.sh [--dev]" >&2
        exit 2
        ;;
esac
