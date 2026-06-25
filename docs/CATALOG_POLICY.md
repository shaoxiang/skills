# ROSClaw Skills Catalog Policy

## Goal

The ROSClaw Skills Catalog is a curated GitHub-based source of installable Skills for ROSClaw agents and robots.

## Hosting Policy

ROSClaw.io does not host Skill tarballs by default.

The canonical source of official Skills is:

```text
https://github.com/ros-claw/skills
```

Skill Hub stores metadata, status, and installation references.

## Authentication Policy

Public Skill installation requires no ROSClaw API key.

`ROSCLAW_ADMIN_API_KEY` is only used by official automation, such as GitHub Actions syncing this catalog to ROSClaw.io.

## Skill Status

A Skill may have one of the following states:

* `draft`
* `candidate`
* `source_verified`
* `ci_passed`
* `official_verified`
* `installable`
* `broken`
* `deprecated`
* `revoked`

## Official Skill Requirements

A Skill is official only when:

1. It exists in this repository.
2. Validation passes.
3. A maintainer approves it.
4. It is merged into the default branch.
5. The registry includes it.
6. The Hub sync marks it as official.

## Revocation

A Skill may be revoked if:

* it contains unsafe behavior
* it bypasses sandbox checks
* its GitHub source disappears
* it includes secrets
* it causes physical safety regressions
* it violates license or data policy
