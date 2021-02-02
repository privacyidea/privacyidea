#!/bin/bash

set -e

# setup patterns for files/directories to include
declare -a include_patterns
include_patterns=(
  "^migrations/"
  "^tests/"
  "^tools/"
  "^privacyidea/lib/"
  "^privacyidea/api/"
  "^privacyidea/webui/"
  "^privacyidea/app.py"
  "^privacyidea/config.py"
  "^privacyidea/models.py"
  "^.github/workflows/python.yml"
  "^pi-manage"
  "^requirements.txt"
  "^setup.py"
)

if [[ -n ${GITHUB_BASE_REF} ]]; then
  echo "PR BASE: ${GITHUB_BASE_REF}"
  # we are in a pull request
  # first get the base branch updated (github only clones with depth 1)
  git fetch origin "${GITHUB_BASE_REF}" --depth=1
  # now get all changed files
  CHANGED_FILES=$( git diff --name-only --diff-filter=AM "${GITHUB_BASE_REF}"... )
elif [[ -n ${GITHUB_REF} ]]; then
  GITHUB_EVENT_BEFORE=$( echo ${GITHUB_CONTEXT} | jq '.event.before' )
  echo "PUSH BASE: ${GITHUB_REF}"
  echo "PUSH BEFORE: ${GITHUB_EVENT_BEFORE}"
  # This is a push event to branch GITHUB_REF
  git fetch origin "${GITHUB_EVENT_BEFORE}" --depth=1
  CHANGED_FILES=$( git diff --name-only --diff-filter=AM "${GITHUB_EVENT_BEFORE}"... )
else
  # No idea what triggered this script
  echo "::warning::Unknown event type: ${GITHUB_EVENT_NAME}"
  echo "::set-output name=ignore_build::True"
  exit 1
fi

echo "Changed Files: ${CHANGED_FILES}"

IGNORE_BUILD=True

for CHANGED_FILE in ${CHANGED_FILES}; do
  match_found=False
  for pattern in "${include_patterns[@]}"; do
    if [[ ${CHANGED_FILE} =~ ${pattern} ]]; then
      match_found=True
      echo "Match found! Changed file: $CHANGED_FILE, pattern: $pattern"
      break
    fi
  done
  if [[ ${match_found} == True ]]; then
    IGNORE_BUILD=False
    echo "Found a test-relevant file: $CHANGED_FILE. Executing tests."
    break
  fi
done

echo "IGNORE_BUILD: $IGNORE_BUILD"

if [[ ${IGNORE_BUILD} == True ]]; then
  echo "No changes to build-essential files found, exiting."
  echo "::set-output name=run_tests::False"
else
  echo "Changes to build-essential files found, continuing with tests."
  echo "::set-output name=run_tests::True"
fi
