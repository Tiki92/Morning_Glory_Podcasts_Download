import os
import re

import requests


PODCAST_DIR = "podcasts"
DOWNLOAD_URL_TEMPLATE = "https://api.rockfm.ro/api/podcast-episode-download/{}"


def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '', filename).strip()


def podcast_save_path(title, occurrence):
    suffix = f" ({occurrence})" if occurrence > 1 else ""
    return os.path.join(PODCAST_DIR, f"{sanitize_filename(title)}{suffix}.mp3")


def has_mp3_header(path):
    with open(path, "rb") as podcast_file:
        header = podcast_file.read(10)
        if header[:3] == b"ID3":
            return True
        if len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0:
            return True
    return False


def check_files():
    occurrences = {}
    checked = 0
    problems = []

    with open("podcast_urls.txt", encoding="utf-8") as urls_file:
        entries = [line.strip().split("|", 1) for line in urls_file if line.strip()]

    for title, page_url in entries:
        occurrences[title] = occurrences.get(title, 0) + 1
        path = podcast_save_path(title, occurrences[title])
        episode_match = re.search(r"/podcast-episode/(\d+)", page_url)
        if not episode_match:
            problems.append(f"No episode ID: {title}")
            continue

        if not os.path.isfile(path):
            problems.append(f"Missing: {path}")
            continue

        try:
            response = requests.head(
                DOWNLOAD_URL_TEMPLATE.format(episode_match.group(1)),
                allow_redirects=True,
                timeout=30,
            )
            response.raise_for_status()
            remote_length = int(response.headers.get("content-length", 0))
            local_length = os.path.getsize(path)
            if remote_length and local_length != remote_length:
                problems.append(
                    f"Size mismatch: {path} (local {local_length}, remote {remote_length})"
                )
            if local_length == 0 or not has_mp3_header(path):
                problems.append(f"Invalid MP3 header or empty file: {path}")
            checked += 1
        except requests.RequestException as error:
            problems.append(f"Could not check {path}: {error}")

    print(f"Checked {checked}/{len(entries)} files.")
    if problems:
        print("Problems found:")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("All files match the server-reported lengths and have MP3 headers.")


if __name__ == "__main__":
    check_files()