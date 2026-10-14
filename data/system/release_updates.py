from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


REPOSITORY = "Teamcereal/skiergportal"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
PACKAGE_ASSET = "SkiErgPortal-windows-x64.zip"
CHECKSUM_ASSET = f"{PACKAGE_ASSET}.sha256"
_VERSION_PATTERN = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_ASSET_URL_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
_MAX_PACKAGE_BYTES = 1_000_000_000


class ReleaseCheckError(RuntimeError):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    version_parts: tuple[int, int, int]
    notes: str
    page_url: str
    package_url: str
    checksum_url: str


def parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise ReleaseCheckError(f"Ugyldig versjonsnummer: {value}")
    return tuple(int(part) for part in match.groups())


def _official_release_url(value: object, tag: str, asset_name: str) -> str:
    if not isinstance(value, str) or not value.startswith(_ASSET_URL_PREFIX):
        raise ReleaseCheckError("Release inneholder en nedlastingsadresse utenfor det offisielle GitHub-repoet.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith(f"/{tag}/{asset_name}")
    ):
        raise ReleaseCheckError("Release inneholder en ugyldig nedlastingsadresse.")
    return value


def parse_release(payload: object) -> Release:
    if not isinstance(payload, dict) or payload.get("draft") or payload.get("prerelease"):
        raise ReleaseCheckError("Fant ingen stabil GitHub Release.")

    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ReleaseCheckError("GitHub Release mangler en gyldig v-prefikset versjonstag.")
    version = tag[1:]
    version_parts = parse_version(version)

    page_url = payload.get("html_url")
    expected_page = f"https://github.com/{REPOSITORY}/releases/tag/"
    if not isinstance(page_url, str) or not page_url.startswith(expected_page):
        raise ReleaseCheckError("GitHub Release har en ugyldig sideadresse.")

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ReleaseCheckError("GitHub Release mangler release-filer.")
    asset_urls: dict[str, str] = {}
    for asset in assets:
        if isinstance(asset, dict) and asset.get("name") in (PACKAGE_ASSET, CHECKSUM_ASSET):
            name = asset["name"]
            if name in asset_urls:
                raise ReleaseCheckError(f"Release inneholder flere assets med navnet {name}.")
            asset_urls[name] = _official_release_url(asset.get("browser_download_url"), tag, name)

    if PACKAGE_ASSET not in asset_urls or CHECKSUM_ASSET not in asset_urls:
        raise ReleaseCheckError("GitHub Release mangler ZIP-pakken eller SHA-256-filen.")

    notes = payload.get("body")
    return Release(
        version=version,
        version_parts=version_parts,
        notes=notes if isinstance(notes, str) else "",
        page_url=page_url,
        package_url=asset_urls[PACKAGE_ASSET],
        checksum_url=asset_urls[CHECKSUM_ASSET],
    )


def fetch_latest_release(timeout: float = 5.0) -> Release:
    request = Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SkiErgPortal-Update-Checker",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(2_000_000))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ReleaseCheckError(f"Kunne ikke hente GitHub Release: {exc}") from exc
    return parse_release(payload)


def is_newer_release(current_version: str, release: Release) -> bool:
    return release.version_parts > parse_version(current_version)


def parse_checksum(value: str) -> str:
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?SkiErgPortal-windows-x64\.zip\s*", value)
    if match is None:
        raise ReleaseCheckError("SHA-256-filen har ugyldig format.")
    return match.group(1).lower()


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "SkiErgPortal-Updater"})


def download_release(
    release: Release,
    destination: Path,
    progress_callback: Callable[[int, int | None], None] | None = None,
    timeout: float = 20.0,
) -> tuple[Path, str]:
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / f"SkiErgPortal-{release.version}-windows-x64.zip"
    partial_path = archive_path.with_suffix(archive_path.suffix + ".part")

    try:
        with urlopen(_request(release.checksum_url), timeout=timeout) as response:
            checksum_text = response.read(2048).decode("ascii")
        expected_hash = parse_checksum(checksum_text)

        digest = hashlib.sha256()
        downloaded = 0
        with urlopen(_request(release.package_url), timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > _MAX_PACKAGE_BYTES:
                raise ReleaseCheckError("Releasepakken er større enn tillatt størrelse.")
            with partial_path.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > _MAX_PACKAGE_BYTES:
                        raise ReleaseCheckError("Releasepakken er større enn tillatt størrelse.")
                    output.write(chunk)
                    digest.update(chunk)
                    if progress_callback:
                        progress_callback(downloaded, int(content_length) if content_length else None)

        if digest.hexdigest() != expected_hash:
            raise ReleaseCheckError("SHA-256-kontrollen av releasepakken feilet.")
        if not zipfile.is_zipfile(partial_path):
            raise ReleaseCheckError("Den nedlastede releasepakken er ikke en gyldig ZIP-fil.")
        partial_path.replace(archive_path)
        return archive_path, expected_hash
    except Exception as exc:
        try:
            partial_path.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, ReleaseCheckError):
            raise
        if isinstance(exc, (OSError, URLError, TimeoutError, UnicodeDecodeError, ValueError)):
            raise ReleaseCheckError(f"Kunne ikke laste ned eller kontrollere releasepakken: {exc}") from exc
        raise