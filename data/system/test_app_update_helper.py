from __future__ import annotations

import tempfile
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from app_update_helper import extract_release_archive, install_update, validate_staged_package


def _write_release_archive(path: Path, version: str = "0.2.0") -> None:
    entries = {
        "SkiErgPortal.exe": b"new app",
        "version.txt": version.encode("ascii"),
        "SkiErgPortalUpdater.exe": b"updater",
        "streamlit_server/streamlit_server.exe": b"server",
        "streamlit_server/app/app.py": b"app",
        "streamlit_server/streamlit/static/index.html": b"html",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            archive.writestr(f"SkiErgPortal/{name}", content)


class _RunningProcess:
    def poll(self) -> None:
        return None


class SafeExtractTests(unittest.TestCase):
    def test_extracts_only_the_application_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("SkiErgPortal/SkiErgPortal.exe", b"app")
            extracted = extract_release_archive(archive_path, root / "staging")
            self.assertEqual((extracted / "SkiErgPortal.exe").read_bytes(), b"app")

    def test_rejects_parent_directory_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("SkiErgPortal/../../escape.txt", b"outside")
            with self.assertRaises(ValueError):
                extract_release_archive(archive_path, root / "staging")
            self.assertFalse((root / "escape.txt").exists())

    def test_rejects_files_outside_expected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("other-app/file.txt", b"outside")
            with self.assertRaises(ValueError):
                extract_release_archive(archive_path, root / "staging")

    def test_rejects_installation_path_that_overlaps_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "SkiErgPortal"
            install.mkdir()
            data_dir = install / "Data"
            data_dir.mkdir()
            with self.assertRaisesRegex(ValueError, "Brukerdata"):
                install_update(install, root / "missing.zip", "", "0.2.0", 1, data_dir)

    def test_validates_complete_staged_release_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app_root = Path(temporary) / "SkiErgPortal"
            required_files = (
                "SkiErgPortal.exe",
                "version.txt",
                "SkiErgPortalUpdater.exe",
                "streamlit_server/streamlit_server.exe",
                "streamlit_server/app/app.py",
                "streamlit_server/streamlit/static/index.html",
            )
            for name in required_files:
                path = app_root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("0.2.0" if name == "version.txt" else "test", encoding="utf-8")

            validate_staged_package(app_root, "0.2.0")
            with self.assertRaisesRegex(ValueError, "forventet 0.3.0"):
                validate_staged_package(app_root, "0.3.0")

    def test_successful_install_replaces_app_and_keeps_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "SkiErgPortal"
            install.mkdir()
            (install / "old.txt").write_text("old", encoding="utf-8")
            data_dir = root / "LocalAppData" / "SkiErgPortal" / "Data"
            data_dir.mkdir(parents=True)
            (data_dir / "training.csv").write_text("preserve", encoding="utf-8")
            archive = root / "release.zip"
            _write_release_archive(archive)
            package_hash = sha256(archive.read_bytes()).hexdigest()
            with (
                patch("app_update_helper._wait_for_process"),
                patch("app_update_helper.subprocess.run", return_value=CompletedProcess([], 0)),
                patch("app_update_helper.subprocess.Popen", return_value=_RunningProcess()),
                patch("app_update_helper.time.sleep"),
            ):
                install_update(install, archive, package_hash, "0.2.0", 123, data_dir)
            self.assertTrue((install / "SkiErgPortal.exe").is_file())
            self.assertFalse((install / "old.txt").exists())
            self.assertEqual((data_dir / "training.csv").read_text(encoding="utf-8"), "preserve")
            self.assertFalse(archive.exists())

    def test_failed_new_version_restores_previous_app(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "SkiErgPortal"
            install.mkdir()
            (install / "old.txt").write_text("old", encoding="utf-8")
            data_dir = root / "LocalAppData" / "SkiErgPortal" / "Data"
            data_dir.mkdir(parents=True)
            archive = root / "release.zip"
            _write_release_archive(archive)
            package_hash = sha256(archive.read_bytes()).hexdigest()
            with (
                patch("app_update_helper._wait_for_process"),
                patch("app_update_helper.subprocess.run", return_value=CompletedProcess([], 1)),
            ):
                with self.assertRaisesRegex(RuntimeError, "smoke-test feilet"):
                    install_update(install, archive, package_hash, "0.2.0", 123, data_dir)
            self.assertEqual((install / "old.txt").read_text(encoding="utf-8"), "old")
            self.assertFalse((install / "SkiErgPortal.exe").exists())
            self.assertTrue(archive.exists())


if __name__ == "__main__":
    unittest.main()