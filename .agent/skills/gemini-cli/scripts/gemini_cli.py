#!/usr/bin/env python3
"""Gemini CLI wrapper for safe, automated AI code assistance.

This script provides a safe interface to the Gemini CLI (npx gemini) with:
- Automatic secret detection and redaction
- Token limit handling and file summarization
- Task-specific prompt templates
- Diff generation and validation
- Integration with Home Assistant development workflows
"""

import argparse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
import subprocess
import sys


class TaskType(Enum):
    """Available Gemini CLI task types."""

    EXPLAIN = "explain"
    TEST = "test"
    REFACTOR = "refactor"
    DOC = "doc"
    DEBUG = "debug"
    MIGRATE = "migrate"


@dataclass
class GeminiConfig:
    """Configuration for Gemini CLI execution."""

    file_path: Path | None = None
    task: TaskType = TaskType.EXPLAIN
    framework: str = "pytest"
    issue: str = ""
    error: str = ""
    context: str = ""
    max_lines: int = 10000
    output_format: str = "code"  # code, diff, markdown
    timeout: int = 120


class SecretDetector:
    """Detects and redacts sensitive information from code."""

    # Patterns for common secrets
    SECRET_PATTERNS = [
        (
            r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "API_KEY",
        ),
        (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]+)['\"]", "PASSWORD"),
        (
            r"(?i)(token|access[_-]token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?",
            "TOKEN",
        ),
        (r"(?i)(secret|secret[_-]key)\s*[:=]\s*['\"]([^'\"]+)['\"]", "SECRET"),
        (r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})", "BEARER_TOKEN"),
        (
            r"(?i)AWS[_-]?ACCESS[_-]?KEY[_-]?ID['\"]?\s*[:=]\s*['\"]?([A-Z0-9]{20})['\"]?",
            "AWS_KEY",
        ),
    ]

    # Files to never send (even if user requests)
    FORBIDDEN_FILES = {
        ".env",
        ".env.local",
        ".env.production",
        "secrets.yaml",
        "secrets.json",
    }

    # Safe file extensions
    SAFE_EXTENSIONS = {
        ".py",
        ".ts",
        ".js",
        ".tsx",
        ".jsx",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".txt",
    }

    @classmethod
    def detect_secrets(cls, content: str) -> list[tuple[str, str]]:
        """Detect secrets in content.

        Args:
            content: File content to scan.

        Returns:
            List of (pattern_match, secret_type) tuples.
        """
        found_secrets = []
        for pattern, secret_type in cls.SECRET_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                found_secrets.append((match.group(0), secret_type))
        return found_secrets

    @classmethod
    def is_safe_file(cls, file_path: Path) -> tuple[bool, str]:
        """Check if file is safe to send to Gemini.

        Args:
            file_path: Path to file to check.

        Returns:
            Tuple of (is_safe, reason_if_unsafe).
        """
        # Check forbidden files
        if file_path.name in cls.FORBIDDEN_FILES:
            return False, f"Forbidden file: {file_path.name}"

        # Check extension
        if file_path.suffix not in cls.SAFE_EXTENSIONS:
            return False, f"Unsafe file extension: {file_path.suffix}"

        return True, ""

    @classmethod
    def sanitize_content(cls, content: str) -> tuple[str, list[str]]:
        """Sanitize content by redacting secrets.

        Args:
            content: Content to sanitize.

        Returns:
            Tuple of (sanitized_content, list_of_redacted_secret_types).
        """
        sanitized = content
        redacted_types = []

        for pattern, secret_type in cls.SECRET_PATTERNS:
            if re.search(pattern, sanitized):
                redacted_types.append(secret_type)
                # Replace the secret value with placeholder
                # Use default argument to bind loop variable
                sanitized = re.sub(
                    pattern,
                    lambda m, st=secret_type: m.group(0).replace(
                        m.group(2), f"[REDACTED_{st}]"
                    ),
                    sanitized,
                )

        return sanitized, redacted_types


