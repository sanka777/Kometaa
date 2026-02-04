import os
import re
from urllib.parse import unquote, urlparse

from modules import util
from modules.util import Failed

logger = util.logger

builders = ["m3u"]

_rating_key_regex = re.compile(r"(?:ratingKey=|/library/metadata/)(\d+)")
_year_suffix_regex = re.compile(r"^(.+?)\s*[\[(](\d{4})[\])]$")
_windows_path_regex = re.compile(r"^[a-zA-Z]:\\")


def _normalize_path(path):
    path = path.strip()
    path = path.replace("\\", "/")
    return os.path.normpath(path)


def _is_windows_path(path):
    return bool(_windows_path_regex.match(path))


def _is_url(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "plex", "file"}


def _extract_rating_key(value):
    match = _rating_key_regex.search(unquote(value))
    return int(match.group(1)) if match else None


def _extract_file_path(value):
    if _is_windows_path(value):
        return value
    parsed = urlparse(value)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    if parsed.scheme:
        return None
    return value


def _split_title_year(title):
    match = _year_suffix_regex.match(title)
    if match:
        return match.group(1).strip(), int(match.group(2))
    return title, None


def parse_m3u(path):
    if not os.path.exists(path):
        raise Failed(f"M3U Error: File not found: {path}")
    entries = []
    current_title = None
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip().lstrip("\ufeff")
            if not line:
                continue
            if line.startswith("#EXTINF"):
                if "," in line:
                    current_title = line.split(",", 1)[1].strip() or None
                else:
                    current_title = None
                continue
            if line.startswith("#"):
                continue
            entries.append({"source": line, "title": current_title})
            current_title = None
    return entries


def _location_map(library, builder_level):
    if builder_level in ["episode", "season", "album", "track"]:
        target_level = builder_level
    elif builder_level == "item":
        if library.is_show:
            target_level = "episode"
        elif library.is_music:
            target_level = "track"
        else:
            target_level = None
    else:
        target_level = builder_level
    items = library.get_all(builder_level=target_level)
    locations = {}
    for item in items:
        if not getattr(item, "locations", None):
            continue
        for location in item.locations:
            if not location:
                continue
            normalized = _normalize_path(str(location))
            locations.setdefault(normalized, []).append(item.ratingKey)
            normalized_case = os.path.normcase(normalized)
            locations.setdefault(normalized_case, []).append(item.ratingKey)
    return locations


def get_m3u_ids(path, libraries, builder_level):
    entries = parse_m3u(path)
    if not entries:
        raise Failed(f"M3U Error: No entries found in {path}")

    location_maps = {}
    ids = []

    for entry in entries:
        source = entry["source"]
        title = entry["title"]

        rating_key = _extract_rating_key(source)
        if rating_key:
            ids.append((rating_key, "ratingKey"))
            continue

        file_path = _extract_file_path(source)
        if file_path:
            normalized = _normalize_path(file_path)
            normalized_case = os.path.normcase(normalized)
            found = False
            for library in libraries:
                if library.name not in location_maps:
                    location_maps[library.name] = _location_map(library, builder_level)
                location_map = location_maps[library.name]
                for lookup in (normalized, normalized_case):
                    if lookup in location_map:
                        ids.extend([(rk, "ratingKey") for rk in location_map[lookup]])
                        found = True
            if not found:
                logger.warning(f"M3U Warning: No Plex item found for path: {source}")
            continue

        if _is_url(source) and title is None:
            parsed = urlparse(source)
            title = os.path.splitext(os.path.basename(parsed.path))[0] or source

        if title:
            parsed_title, year = _split_title_year(title)
            found = False
            for library in libraries:
                libtype = None if builder_level == "item" else library.Plex.TYPE
                results = library.exact_search(parsed_title, libtype=libtype, year=year)
                matches = [item for item in results if item.title == parsed_title]
                if matches:
                    ids.extend([(item.ratingKey, "ratingKey") for item in matches])
                    found = True
            if not found:
                logger.warning(f"M3U Warning: No Plex item found for title: {title}")
        else:
            logger.warning(f"M3U Warning: No title or path found for entry: {source}")

    return ids
