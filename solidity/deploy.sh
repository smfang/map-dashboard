#!/bin/bash

# Initialize git if not already initialized
if [ ! -d .git ]; then
    git init
fi

# Add all files
git add .

# Commit changes
git commit -m "Initial deployment of map dashboard"

# Add the remote repository if it doesn't exist
if ! git remote | grep -q "origin"; then
    git remote add origin https://github.com/smfang/map-dashboard.git
fi

# Push to GitHub
git push -u origin main 