class PromptBuilder:
    """Builds task-specific prompts for Gemini CLI."""

    @staticmethod
    def build_system_context(config: GeminiConfig) -> str:
        """Build system context based on file type and project.

        Args:
            config: Gemini configuration.

        Returns:
            System context string.
        """
        context_parts = [
            "You are an expert software engineer integrated into the Antigravity IDE.",
            "Your output must be valid code or Markdown.",
            "Do not include conversational filler.",
            "Focus on efficiency, type safety, and adherence to project standards.",
        ]

        # Add custom context if provided
        if config.context:
            context_parts.append(f"\nAdditional Context: {config.context}")

        # Infer project type from file
        if config.file_path:
            if "custom_components" in str(config.file_path):
                context_parts.append(
                    "\nProject: Home Assistant custom component (Python 3.13+, async, Quality Scale: Silver/Gold)"
                )
            elif "lovelace" in str(config.file_path):
                context_parts.append(
                    "\nProject: Lovelace card (TypeScript, LIT 3.0, Web Components)"
                )

        return "\n".join(context_parts)

    @staticmethod
    def build_task_prompt(config: GeminiConfig, content: str) -> str:
        """Build task-specific prompt.

        Args:
            config: Gemini configuration.
            content: File content.

        Returns:
            Complete prompt string.
        """
        system_context = PromptBuilder.build_system_context(config)

        if config.task == TaskType.EXPLAIN:
            return f"""{system_context}

Task: Explain the logic and flow of this code
Focus: Data flow, async operations, error handling, design patterns

Code:
{content}
"""

        if config.task == TaskType.TEST:
            return f"""{system_context}

Task: Generate comprehensive {config.framework} tests
Requirements:
- Use async fixtures where appropriate
- Mock external API calls
- Cover happy path and error cases
- Follow existing project test patterns
- Include edge cases and boundary conditions

Code to test:
{content}
"""

        if config.task == TaskType.REFACTOR:
            issue_desc = config.issue or "general code quality"
            return f"""{system_context}

Task: Refactor code to address: {issue_desc}
Requirements:
- Maintain current functionality
- Improve code quality (DRY, SOLID principles)
- Preserve type safety
- Follow project coding standards
- Add explanatory comments for significant changes

Code to refactor:
{content}
"""

        if config.task == TaskType.DOC:
            return f"""{system_context}

Task: Add comprehensive documentation
Requirements:
- Add Google-style docstrings to all functions and classes
- Include Args, Returns, Raises sections
- Use American English
- Be concise but comprehensive
- Include type hints in docstrings

Code to document:
{content}
"""

        if config.task == TaskType.DEBUG:
            return f"""{system_context}

Task: Analyze this error and suggest fixes
Error:
{config.error}

Relevant code:
{content}

Provide:
1. Root cause analysis
2. Suggested fix with code
3. Prevention strategies
"""

        if config.task == TaskType.MIGRATE:
            return f"""{system_context}

Task: Migrate this code to modern standards
Requirements:
- Update to latest language features
- Improve type safety
- Maintain functionality
- Follow current best practices

Code to migrate:
{content}
"""

        return f"{system_context}\n\nCode:\n{content}"


