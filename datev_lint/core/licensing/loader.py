"""
License loading from filesystem.

Searches for license files in standard locations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from datev_lint.core.licensing.models import FREE_LICENSE, License
from datev_lint.core.licensing.verifier import LicenseVerifier, VerificationError


# License file names to search for
LICENSE_FILE_NAMES = [
    ".datev-lint-license.json",
    "datev-lint-license.json",
    ".datev-lint.license",
]


def get_license_search_paths() -> list[Path]:
    """
    Get paths to search for license files.

    Returns:
        List of directories to search (in priority order)
    """
    paths: list[Path] = []

    # 1. Current directory
    paths.append(Path.cwd())

    # 2. User home directory
    home = Path.home()
    paths.append(home)
    paths.append(home / ".config" / "datev-lint")

    # 3. System config (Windows/Unix)
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "datev-lint")
    else:
        paths.append(Path("/etc/datev-lint"))

    # 4. Environment variable
    env_path = os.environ.get("DATEV_LINT_LICENSE_PATH")
    if env_path:
        paths.insert(0, Path(env_path).parent)

    return paths


def find_license_file() -> Path | None:
    """
    Find a license file in standard locations.

    Returns:
        Path to license file, or None if not found
    """
    # Check environment variable first
    env_path = os.environ.get("DATEV_LINT_LICENSE_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Search standard paths
    for search_dir in get_license_search_paths():
        for filename in LICENSE_FILE_NAMES:
            license_path = search_dir / filename
            if license_path.exists():
                return license_path

    return None


class LicenseLoader:
    """Loads and caches licenses."""

    def __init__(self, verifier: LicenseVerifier | None = None):
        """
        Initialize loader.

        Args:
            verifier: LicenseVerifier to use. Creates default if None.
        """
        self._verifier = verifier or LicenseVerifier()
        self._cached_license: License | None = None
        self._cache_path: Path | None = None

    def load(self, path: Path | None = None) -> License:
        """
        Load license from file or search for one.

        Args:
            path: Explicit license path, or None to search

        Returns:
            License object (FREE_LICENSE if none found)
        """
        # Check cache
        if path is None and self._cached_license is not None:
            return self._cached_license

        # Find license file
        if path is None:
            path = find_license_file()

        if path is None:
            return FREE_LICENSE

        # Check cache for this path
        if self._cache_path == path and self._cached_license is not None:
            return self._cached_license

        # Load and verify
        try:
            license_obj = self._verifier.verify_file(path)
            self._cached_license = license_obj
            self._cache_path = path
            return license_obj
        except VerificationError:
            # Return free license on verification failure
            return FREE_LICENSE

    def reload(self) -> License:
        """Force reload of license file."""
        self._cached_license = None
        self._cache_path = None
        return self.load()


# Global loader instance
_loader: LicenseLoader | None = None


def get_loader() -> LicenseLoader:
    """Get global license loader."""
    global _loader
    if _loader is None:
        _loader = LicenseLoader()
    return _loader


def get_license(path: Path | None = None) -> License:
    """
    Get the current license.

    Args:
        path: Explicit license path, or None to search

    Returns:
        License object
    """
    return get_loader().load(path)


def reset_license_cache() -> None:
    """Reset the license cache (for testing)."""
    global _loader
    _loader = None
