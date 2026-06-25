"""Schema tests for ros_install."""

from pathlib import Path

from rosclaw.skill.models import SkillPackage
from rosclaw.skill.validators import validate_package


def test_skill_package_valid():
    pkg = SkillPackage.load(Path(__file__).parent.parent)
    report = validate_package(pkg)
    assert report.ok, report.errors


def test_readme_has_required_sections():
    from rosclaw.skill.validators import validate_readme

    report = validate_readme(Path(__file__).parent.parent)
    assert report.checks.get("readme_sections"), report.warnings


def test_behavior_tree_has_required_nodes():
    from rosclaw.skill.validators import validate_behavior_tree

    report = validate_behavior_tree(Path(__file__).parent.parent / "behavior_tree.xml")
    assert report.checks.get("behavior_tree_lint"), report.errors
