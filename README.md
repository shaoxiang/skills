# ROSClaw Skills

Official ROSClaw Skills Catalog — versioned, verifiable physical skills for embodied agents.

ROSClaw Skills are reusable physical capabilities for robots and embodied agents. A Skill is not just a prompt or a policy checkpoint. A ROSClaw Skill is a versioned physical asset containing behavior recipes, safety constraints, provider routes, compatible embodiment profiles, evaluation evidence, and lineage.

## What is a ROSClaw Skill?

A Skill may contain:

- `SKILL.md` — agent-readable skill instruction
- `skill.yaml` — skill metadata and runtime contract
- `behavior_tree.xml` — executable behavior structure
- `prompts/` — planner, verifier, recovery, and safety prompts
- `policies/` — policy adapters, parameters, or checkpoints
- `providers.yaml` — model and tool provider routing
- `e-urdf-compat.yaml` — compatible robot embodiments
- `safety.yaml` — runtime safety constraints
- `dojo.yaml` — practice / mining / replay configuration
- `darwin_eval.yaml` — evaluation and promotion gates
- `evidence/` — evaluation summaries and reports
- `lineage.yaml` — origin, version, and promotion history

## Install a Skill

```bash
rosclaw skill install ros-claw/ros_install
```

Install a specific version:

```bash
rosclaw skill install ros-claw/ros_install@0.1.0
```

No ROSClaw API key is required to install public official skills.

## Available Skills

The generated registry is located at:

```text
registry/skills.json
```

Each skill lives under:

```text
skills/<skill_name>/
```

## Contribute a Skill

Submit a pull request adding your skill under:

```text
skills/<your_skill_name>/
```

Your PR must pass:

* schema validation
* required file checks
* safety checks
* secret scanning
* local path scanning
* installation dry-run
* registry generation

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Official Verification

A Skill becomes official only after:

1. It is added to this repository.
2. GitHub Actions validation passes.
3. A maintainer reviews and merges the pull request.
4. The registry is rebuilt.
5. The Skill is synchronized to the ROSClaw Skill Hub.

## Safety Notice

ROSClaw Skills may control or influence physical robots. Every physical Skill must include `safety.yaml`, compatible embodiment constraints, and evaluation evidence. Unsafe, unverifiable, or sandbox-bypassing Skills will be rejected or revoked.

## License

Apache-2.0 unless otherwise specified inside each Skill directory.
