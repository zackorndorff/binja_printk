#!/usr/bin/env python3
"""
Make a GitHub release for the binaries we've built.
"""
import argparse
import os
import subprocess


def hub(*args, check=True):
    args = ["hub"] + list(args)
    print("Running command", args)
    result = subprocess.run(args, check=check)
    print("Command returned", result.returncode)
    return result


def git_describe(exclude=""):
    args = ["git", "describe", "--tags"]
    if exclude:
        args += ["--exclude", exclude]
    return (
        subprocess.run(args, check=True, capture_output=True)
        .stdout.decode()
        .strip()
    )


def main():
    parser = argparse.ArgumentParser("Create GitHub Release")
    parser.add_argument(
        "--title",
        help="title for new release, if not already extant or is overwritten",
        required=True,
    )
    parser.add_argument("--tag", help="tag for release", required=True)
    parser.add_argument("--artifacts", help="directory of artifacts to upload")
    parser.add_argument(
        "--prerelease",
        help="if release doesn't already exists or is overwritten, mark new release as prerelease",
        action="store_true",
    )
    parser.add_argument(
        "--exclude-tag", help="exclude tag from consideration for git describe"
    )
    parser.add_argument(
        "--overwrite",
        help="Overwite old release for this tag if it exists, removing description, etc",
        action="store_true",
    )

    args = parser.parse_args()

    if args.overwrite:
        hub("release", "delete", args.tag, check=False)

    exists = hub("release", "show", args.tag, check=False).returncode == 0

    # If the release doesn't already exist (or we removed it to overwrite it),
    # then we'll need to make a new one
    if not exists:
        # Make description from git describe
        revision = git_describe(exclude=args.exclude_tag)
        message = args.title + " " + revision

        hub_args = ["release", "create", "-m", message]
        if args.prerelease:
            hub_args += ["--prerelease=true"]
        hub_args += [args.tag]
        hub(*hub_args)

    # Attach built binaries to the release.
    if args.artifacts:
        for file in os.listdir(args.artifacts):
            file = os.path.join(args.artifacts, file)
            hub("release", "edit", "-m", "", "-a", file, args.tag)


main()
