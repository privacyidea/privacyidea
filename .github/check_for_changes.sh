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
  "^.github/check_for_changes.sh"
  "^pi-manage"
  "^requirements.txt"
  "^setup.py"
)

CHANGED_FILES=${DIFF}
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
