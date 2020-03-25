#!/bin/bash

set -ev

# setup patterns for files/directories to ignore
declare -a ignore_patterns
ignore_patterns=(
  "^doc/"
  "^privacyidea/static/"
  "^privacyidea/translations/"
  "^migrations/"
  "^deploy/"
  "^contrib/"
  "READ_BEFORE_UPDATE.md"
  "README.rst"
  "SECURITY.md"
  "^\.circleci/"
  "^\.codespell_skip"
  "^\.github/"
  "^\.gitignore"
  "^\.pep8speaks.yml"
  "^\.readthedocs.yaml"
  )

# get the base branch for checking changes
if [[ $TRAVIS_PULL_REQUEST == false ]]; then
  base_branch="master"
else
  base_branch=${TRAVIS_BRANCH}
fi

echo "base_branch: $base_branch"
echo "travis pull request: $TRAVIS_PULL_REQUEST"

git remote set-branches --add origin "${base_branch}"
git fetch
git update-ref "${base_branch}" "origin/${base_branch}"
CHANGED_FILES=$( git diff --name-only --diff-filter=AM "${base_branch}"...HEAD )

echo "Changed Files: ${CHANGED_FILES}"

IGNORE_BUILD=True

for CHANGED_FILE in ${CHANGED_FILES}; do
  match_found=False
  for pattern in "${ignore_patterns[@]}"; do
    if [[ ${CHANGED_FILE} =~ ${pattern} ]]; then
      match_found=True
      echo "Match found! Changed file: $CHANGED_FILE, pattern: $pattern"
      break
    fi
  done
  if [[ ${match_found} == False ]]; then
    IGNORE_BUILD=False
    echo "Found a test-relevant file: $CHANGED_FILE. Executing tests."
    break
  fi
done

echo "IGNORE_BUILD: $IGNORE_BUILD"

if [[ ${IGNORE_BUILD} == True ]]; then
  echo "No changes to build-essential files found, exiting."
  exit 123
else
  echo "Changes to build-essential files found, continuing with tests."
fi

