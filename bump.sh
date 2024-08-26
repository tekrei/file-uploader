#!/usr/bin/env bash
# exit when a command fails
set -e
# BUMP_TYPE is the first argument to the script
# It should ideally be a valid semver string or a valid bump rule:
#       patch, minor, major, prepatch, preminor, premajor, prerelease
# Default is patch
BUMP_TYPE="${1:-patch}"
# bump the version
poetry version $BUMP_TYPE
# update the version file
echo "__version__ = \"$(poetry version --short)\"" >uploader/_version.py
