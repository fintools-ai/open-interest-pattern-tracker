#!/bin/bash

# Git setup script for OI Pattern Tracker

echo "Setting up git repository for fintools-ai/open-interest-pattern-tracker"

# Initialize git if not already initialized
if [ ! -d .git ]; then
    git init
    echo "Initialized git repository"
fi

# Add the remote repository
git remote add origin https://github.com/fintools-ai/open-interest-pattern-tracker.git

# Create initial commit
git add .
git commit -m "Initial commit: OI Pattern Tracker - Options trading signal system based on open interest analysis"

# Push to main branch
echo "Pushing to GitHub..."
git push -u origin main

echo "Done! Your code has been pushed to https://github.com/fintools-ai/open-interest-pattern-tracker"
