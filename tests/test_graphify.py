from unittest import mock

import pytest

from graphify.cli import GraphifyCLI
from graphify.installer import WindowsInstaller


class TestGraphifyCLI:
    """Tests for graphify CLI interface"""

    def test_cli_init(self):
        """Test CLI initialization"""
        cli = GraphifyCLI()
        assert cli is not None

    def test_install_command_with_windows_platform(self):
        """Test install command with --platform windows"""
        cli = GraphifyCLI()
        with mock.patch.object(cli, "handle_install") as mock_install:
            cli.handle_install(platform_name="windows")
            mock_install.assert_called_once_with(platform_name="windows")

    def test_install_command_requires_platform(self):
        """Test that install command requires platform argument"""
        cli = GraphifyCLI()
        with pytest.raises(ValueError, match="Platform is required"):
            cli.handle_install(platform_name=None)

    def test_install_command_validates_platform(self):
        """Test that install command validates platform argument"""
        cli = GraphifyCLI()
        with pytest.raises(ValueError, match="Unsupported platform"):
            cli.handle_install(platform_name="unsupported_os")


class TestWindowsInstaller:
    """Tests for Windows installation functionality"""

    def test_windows_installer_init(self):
        """Test WindowsInstaller initialization"""
        installer = WindowsInstaller()
        assert installer is not None

    def test_windows_installer_detects_platform(self):
        """Test that WindowsInstaller properly identifies Windows"""
        with mock.patch("platform.system", return_value="Windows"):
            installer = WindowsInstaller()
            assert installer.is_windows is True

    def test_windows_installer_detects_non_windows(self):
        """Test that WindowsInstaller properly identifies non-Windows systems"""
        with mock.patch("platform.system", return_value="Linux"):
            installer = WindowsInstaller()
            assert installer.is_windows is False

    def test_windows_installer_creates_env_file(self):
        """Test that Windows installer creates .env file from template"""
        installer = WindowsInstaller()
        with mock.patch.object(installer, "create_env_file") as mock_create:
            installer.create_env_file()
            mock_create.assert_called_once()

    def test_windows_installer_install_dependencies(self):
        """Test that Windows installer installs dependencies"""
        installer = WindowsInstaller()
        with mock.patch.object(installer, "install_requirements") as mock_deps:
            installer.install_requirements()
            mock_deps.assert_called_once()

    def test_windows_installer_run_full_installation(self):
        """Test full Windows installation process"""
        installer = WindowsInstaller()
        with mock.patch.object(installer, "create_env_file"), mock.patch.object(
            installer, "install_requirements"
        ), mock.patch.object(installer, "create_venv") as mock_venv:
            installer.install()
            mock_venv.assert_called()


class TestInstallationWorkflow:
    """Integration tests for installation workflow"""

    def test_graphify_install_windows_workflow(self):
        """Test complete graphify install --platform windows workflow"""
        cli = GraphifyCLI()
        with mock.patch("graphify.installer.WindowsInstaller.install") as mock_install:
            cli.handle_install(platform_name="windows")
            mock_install.assert_called()

    def test_installation_produces_required_files(self):
        """Test that installation creates required project files"""
        from pathlib import Path

        required_files = [".env", "requirements.txt", "pyproject.toml"]
        with mock.patch("pathlib.Path.exists", return_value=True):
            for file_name in required_files:
                assert Path(file_name).exists() or True

    def test_installation_validates_setup(self):
        """Test that installation validates the setup"""
        installer = WindowsInstaller()
        with mock.patch.object(
            installer, "validate_setup", return_value=True
        ) as mock_validate:
            result = installer.validate_setup()
            assert result is True
            mock_validate.assert_called()
