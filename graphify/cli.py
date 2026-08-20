"""Command-line interface for graphify"""

import sys
from typing import Optional

from graphify.installer import WindowsInstaller


class GraphifyCLI:
    """Main CLI class for graphify commands"""

    SUPPORTED_PLATFORMS = ["windows", "linux", "macos"]

    def __init__(self):
        """Initialize GraphifyCLI"""
        self.platform_name = None

    def handle_install(self, platform_name: Optional[str] = None) -> None:
        """Handle the install command

        Args:
            platform_name: Target platform ('windows', 'linux', 'macos')

        Raises:
            ValueError: If platform is not provided or unsupported
        """
        if platform_name is None:
            raise ValueError("Platform is required for install command")

        platform_lower = platform_name.lower()
        if platform_lower not in self.SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform '{platform_name}'. "
                f"Supported: {', '.join(self.SUPPORTED_PLATFORMS)}"
            )

        if platform_lower == "windows":
            installer = WindowsInstaller()
            installer.install()
            print(f"✓ Graphify installation complete for {platform_name}")
        else:
            print(f"Platform '{platform_name}' support coming soon")

    def main(self, args: Optional[list] = None) -> int:
        """Main entry point for CLI

        Args:
            args: Command-line arguments (defaults to sys.argv[1:])

        Returns:
            Exit code (0 for success, 1 for error)
        """
        if args is None:
            args = sys.argv[1:]

        try:
            if not args:
                self.print_help()
                return 0

            command = args[0]

            if command == "install":
                if len(args) < 2:
                    print("Error: install requires --platform argument")
                    return 1

                platform_arg = args[1]
                if not platform_arg.startswith("--platform"):
                    print("Error: expected --platform argument")
                    return 1

                if platform_arg == "--platform":
                    if len(args) < 3:
                        print("Error: --platform requires a value")
                        return 1
                    platform_name = args[2]
                else:
                    platform_name = platform_arg.split("=", 1)[1]

                self.handle_install(platform_name=platform_name)
                return 0

            else:
                print(f"Error: Unknown command '{command}'")
                self.print_help()
                return 1

        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Fatal error: {e}")
            return 1

    @staticmethod
    def print_help() -> None:
        """Print help message"""
        help_text = """
Graphify - Installation and setup tool

Usage:
    graphify <command> [options]

Commands:
    install          Install graphify for a specific platform

Options for install:
    --platform       Target platform (windows, linux, macos)

Examples:
    graphify install --platform windows
    graphify install --platform linux
"""
        print(help_text)


def main() -> int:
    """Entry point for graphify command"""
    cli = GraphifyCLI()
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())
