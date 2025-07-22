# Tests for CLI commands in aurora-biologic
# Most require Biologic hardware to run, only help command is tested here

import subprocess

class TestCLI:
    """Test the CLI commands."""

    def test_biologic_help(self) -> None:
        """Test CLI help output"""
        result = subprocess.run(
            "biologic --help",
            capture_output=True,
            text=True,
        )
        print(result)

        # Assert it runs without crashing
        assert result.returncode == 0, f"CLI exited with {result.returncode}. Stderr: {result.stderr}"

        # Check expected help text output
        assert "usage" in result.stdout.lower(), "Help output missing expected content"
