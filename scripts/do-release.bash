#!/bin/bash

set -euo pipefail
set -x

# args:
# $1 is the title
# $2 is tag name to make release for
# $3 is directory of release files
# $4 is "true" or "false" for prerelease
# $5 is "true" or "false" for draft

title="$1"
tag_name="$2"
release_dir="$3"
prerelease="$4"
draft="$5"

message="$title\nAutomated build."

hub(){
    echo "$*"
}

hub release create -t "$GITHUB_SHA" -m "$message" -d --prerelease="$prerelease" "$tag_name"
for file in "$release_dir/*"
do
    hub release edit -m "" -a "$file" "$tag_name"
done

if [ "$draft" == "false" ]
then
    hub release edit -m "" --draft="$draft"
fi
