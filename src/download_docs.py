"""Download the public PDFs listed in config/sources.json."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def download_documents(sources_file, output_dir):
    sources = json.loads(Path(sources_file).read_text(encoding="utf-8"))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for source in sources:
        filename = source["filename"]
        destination = output_dir / filename
        if destination.exists():
            print(f"Already exists: {destination}")
            continue

        print(f"Downloading: {source['title']}")
        request = Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
        temporary = destination.with_suffix(".part")

        try:
            with urlopen(request, timeout=60) as response:
                with temporary.open("wb") as file:
                    while True:
                        data = response.read(1024 * 1024)
                        if not data:
                            break
                        file.write(data)

            with temporary.open("rb") as file:
                if file.read(5) != b"%PDF-":
                    raise ValueError("The server returned a non-PDF file")
            temporary.replace(destination)
            print(f"Saved: {destination}")
        except Exception as error:
            temporary.unlink(missing_ok=True)
            print(f"Could not download {filename}: {error}")
            print(f"Download it manually from: {source['url']}")


if __name__ == "__main__":
    download_documents(ROOT / "config/sources.json", ROOT / "data/raw")
