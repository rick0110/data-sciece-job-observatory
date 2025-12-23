from __future__ import annotations

import json
from pathlib import Path

from job_scrapper.specialized_scrappers import scrape_from_linkedin


def get_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "data").exists():
            return parent
    return Path.cwd()


def main(headless: bool = False) -> None:
    project_root = get_project_root()
    links_path = Path(__file__).resolve().parent / ".config" / "links_linkedin.txt"
    output_path = project_root / "data" / "linkedin_data_raw.json"

    with open(links_path, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f.readlines() if line.strip()]

    data: list[dict] = []
    for link in links:
        print(f"Scraping data from: {link}")
        scraped_data = scrape_from_linkedin(link, headless=headless)
        data.extend(scraped_data)
        print(f"Already scraped {len(data)} job postings so far.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Saved {len(data)} job postings to: {output_path}")


if __name__ == "__main__":
    main(headless=False)
