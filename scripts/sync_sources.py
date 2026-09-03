"""
Academic data synchronization

Rules:
1. publications.yml is the ONLY source of publications.
2. External APIs only update metadata.
3. Never add/remove publications automatically.
"""


import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CACHE = ROOT / "data" / "cache"


def load_json(path):

    if path.exists():
        return json.loads(path.read_text(
            encoding="utf-8"
        ))

    return {}



def save_json(path,data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )



def sync_github():

    print("Sync GitHub statistics")

    github = {
        "enabled": True
    }

    save_json(
        CACHE/"github.json",
        github
    )



def sync_scholar():

    print("Sync Google Scholar statistics")

    scholar = {

        "enabled": True,

        # future:
        # citation_count
        # h_index

    }

    save_json(
        CACHE/"scholar.json",
        scholar
    )



def sync_crossref():

    print("Sync Crossref metadata")

    crossref = {

        "enabled": True,

        # DOI metadata only

    }


    save_json(
        CACHE/"crossref.json",
        crossref
    )



def main():

    print(
        "Start academic synchronization"
    )


    sync_github()

    sync_scholar()

    sync_crossref()


    print(
        "Sync finished."
    )


if __name__=="__main__":

    main()
