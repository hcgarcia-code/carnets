"""Installation and setup logic for graphify"""

import platform
import subprocess  # nosec: B404
import sys
from pathlib import Path


class WindowsInstaller:
    """Handle Windows-specific installation"""

    def __init__(self):
        """Initialize WindowsInstaller"""
        self.base_dir = Path.cwd()
        self.is_windows = platform.system() == "Windows"
        self.python_exe = sys.executable

    def create_venv(self) -> None:
        """Create Python virtual environment"""
        venv_path = self.base_dir / "venv"

        if venv_path.exists():
            print("✓ Virtual environment already exists")
            return

        print("Creating virtual environment...")
        # Use list instead of shell=True for safety
        subprocess.run(  # noqa: S603  # nosec
            [self.python_exe, "-m", "venv", str(venv_path)], check=True
        )
        print("✓ Virtual environment created")

    def create_env_file(self) -> None:
        """Create .env file from .env.example"""
        env_file = self.base_dir / ".env"
        env_example = self.base_dir / ".env.example"

        if env_file.exists():
            print("✓ .env file already exists")
            return

        if not env_example.exists():
            print("Warning: .env.example not found, creating minimal .env")
            env_file.write_text(
                "SECRET_KEY=changeme\n"
                "DEBUG=False\n"
                "ALLOWED_HOSTS=localhost,127.0.0.1\n"
            )
            return

        print("Creating .env file from .env.example...")
        env_content = env_example.read_text()
        env_file.write_text(env_content)
        print("✓ .env file created (update with your values)")

    def install_requirements(self) -> None:
        """Install Python dependencies"""
        requirements_file = self.base_dir / "requirements.txt"

        if not requirements_file.exists():
            print("Warning: requirements.txt not found")
            return

        print("Installing Python dependencies...")
        if self.is_windows:
            pip_exe = self.base_dir / "venv" / "Scripts" / "pip.exe"
        else:
            pip_exe = self.base_dir / "venv" / "bin" / "pip"

        # Use list instead of shell=True for safety
        subprocess.run(  # noqa: S603  # nosec
            [str(pip_exe), "install", "-r", str(requirements_file)], check=True
        )
        print("✓ Dependencies installed")

    def validate_setup(self) -> bool:
        """Validate the installation setup"""
        print("Validating setup...")

        checks = [
            (self.base_dir / ".env", ".env file exists"),
            (self.base_dir / "requirements.txt", "requirements.txt exists"),
            (self.base_dir / "venv", "Virtual environment exists"),
        ]

        all_valid = True
        for path, description in checks:
            if path.exists():
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description}")
                all_valid = False

        return all_valid

    def install(self) -> None:
        """Execute the full installation process"""
        print(f"Starting graphify installation for {platform.system()}...")

        try:
            self.create_venv()
            self.create_env_file()
            self.install_requirements()

            if self.validate_setup():
                print("\n✓ Installation successful!")
                print("Next steps:")
                print("  1. Activate virtual environment:")
                if self.is_windows:
                    print("     .\\venv\\Scripts\\activate")
                else:
                    print("     source venv/bin/activate")
                print("  2. Update .env with your configuration")
                print("  3. Run: pytest tests/ -v")
            else:
                print("\nWarning: Some checks failed. Please review the output above.")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Installation failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during installation: {e}") from e
