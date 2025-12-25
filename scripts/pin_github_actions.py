from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_USES_RE = re.compile(r"^(?P<indent>\s*)uses:\s*(?P<action>\S+?)@(?P<ref>\S+)\s*$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class UsesRef:
    action: str
    ref: str


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "datev-lint-pin-github-actions",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _resolve_ref_to_sha(uses: UsesRef, token: str | None) -> str:
    if uses.action.startswith("./") or uses.action.startswith("docker://"):
        raise ValueError(f"Unsupported action reference: {uses.action}")

    parts = uses.action.split("/")
    if len(parts) < 2:
        raise ValueError(f"Unsupported action reference: {uses.action}")

    owner, repo = parts[0], parts[1]
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{uses.ref}"

    request = urllib.request.Request(url, headers=_github_headers(token))  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))

    sha = payload.get("sha")
    if not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
        raise ValueError(f"Failed to resolve {uses.action}@{uses.ref} to a commit SHA")

    return sha


def _pin_file(path: Path, token: str | None, dry_run: bool) -> tuple[bool, list[str]]:
    changed = False
    output: list[str] = []
    cache: dict[UsesRef, str] = {}

    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = _USES_RE.match(line.rstrip("\n").rstrip("\r"))
        if not match:
            output.append(line)
            continue

        indent = match.group("indent")
        action = match.group("action")
        ref = match.group("ref")

        if action.startswith("./") or action.startswith("docker://") or "/" not in action:
            output.append(line)
            continue

        if _SHA_RE.fullmatch(ref):
            output.append(line)
            continue

        uses = UsesRef(action=action, ref=ref)
        if uses not in cache:
            cache[uses] = _resolve_ref_to_sha(uses, token)
        sha = cache[uses]

        newline = "\n"
        if line.endswith("\r\n"):
            newline = "\r\n"

        output.append(f"{indent}uses: {action}@{sha} # {ref}{newline}")
        changed = True

    if changed and not dry_run:
        path.write_text("".join(output), encoding="utf-8")

    return changed, output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pin GitHub Actions 'uses:' references in workflow YAML files to immutable commit SHAs."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[".github/workflows"],
        help="Workflow file(s) or directory (default: .github/workflows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not modify files; print updated content to stdout.",
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable name holding a GitHub token (default: GITHUB_TOKEN).",
    )

    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env)

    workflow_files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            workflow_files.extend(sorted(p.rglob("*.yml")))
            workflow_files.extend(sorted(p.rglob("*.yaml")))
        else:
            workflow_files.append(p)

    if not workflow_files:
        print("No workflow files found.", file=sys.stderr)
        return 2

    any_changed = False
    for file_path in workflow_files:
        try:
            changed, rendered = _pin_file(file_path, token=token, dry_run=args.dry_run)
        except urllib.error.HTTPError as e:
            print(f"{file_path}: failed to resolve actions ({e.code})", file=sys.stderr)
            return 2
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"{file_path}: {e}", file=sys.stderr)
            return 2

        if changed:
            any_changed = True
            print(f"Pinned: {file_path}")
            if args.dry_run:
                print("".join(rendered))

    if not any_changed:
        print("No changes needed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
