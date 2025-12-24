"""
Rule Registry.

Central registry for all rules and profiles.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from .loader import load_profiles_from_directory, load_rules_from_directory
from .models import Profile, Rule, Severity

if TYPE_CHECKING:
    pass


class RuleRegistry:
    """
    Central registry for all rules.

    Loads rules from:
    1. Built-in YAML files
    2. Python plugin entry points
    3. Custom rule directories
    """

    def __init__(self) -> None:
        self.rules: dict[str, Rule] = {}
        self.profiles: dict[str, Profile] = {}
        self._loaded = False

    def register_rule(self, rule: Rule) -> None:
        """Register a rule."""
        self.rules[rule.id] = rule

    def register_profile(self, profile: Profile) -> None:
        """Register a profile."""
        self.profiles[profile.id] = profile

    def get_rule(self, rule_id: str) -> Rule | None:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def get_profile(self, profile_id: str) -> Profile | None:
        """Get a profile by ID."""
        return self.profiles.get(profile_id)

    def get_rules_for_profile(self, profile: Profile) -> list[Rule]:
        """
        Get rules enabled by profile, with overrides applied.

        Handles:
        - Glob patterns in enable/disable
        - Severity overrides
        - Profile inheritance via base
        """
        # Resolve inheritance
        resolved_profile = self._resolve_profile(profile)

        # Filter rules by enable/disable patterns
        enabled_rules: list[Rule] = []

        for rule in self.rules.values():
            if rule.deprecated:
                continue

            # Check if rule matches any enable pattern
            matches_enable = any(
                fnmatch.fnmatch(rule.id, pattern) for pattern in resolved_profile.enable
            )

            # Check if rule matches any disable pattern
            matches_disable = any(
                fnmatch.fnmatch(rule.id, pattern) for pattern in resolved_profile.disable
            )

            # Check if explicitly disabled in overrides
            explicitly_disabled = rule.id in resolved_profile.overrides.disabled

            if matches_enable and not matches_disable and not explicitly_disabled:
                # Apply severity override if present
                if rule.id in resolved_profile.overrides.severity:
                    severity_str = resolved_profile.overrides.severity[rule.id]
                    try:
                        new_severity = Severity(severity_str)
                        # Create new rule with overridden severity
                        rule = Rule(
                            id=rule.id,
                            version=rule.version,
                            title=rule.title,
                            stage=rule.stage,
                            severity=new_severity,
                            applies_to=rule.applies_to,
                            selector=rule.selector,
                            constraint=rule.constraint,
                            message=rule.message,
                            docs_url=rule.docs_url,
                            fix=rule.fix,
                            tags=rule.tags,
                            deprecated=rule.deprecated,
                        )
                    except ValueError:
                        pass

                enabled_rules.append(rule)

        return enabled_rules

    def _resolve_profile(self, profile: Profile) -> Profile:
        """Resolve profile inheritance."""
        if not profile.base:
            return profile

        base = self.get_profile(profile.base)
        if not base:
            return profile

        # Recursively resolve base
        resolved_base = self._resolve_profile(base)

        # Merge: profile overrides base
        merged_enable = resolved_base.enable + [
            p for p in profile.enable if p not in resolved_base.enable
        ]
        merged_disable = resolved_base.disable + [
            p for p in profile.disable if p not in resolved_base.disable
        ]

        merged_severity = {**resolved_base.overrides.severity, **profile.overrides.severity}
        merged_params = {**resolved_base.overrides.params, **profile.overrides.params}
        merged_disabled = list(
            set(resolved_base.overrides.disabled) | set(profile.overrides.disabled)
        )

        from .models import ProfileOverrides

        return Profile(
            id=profile.id,
            version=profile.version,
            label=profile.label,
            base=None,  # Already resolved
            enable=merged_enable,
            disable=merged_disable,
            overrides=ProfileOverrides(
                severity=merged_severity,
                params=merged_params,
                disabled=merged_disabled,
            ),
        )

    def load_builtin(self) -> None:
        """Load built-in rules from package."""
        if self._loaded:
            return

        # Find the package rules directory
        package_dir = Path(__file__).parent.parent.parent
        rules_dir = package_dir / "rules"
        profiles_dir = rules_dir / "profiles"

        # Load rules
        if rules_dir.exists():
            rules = load_rules_from_directory(rules_dir)
            for rule in rules:
                self.register_rule(rule)

        # Load profiles
        if profiles_dir.exists():
            profiles = load_profiles_from_directory(profiles_dir)
            for profile in profiles:
                self.register_profile(profile)

        self._loaded = True

    def load_from_directory(self, directory: Path) -> None:
        """Load rules and profiles from a custom directory."""
        rules = load_rules_from_directory(directory)
        for rule in rules:
            self.register_rule(rule)

        profiles_dir = directory / "profiles"
        if profiles_dir.exists():
            profiles = load_profiles_from_directory(profiles_dir)
            for profile in profiles:
                self.register_profile(profile)


# Global registry instance
_registry: RuleRegistry | None = None


def get_registry() -> RuleRegistry:
    """Get the global rule registry."""
    global _registry
    if _registry is None:
        _registry = RuleRegistry()
        _registry.load_builtin()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None
