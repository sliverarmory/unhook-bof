#!/usr/bin/env python3
"""Fail a tag release before key access unless GitHub protections are active."""

import argparse
import fnmatch
import json
import subprocess


def api(path: str) -> object:
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"Cannot read {path}; release controls are not verified")
    return json.loads(result.stdout)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def matches(pattern: str, ref: str) -> bool:
    return pattern == "~ALL" or fnmatch.fnmatchcase(ref, pattern)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--tag-bypass-reviewed", action="store_true",
                        help="confirm the listed bypass actors can create version tags only when authorized")
    parser.add_argument("--environment-bypass-reviewed", action="store_true",
                        help="confirm environment administrator bypass is disabled in repository settings")
    args = parser.parse_args()
    repository = args.repository
    ref = f"refs/tags/{args.tag}"

    environment = api(f"repos/{repository}/environments/armory-release")
    rules = environment.get("protection_rules", [])
    require(any(rule.get("type") == "required_reviewers" and rule.get("reviewers")
                and rule.get("prevent_self_review") is True
                for rule in rules),
            "armory-release needs a required reviewer with self-review disabled")
    policy = environment.get("deployment_branch_policy") or {}
    require(policy.get("custom_branch_policies") is True,
            "armory-release must use custom deployment branch/tag policies")
    policies = api(f"repos/{repository}/environments/armory-release/deployment-branch-policies")
    allowed = policies.get("deployment_branch_policies", [])
    require(allowed and all(item.get("type") == "tag" and item.get("name") == "v*"
                            for item in allowed),
            "armory-release must admit only version tags through a v* tag policy")

    branch = api(f"repos/{repository}/branches/master")
    require(branch.get("protected") is True, "master must be protected")
    effective = api(f"repos/{repository}/rules/branches/master")
    require(any(rule.get("type") == "pull_request" and
                (rule.get("parameters") or {}).get("required_approving_review_count", 0) >= 1
                for rule in effective), "master must require at least one pull request approval")
    status_rules = [rule for rule in effective if rule.get("type") == "required_status_checks"]
    checks = {
        check.get("context", ""): check.get("integration_id")
        for rule in status_rules
        for check in (rule.get("parameters") or {}).get("required_status_checks", [])
    }
    required_contexts = {
        "e2e / Plan target matrix",
        "e2e / windows/amd64",
        "e2e / windows/386",
        "e2e / Aggregate results",
        "Build and validate unsigned package",
    }
    require(required_contexts <= checks.keys(),
            f"master required checks missing: {sorted(required_contexts - checks.keys())}")
    require(all(checks[context] == 15368 for context in required_contexts),
            "required checks must be bound to the GitHub Actions app (integration_id 15368)")

    summaries = api(f"repos/{repository}/rulesets?includes_parents=true")
    protected = False
    bypass_actors = []
    for summary in summaries:
        if summary.get("target") != "tag" or summary.get("enforcement") != "active":
            continue
        detail = api(f"repos/{repository}/rulesets/{summary['id']}")
        names = (detail.get("conditions") or {}).get("ref_name") or {}
        included = any(matches(item, ref) for item in names.get("include", []))
        excluded = any(matches(item, ref) for item in names.get("exclude", []))
        rule_types = {item.get("type") for item in detail.get("rules", [])}
        if included and not excluded and {"creation", "update", "deletion"} <= rule_types:
            protected = True
            bypass_actors = detail.get("bypass_actors", [])
            break
    require(protected, f"{ref} needs an active creation/update/deletion tag ruleset")
    print("Version-tag ruleset bypass actors:", json.dumps(bypass_actors, sort_keys=True))
    require(args.tag_bypass_reviewed,
            "review version-tag bypass actors and rerun with --tag-bypass-reviewed")
    require(args.environment_bypass_reviewed,
            "confirm administrator environment bypass is disabled and rerun with "
            "--environment-bypass-reviewed")
    environment_secrets = api(f"repos/{repository}/environments/armory-release/secrets")
    require(any(item.get("name") == "ARMORY_RELEASE_MINISIGN_PRIVATE_KEY"
                for item in environment_secrets.get("secrets", [])),
            "the signing key must be an armory-release environment-only secret")
    repository_secrets = api(f"repos/{repository}/actions/secrets")
    require(all(item.get("name") not in {
                    "MINISIGN_PRIVATE_KEY", "ARMORY_RELEASE_MINISIGN_PRIVATE_KEY"
                }
                for item in repository_secrets.get("secrets", [])),
            "remove every repository-scoped signing key; keep only the environment secret")
    immutable = api(f"repos/{repository}/immutable-releases")
    require(immutable.get("enabled") is True, "immutable releases must be enabled")
    print("Release environment, master, version-tag, key-scope, and immutability controls verified")


if __name__ == "__main__":
    main()