class GeminiCLI:
    """Wrapper for Gemini CLI interactions."""

    def __init__(self, config: GeminiConfig) -> None:
        """Initialize Gemini CLI wrapper.

        Args:
            config: Configuration for Gemini execution.
        """
        self.config = config
        self.secret_detector = SecretDetector()

    def _check_file_safety(self) -> None:
        """Check if file is safe to send.

        Raises:
            ValueError: If file is unsafe.
        """
        if not self.config.file_path:
            return

        is_safe, reason = self.secret_detector.is_safe_file(self.config.file_path)
        if not is_safe:
            raise ValueError(f"Unsafe file: {reason}")

    def _read_and_sanitize_file(self) -> tuple[str, list[str]]:
        """Read file and sanitize content.

        Returns:
            Tuple of (sanitized_content, redacted_secret_types).

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        if not self.config.file_path:
            return "", []

        if not self.config.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.config.file_path}")

        content = self.config.file_path.read_text()

        # Check for secrets (log findings to stderr)
        secrets = self.secret_detector.detect_secrets(content)
        if secrets:
            sys.stderr.write(
                f"⚠️  Warning: Found {len(secrets)} potential secrets in file\n"
            )
            for _, secret_type in secrets:
                sys.stderr.write(f"   - {secret_type}\n")
            sys.stderr.write("   Secrets will be redacted before sending\n")

        # Sanitize
        sanitized_content, redacted_types = self.secret_detector.sanitize_content(
            content
        )

        # Check line count (log warning to stderr)
        lines = sanitized_content.count("\n")
        if lines > self.config.max_lines:
            sys.stderr.write(
                f"⚠️  Warning: File has {lines} lines (max: {self.config.max_lines})\n"
            )
            sys.stderr.write("   Consider using --summarize or splitting the file\n")

        return sanitized_content, redacted_types

    def execute(self) -> str:
        """Execute Gemini CLI with configured task.

        Returns:
            Gemini CLI output.

        Raises:
            ValueError: If configuration is invalid.
            subprocess.CalledProcessError: If Gemini CLI fails.
        """
        # Safety checks
        self._check_file_safety()

        # Read and sanitize content
        content, _redacted = self._read_and_sanitize_file()

        # Build prompt
        prompt = PromptBuilder.build_task_prompt(self.config, content)

        # Execute Gemini CLI
        sys.stderr.write(f"🤖 Executing Gemini CLI ({self.config.task.value})...\n")

        try:
            result = subprocess.run(
                ["npx", "gemini", "prompt", prompt],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.config.timeout,
            )

            sys.stderr.write("✅ Gemini CLI execution successful\n")
            return result.stdout

        except subprocess.TimeoutExpired as e:
            sys.stderr.write(
                f"❌ Gemini CLI timed out after {self.config.timeout} seconds\n"
            )
            raise TimeoutError("Gemini CLI timed out") from e
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"❌ Gemini CLI failed with exit code {e.returncode}\n")
            sys.stderr.write(f"Error: {e.stderr}\n")
            raise RuntimeError(f"Gemini CLI failed: {e.stderr}") from e


def main() -> int:
    """Main entry point for Gemini CLI wrapper.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Gemini CLI wrapper for safe AI code assistance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Explain code
  %(prog)s --task explain --file path/to/file.py

  # Generate tests
  %(prog)s --task test --file path/to/file.py --framework pytest

  # Refactor for DRY
  %(prog)s --task refactor --file path/to/file.py --issue "DRY principle"

  # Add documentation
  %(prog)s --task doc --file path/to/file.py

  # Debug error
  %(prog)s --task debug --file path/to/file.py --error "AttributeError: ..."
        """,
    )

    parser.add_argument(
        "--task",
        type=str,
        choices=[t.value for t in TaskType],
        required=True,
        help="Task type",
    )

    parser.add_argument("--file", type=Path, help="File to process")

    parser.add_argument(
        "--framework", type=str, default="pytest", help="Test framework (for test task)"
    )

    parser.add_argument(
        "--issue", type=str, default="", help="Issue to address (for refactor task)"
    )

    parser.add_argument(
        "--error", type=str, default="", help="Error message (for debug task)"
    )

    parser.add_argument(
        "--context", type=str, default="", help="Additional context for Gemini"
    )

    parser.add_argument(
        "--max-lines",
        type=int,
        default=10000,
        help="Maximum lines to send (default: 10000)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds (default: 120)",
    )

    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")

    args = parser.parse_args()

    # Create config
    try:
        config = GeminiConfig(
            file_path=args.file,
            task=TaskType(args.task),
            framework=args.framework,
            issue=args.issue,
            error=args.error,
            context=args.context,
            max_lines=args.max_lines,
            timeout=args.timeout,
        )

        # Execute
        cli = GeminiCLI(config)
        output = cli.execute()

        # Write output
        if args.output:
            args.output.write_text(output)
            sys.stderr.write(f"✅ Output written to {args.output}\n")
        else:
            sys.stdout.write(output)

        return 0

    except (ValueError, FileNotFoundError, TimeoutError, RuntimeError) as e:
        sys.stderr.write(f"❌ Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
