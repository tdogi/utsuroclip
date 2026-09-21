#!/bin/bash

cd "$(cd "$(dirname "$0")" && pwd)"


if [ "$1" = "--dev" ]; then
    cp AGENTS.dev.md AGENTS.md
    cp -r .codex.dev .codex
    echo "Developer Setup completed successfully."
fi
