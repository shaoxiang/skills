# Contributing ROSClaw Skills

Thank you for contributing to the ROSClaw Skills Catalog.

This repository is the official catalog of installable ROSClaw Skills. To keep the ecosystem reliable and safe, every Skill must be submitted through a pull request and pass automated validation.

## Contribution Modes

### 1. Add a new Skill

Create a directory:

```text
skills/<skill_name>/
```

Required files:

```text
SKILL.md
README.md
skill.yaml
behavior_tree.xml
providers.yaml
e-urdf-compat.yaml
safety.yaml
dojo.yaml
darwin_eval.yaml
lineage.yaml
```

Recommended files:

```text
prompts/
policies/
tests/
evidence/
checksums.json
```

### 2. Update an existing Skill

Update the Skill directory and bump the version in:

```text
skill.yaml
lineage.yaml
CHANGELOG.md
```

### 3. Report a broken Skill

Open an issue using the `broken_skill` template.

## Validation

Before opening a PR, run:

```bash
python scripts/validate_skill.py skills/<skill_name>
python scripts/build_registry.py
python scripts/verify_install.py skills/<skill_name>
```

## Safety Rules

The following are not allowed:

* hard-coded API keys
* private tokens
* absolute local paths such as `/data/...` or `/home/...`
* disabling sandbox checks
* default unguarded real-robot execution
* missing `safety.yaml`
* missing compatible robot constraints
* prompt instructions that bypass safety
* large binary artifacts without external references

## Official Status

A Skill is official only after the PR is merged by a maintainer and the generated registry is synchronized to the ROSClaw Skill Hub.

Opening a PR does not automatically mean the Skill is official.

## Large Files

Do not commit large MCAP files, videos, datasets, or model checkpoints directly.

Use external references:

```yaml
artifacts:
  checkpoint:
    uri: "https://..."
    sha256: "..."
```

## Pull Request Checklist

* [ ] Skill directory is under `skills/<skill_name>/`
* [ ] `skill.yaml` is valid
* [ ] `SKILL.md` exists
* [ ] `README.md` exists
* [ ] `safety.yaml` exists
* [ ] `e-urdf-compat.yaml` exists
* [ ] `lineage.yaml` exists
* [ ] No secrets are included
* [ ] No local machine paths are included
* [ ] Installation dry-run passes
* [ ] Version is bumped if updating an existing Skill
