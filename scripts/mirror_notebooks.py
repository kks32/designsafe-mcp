"""Mirror the UW community-data corpus locally (reproducible fetch).

The MCP grounds its snippets in these folders; run this once after
cloning. Files over 50 MB are skipped.
"""

import os

from dapi import DSClient

BASE = "Jupyter Notebooks for Civil Engineering Courses/University_of_Washington"
DEST = os.path.join(os.path.dirname(__file__), "..", "notebooks",
                    "University_of_Washington")
CAP = 50 * 1024 * 1024

ds = DSClient()


def pull(rel=""):
    uri = f"tapis://designsafe.storage.community/{BASE}/{rel}".rstrip("/")
    for it in ds.files.list(uri):
        child = f"{rel}/{it.name}".strip("/")
        if it.type == "dir":
            pull(child)
            continue
        if (getattr(it, "size", 0) or 0) > CAP:
            print(f"skip (> {CAP >> 20} MB): {child}")
            continue
        dest = os.path.join(DEST, child)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        ds.files.download(f"{uri}/{it.name}", dest)


if __name__ == "__main__":
    pull()
    print("mirror complete")
