#!/usr/bin/env python3
import argparse
import os
import subprocess

dry_run = False


def hub(*args, check=True):
    args = ["hub"] + list(args)
    if dry_run:
        print("Would run", " ".join(args))
        return
    return subprocess.run(args, check=check)


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
    parser.add_argument("--title", help="title for release", required=True)
    parser.add_argument("--tag", help="tag for release", required=True)
    parser.add_argument(
        "--dry-run",
        help="don't actually run the hub command",
        action="store_true",
    )
    parser.add_argument("--artifacts", help="directory of artifacts to upload")
    parser.add_argument(
        "--prerelease", help="mark release as prerelease", action="store_true"
    )
    parser.add_argument(
        "--draft", help="mark release as draft", action="store_true"
    )
    parser.add_argument(
        "--exclude-tag", help="exclude tag from consideration for git describe"
    )

    args = parser.parse_args()

    # If we try to include this with every call, we will miss one
    global dry_run
    dry_run = args.dry_run

    revision = git_describe(exclude=args.exclude_tag)
    message = args.title + " " + revision

    hub("release", "delete", args.tag, check=False)

    hub_args = ["release", "create", "-m", message, "--draft"]
    if args.prerelease:
        hub_args += ["--prerelease=true"]
    hub_args += [args.tag]
    hub(*hub_args)

    if args.artifacts:
        for file in os.listdir(args.artifacts):
            file = os.path.join(args.artifacts, file)
            hub("release", "edit", "-m", "", "-a", file, args.tag)

    if not args.draft:
        hub("release", "edit", "-m", "", "--draft=false", args.tag)


main()
