"""Fetch the reference documents the knowledge layer cites.

community_data/ is gitignored, so these downloads make the corpus
reproducible on a fresh clone. Run once, then `reindex` so the PDFs
join the passage search.
"""

import urllib.request
from pathlib import Path

REFERENCES = {
    "PM4Sand_v3.3_CGM-23-01.pdf": (
        "https://itasca-software.s3.amazonaws.com/udm-library/"
        "Boulanger_Ziotopoulou_PM4Sand_v3.3_CGM-23-01.pdf"
    ),
}


def main() -> None:
    dest = Path(__file__).parent.parent / "community_data" / "references"
    dest.mkdir(parents=True, exist_ok=True)
    for name, url in REFERENCES.items():
        target = dest / name
        if target.exists():
            print(f"have {name}")
            continue
        print(f"fetching {name}")
        urllib.request.urlretrieve(url, target)
    print(f"references in {dest}")


if __name__ == "__main__":
    main()
