from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from release_updates import (
    CHECKSUM_ASSET,
    PACKAGE_ASSET,
    ReleaseCheckError,
    download_release,
    is_newer_release,
    parse_release,
    parse_version,
)


def _release_payload(tag: str = "v0.2.0") -> dict:
    asset_base = f"https://github.com/Teamcereal/skiergportal/releases/download/{tag}"
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/Teamcereal/skiergportal/releases/tag/{tag}",
        "body": "Release notes",
        "assets": [
            {"name": PACKAGE_ASSET, "browser_download_url": f"{asset_base}/{PACKAGE_ASSET}"},
            {"name": CHECKSUM_ASSET, "browser_download_url": f"{asset_base}/{CHECKSUM_ASSET}"},
        ],
    }


class _Response:
    def __init__(self, content: bytes) -> None:
        self.content = io.BytesIO(content)
        self.headers = {"Content-Length": str(len(content))}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.content.close()

    def read(self, size: int = -1) -> bytes:
        return self.content.read(size)


class ReleaseUpdateTests(unittest.TestCase):
    def test_parse_version(self) -> None:
        self.assertEqual(parse_version("v1.12.3"), (1, 12, 3))

    def test_rejects_non_semantic_versions(self) -> None:
        with self.assertRaises(ReleaseCheckError):
            parse_version("v1.2")

    def test_parses_official_release_assets(self) -> None:
        release = parse_release(_release_payload())
        self.assertEqual(release.version, "0.2.0")
        self.assertEqual(release.notes, "Release notes")
        self.assertTrue(release.package_url.endswith(PACKAGE_ASSET))

    def test_rejects_untrusted_asset_url(self) -> None:
        payload = _release_payload()
        payload["assets"][0]["browser_download_url"] = "https://example.com/app.zip"
        with self.assertRaises(ReleaseCheckError):
            parse_release(payload)

    def test_rejects_asset_url_with_wrong_tag_or_name(self) -> None:
        payload = _release_payload()
        payload["assets"][0]["browser_download_url"] = (
            "https://github.com/Teamcereal/skiergportal/releases/download/v9.9.9/other.zip"
        )
        with self.assertRaises(ReleaseCheckError):
            parse_release(payload)

    def test_requires_package_and_checksum(self) -> None:
        payload = _release_payload()
        payload["assets"].pop()
        with self.assertRaises(ReleaseCheckError):
            parse_release(payload)

    def test_detects_only_newer_versions(self) -> None:
        release = parse_release(_release_payload())
        self.assertTrue(is_newer_release("0.1.0", release))
        self.assertFalse(is_newer_release("0.2.0", release))
        self.assertFalse(is_newer_release("0.3.0", release))

    def test_downloads_and_verifies_release_zip(self) -> None:
        release = parse_release(_release_payload())
        package_stream = io.BytesIO()
        with zipfile.ZipFile(package_stream, "w") as archive:
            archive.writestr("SkiErgPortal/SkiErgPortal.exe", b"test executable")
        package_bytes = package_stream.getvalue()
        checksum = f"{hashlib.sha256(package_bytes).hexdigest()}  {PACKAGE_ASSET}".encode("ascii")

        with tempfile.TemporaryDirectory() as temporary:
            with patch("release_updates.urlopen", side_effect=[_Response(checksum), _Response(package_bytes)]):
                package_path, actual_hash = download_release(release, Path(temporary))
            self.assertTrue(zipfile.is_zipfile(package_path))
            self.assertEqual(actual_hash, hashlib.sha256(package_bytes).hexdigest())
            self.assertFalse(package_path.with_suffix(package_path.suffix + ".part").exists())

    def test_rejects_bad_checksum_and_removes_partial_archive(self) -> None:
        release = parse_release(_release_payload())
        package_stream = io.BytesIO()
        with zipfile.ZipFile(package_stream, "w") as archive:
            archive.writestr("SkiErgPortal/SkiErgPortal.exe", b"test executable")

        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "release_updates.urlopen",
                side_effect=[_Response(b"0" * 64 + b"  " + PACKAGE_ASSET.encode()), _Response(package_stream.getvalue())],
            ):
                with self.assertRaises(ReleaseCheckError):
                    download_release(release, Path(temporary))
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == "__main__":
    unittest.main()