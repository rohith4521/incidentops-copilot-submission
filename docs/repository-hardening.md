# Repository Hardening Contract

The repository is designed so that code quality and security checks can become merge-enforced controls.

## Required GitHub settings

Repository administrators should configure a ruleset/protection policy for main with:

- Pull request required before merge
- Required status checks for backend CI, frontend quality gate, CodeQL and dependency review
- Required CODEOWNER review
- Dismiss stale approvals when new commits are pushed
- Require conversation resolution
- Block force pushes
- Block branch deletion
- Restrict who can push directly to main
- Require linear history where compatible with the team's workflow
- Require signed commits if the team adopts verified signing

## Security settings

Enable and verify:

- Dependabot security updates/alerts
- Secret scanning
- Push protection
- Code scanning / CodeQL
- Dependency graph

## Why this is separate from repository code

These controls are GitHub repository configuration, not files committed to the repository. A workflow can exist without being a required merge check, and CODEOWNERS can exist without being enforced by branch rules.

Therefore this repository documents the required state rather than falsely claiming that the GitHub-side policy has been enabled.

## Review standard

A change should be considered mergeable only when:

~~~text
Code -> tests -> security scans -> review -> protected merge
~~~

The goal is enforcement, not the appearance of enforcement.
