#!/bin/bash

# We want to loop over all 3 platform builds across all supported Binary Ninja
# versions and copy all built artifacts into one release directory, adding
# "dev-" or "stable-" to the beginning of the filename to disambiguate.
# We then print the hashes for good measure.

# Parameters: set of builds to dir up. i.e. "dev stable"

set -x

set -euo pipefail

mkdir release

# for i in dev stable
for i in $*
do
    # for file in dev/*
    for file in ${i}-*/*
    do
        # file = dev-macOS/libbinja_printk.dylib
        # base = libbinja_printk.dylib
        base="$(basename "$file")"
        # cp dev-macOS/libbinja_printk.dylib release/dev-libbinja_printk.dylib
        cp "$file" "release/${i}-$base"
    done
done

sha256sum release/*
