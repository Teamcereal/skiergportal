from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path, PurePosixPath


_MAX_EXTRACTED_BYTES = 2_000_000_000
_REQUIRED_FILES = (
    "SkiErgPortal.exe",
    "version.txt",
    "SkiErgPortalUpdater.exe",
    "streamlit_server/streamlit_server.exe",
    "streamlit_server/app/app.py",
    "streamlit_server/streamlit/static/index.html",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def extract_release_archive(archive_path: Path, staging_root: Path) -> Path:
    staging_root.mkdir(parents=True, exist_ok=True)
    staging_root = staging_root.resolve()
    seen: set[str] = set()
    total_size = 0

    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            normalized_name = info.filename.replace("\\", "/")
            if normalized_name.startswith("/") or "\x00" in normalized_name:
                raise ValueError("ZIP-en inneholder en ugyldig filsti.")
            raw_parts = normalized_name.rstrip("/").split("/")
            if (
                not raw_parts
                or raw_parts[0] != "SkiErgPortal"
                or any(part in ("", ".", "..") or ":" in part for part in raw_parts)
            ):
                raise ValueError("ZIP-en inneholder en filsti utenfor SkiErgPortal-mappen.")

            relative_name = "/".join(raw_parts)
            if relative_name in seen:
                raise ValueError("ZIP-en inneholder dupliserte filstier.")
            seen.add(relative_name)

            file_type = stat.S_IFMT(info.external_attr >> 16)
            if file_type == stat.S_IFLNK:
                raise ValueError("ZIP-en inneholder symbolske lenker.")

            destination = staging_root.joinpath(*raw_parts)
            if not destination.resolve().is_relative_to(staging_root):
                raise ValueError("ZIP-en inneholder en filsti utenfor staging-mappen.")
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            total_size += info.file_size
            if total_size > _MAX_EXTRACTED_BYTES:
                raise ValueError("ZIP-en er større enn tillatt utpakket størrelse.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("xb") as target:
                shutil.copyfileobj(source, target)

    return staging_root / "SkiErgPortal"


def validate_staged_package(app_root: Path, expected_version: str) -> None:
    missing = [name for name in _REQUIRED_FILES if not (app_root / name).is_file()]
    if missing:
        raise ValueError("Releasepakken mangler nødvendige filer: " + ", ".join(missing))
    actual_version = (app_root / "version.txt").read_text(encoding="ascii").strip()
    if actual_version != expected_version:
        raise ValueError(f"Releasepakken har versjon {actual_version}, forventet {expected_version}.")


def _wait_for_process(process_id: int, timeout_seconds: int = 120) -> None:
    if os.name != "nt":
        raise OSError("Oppdatereren kan bare installere Windows-bygg.")
    synchronize = 0x00100000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    process_handle = kernel32.OpenProcess(synchronize, False, process_id)
    if not process_handle:
        error = ctypes.get_last_error()
        if error == 87:
            return
        raise OSError(error, "Kunne ikke vente på SkiErgPortal-launcheren.")
    try:
        result = kernel32.WaitForSingleObject(process_handle, timeout_seconds * 1000)
        if result == 0x00000102:
            raise TimeoutError("Launcheren avsluttet ikke innen tidsfristen.")
        if result != 0:
            raise OSError(ctypes.get_last_error(), "Ventingen på launcheren feilet.")
    finally:
        kernel32.CloseHandle(process_handle)


def install_update(
    install_dir: Path,
    archive_path: Path,
    expected_sha256: str,
    expected_version: str,
    parent_process_id: int,
    data_dir: Path,
    status_callback: Callable[[str], None] | None = None,
) -> None:
    if status_callback:
        status_callback("Venter pa at SkiErgPortal avslutter …")
    install_dir = install_dir.resolve(strict=True)
    data_dir = data_dir.resolve()
    if data_dir == install_dir or data_dir in install_dir.parents or install_dir in data_dir.parents:
        raise ValueError("Brukerdata ligger inne i appmappen og kan ikke oppdateres trygt.")
    if not install_dir.is_dir():
        raise ValueError("Fant ikke installasjonsmappen.")
    if status_callback:
        status_callback("Kontrollerer SHA-256 …")
    if sha256_file(archive_path) != expected_sha256.lower():
        raise ValueError("SHA-256-kontrollen av releasepakken feilet.")

    _wait_for_process(parent_process_id)

    parent_dir = install_dir.parent
    staging_root = Path(tempfile.mkdtemp(prefix=".SkiErgPortal-staging-", dir=parent_dir))
    backup_dir = parent_dir / f".SkiErgPortal-backup-{uuid.uuid4().hex}"
    moved_old_install = False
    try:
        if status_callback:
            status_callback("Validerer releasepakken …")
        staged_app = extract_release_archive(archive_path, staging_root)
        validate_staged_package(staged_app, expected_version)
        if status_callback:
            status_callback("Installerer oppdateringen …")
        os.replace(install_dir, backup_dir)
        moved_old_install = True
        try:
            os.replace(staged_app, install_dir)
            environment = os.environ.copy()
            environment["SKIERGPORTAL_DATA_DIR"] = str(data_dir)
            smoke_result = subprocess.run(
                [str(install_dir / "SkiErgPortal.exe"), "--smoke-test"],
                cwd=install_dir,
                env=environment,
                check=False,
                timeout=60,
            )
            if smoke_result.returncode != 0:
                raise RuntimeError("Den oppdaterte appens smoke-test feilet.")
            if status_callback:
                status_callback("Starter den nye versjonen …")
            application = subprocess.Popen([str(install_dir / "SkiErgPortal.exe")], cwd=install_dir, env=environment)
            time.sleep(2)
            if application.poll() is not None:
                raise RuntimeError("Den oppdaterte appen avsluttet under oppstart.")
        except Exception:
            failed_install = parent_dir / f".SkiErgPortal-failed-{uuid.uuid4().hex}"
            if install_dir.exists():
                os.replace(install_dir, failed_install)
            if backup_dir.exists():
                os.replace(backup_dir, install_dir)
            moved_old_install = False
            shutil.rmtree(failed_install, ignore_errors=True)
            raise
        shutil.rmtree(backup_dir, ignore_errors=True)
        moved_old_install = False
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass
    finally:
        if moved_old_install and backup_dir.exists() and not install_dir.exists():
            os.replace(backup_dir, install_dir)
        shutil.rmtree(staging_root, ignore_errors=True)


class _UpdateProgress:
    def __init__(self) -> None:
        self.root = None
        self.label = None
        self.progress = None
        try:
            import tkinter as tk
            from tkinter import ttk

            self.root = tk.Tk()
            self.root.title("Oppdaterer SkiErgPortal")
            self.root.resizable(False, False)
            self.root.geometry("360x110")
            self.root.protocol("WM_DELETE_WINDOW", lambda: None)
            self.label = ttk.Label(self.root, text="Starter oppdatering …", padding=(16, 14))
            self.label.pack(fill=tk.X)
            self.progress = ttk.Progressbar(self.root, mode="indeterminate")
            self.progress.pack(fill=tk.X, padx=16, pady=(0, 14))
            self.progress.start(12)
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            if self.root is not None:
                try:
                    self.root.destroy()
                except Exception:
                    pass
            self.root = None

    def set_status(self, message: str) -> None:
        if self.root is None or self.label is None:
            return
        try:
            self.label.configure(text=message)
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            self.root = None

    def close(self) -> None:
        if self.root is not None:
            try:
                self.progress.stop()
                self.root.destroy()
            except Exception:
                pass
            self.root = None


def _show_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SkiErgPortal kunne ikke oppdateres", message, parent=root)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--version")
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args(argv)
    if args.smoke_test:
        return 0

    required = (args.install_dir, args.archive, args.sha256, args.version, args.parent_pid, args.data_dir)
    if any(value is None for value in required):
        parser.error("Alle installasjonsargumenter er påkrevd.")
    progress = _UpdateProgress()
    try:
        progress.set_status("Kontrollerer oppdateringen …")
        install_update(
            args.install_dir,
            args.archive,
            args.sha256,
            args.version,
            args.parent_pid,
            args.data_dir,
            status_callback=progress.set_status,
        )
    except Exception as exc:
        progress.close()
        _show_error(str(exc))
        return 1
    progress.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())