# Security Policy

## Reporting a vulnerability

Please report security issues privately.

- If this repository is hosted on GitHub: use **Security Advisories** (preferred) so maintainers can coordinate a fix before public disclosure.
- Do not open a public issue for suspected vulnerabilities.

## Supported versions

Security fixes are provided for the latest released version. Enterprises should pin and regularly update dependencies.

## Supply chain hardening

- Pin GitHub Actions to immutable SHAs (helper: `scripts/pin_github_actions.py`).
- Review SBOM and provenance attestations attached to releases.
