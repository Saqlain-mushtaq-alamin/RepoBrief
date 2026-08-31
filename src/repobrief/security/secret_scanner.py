"""Regex-based secret/credential detection engine.

Scans file content for patterns that look like API keys, tokens, passwords,
and other credentials. Supports two modes:
- EXCLUDE: mark the file for removal from the digest
- REDACT: replace matched secrets with [REDACTED] in the content
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SecretAction(Enum):
    """What to do when a secret is found."""

    EXCLUDE = "exclude"  # Remove the entire file from output
    REDACT = "redact"  # Replace the secret value with [REDACTED]


@dataclass
class SecretPattern:
    """A single secret detection pattern.

    Attributes:
        name: Human-readable name (e.g., "AWS Access Key").
        pattern: Compiled regex pattern.
        description: Short description for reports.
    """

    name: str
    pattern: re.Pattern
    description: str


@dataclass
class SecretFinding:
    """A single secret found in a file.

    Attributes:
        file_path: Relative path to the file containing the secret.
        line_number: 1-indexed line number where the secret was found.
        pattern_name: Name of the pattern that matched.
        matched_text: The text that matched (truncated for safety in reports).
        description: Human-readable description of the finding.
    """

    file_path: Path
    line_number: int
    pattern_name: str
    matched_text: str  # First 20 chars + "..." for safety
    description: str


@dataclass
class ScanResult:
    """Result of scanning a file for secrets.

    Attributes:
        has_secrets: True if any secrets were found.
        findings: List of individual secret findings.
        redacted_content: If action=REDACT, the content with secrets replaced.
    """

    has_secrets: bool = False
    findings: list[SecretFinding] = field(default_factory=list)
    redacted_content: str | None = None


# -- Pattern Definitions -------------------------------------------------------


def _build_patterns() -> list[SecretPattern]:
    """Build the list of secret detection patterns.

    Returns:
        List of compiled SecretPattern objects.
    """
    raw_patterns = [
        # AWS
        (
            "AWS Access Key ID",
            r"(?:^|[^a-zA-Z0-9])AKIA[0-9A-Z]{16}(?:[^a-zA-Z0-9]|$)",
            "AWS IAM access key",
        ),
        # GitHub
        ("GitHub PAT (classic)", r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token (classic)"),
        (
            "GitHub PAT (fine-grained)",
            r"github_pat_[a-zA-Z0-9_]{82}",
            "GitHub fine-grained personal access token",
        ),
        ("GitHub OAuth", r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth access token"),
        # OpenAI / Anthropic
        ("OpenAI API Key", r"sk-[a-zA-Z0-9]{20,}", "OpenAI API key"),
        ("Anthropic API Key", r"sk-ant-[a-zA-Z0-9\-_]{20,}", "Anthropic API key"),
        # Private keys
        (
            "Private Key",
            r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)\s+PRIVATE\s+KEY-----",
            "Private cryptographic key",
        ),
        # Slack
        ("Slack Token", r"xox[bprs]-[0-9a-zA-Z\-]{10,}", "Slack API token"),
        # Stripe
        ("Stripe Secret Key", r"sk_live_[0-9a-zA-Z]{24,}", "Stripe live secret key"),
        ("Stripe Restricted Key", r"rk_live_[0-9a-zA-Z]{24,}", "Stripe live restricted key"),
        # Generic patterns (more prone to false positives -- lower priority)
        (
            "Hardcoded Password",
            r"""(?i)(?:password|passwd|pwd)\s*[=:]\s*["'][^"'\s]{8,}["']""",
            "Hardcoded password in source code",
        ),
        (
            "Generic Secret Assignment",
            r"""(?i)(?:secret|api_key|apikey|api_secret|access_token)\s*[=:]\s*["'][^"'\s]{16,}["']""",
            "Generic secret/token assignment",
        ),
    ]

    return [
        SecretPattern(
            name=name,
            pattern=re.compile(pattern),
            description=desc,
        )
        for name, pattern, desc in raw_patterns
    ]


# Module-level singleton -- patterns are compiled once
SECRET_PATTERNS: list[SecretPattern] = _build_patterns()


# -- .env file handling --------------------------------------------------------

ENV_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
}


def _is_env_file(file_path: Path) -> bool:
    """Check if a file is a .env-style file (always treated as containing secrets)."""
    return file_path.name in ENV_FILE_NAMES


# -- Core scanning logic -------------------------------------------------------


def scan_content_for_secrets(
    content: str,
    file_path: Path,
    action: SecretAction = SecretAction.EXCLUDE,
) -> ScanResult:
    """Scan a file's content for secrets.

    Args:
        content: The text content of the file.
        file_path: Relative path (for reporting).
        action: What to do if secrets are found (EXCLUDE or REDACT).

    Returns:
        ScanResult with findings and optionally redacted content.
    """
    result = ScanResult()

    # .env files are always flagged entirely
    if _is_env_file(file_path):
        result.has_secrets = True
        result.findings.append(
            SecretFinding(
                file_path=file_path,
                line_number=1,
                pattern_name=".env file",
                matched_text="(entire file)",
                description="Environment variable file -- likely contains secrets",
            )
        )
        if action == SecretAction.REDACT:
            # Redact all values in KEY=VALUE lines
            redacted_lines = []
            for line in content.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    key, _, _ = line.partition("=")
                    redacted_lines.append(f"{key}=[REDACTED]")
                else:
                    redacted_lines.append(line)
            result.redacted_content = "\n".join(redacted_lines)
        return result

    # For all other files, check each pattern
    lines = content.splitlines()
    redacted_content = content  # Start with original, replace matches

    for pattern in SECRET_PATTERNS:
        for line_idx, line in enumerate(lines, start=1):
            for match in pattern.pattern.finditer(line):
                result.has_secrets = True
                matched_text = match.group()

                # Truncate for safe reporting
                safe_text = matched_text[:20] + "..." if len(matched_text) > 20 else matched_text

                result.findings.append(
                    SecretFinding(
                        file_path=file_path,
                        line_number=line_idx,
                        pattern_name=pattern.name,
                        matched_text=safe_text,
                        description=pattern.description,
                    )
                )

                if action == SecretAction.REDACT:
                    redacted_content = redacted_content.replace(matched_text, "[REDACTED]")

    if action == SecretAction.REDACT:
        result.redacted_content = redacted_content

    return result


def scan_files_for_secrets(
    files: list,  # List[ScannedFile] -- avoiding circular import
    action: SecretAction = SecretAction.EXCLUDE,
) -> tuple[list, list[SecretFinding]]:
    """Scan a list of ScannedFile objects and return filtered results.

    Args:
        files: List of ScannedFile objects from the scanner.
        action: EXCLUDE (remove files with secrets) or REDACT (replace secret values).

    Returns:
        Tuple of:
        - List of ScannedFile objects (filtered/redacted)
        - List of all SecretFinding objects (for reporting)
    """
    clean_files = []
    all_findings: list[SecretFinding] = []

    for scanned_file in files:
        result = scan_content_for_secrets(
            content=scanned_file.content,
            file_path=scanned_file.relative_path,
            action=action,
        )

        all_findings.extend(result.findings)

        if not result.has_secrets:
            # No secrets -- include as-is
            clean_files.append(scanned_file)
        elif action == SecretAction.REDACT and result.redacted_content is not None:
            # Has secrets, but we're redacting -- include with redacted content
            scanned_file.content = result.redacted_content
            clean_files.append(scanned_file)
        # else: action == EXCLUDE -> drop the file entirely

    return clean_files, all_findings
