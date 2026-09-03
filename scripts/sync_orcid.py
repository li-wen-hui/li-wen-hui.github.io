import requests
import json


ORCID = "0009-0008-4156-6373"

url = (
    f"https://pub.orcid.org/v3.0/"
    f"{ORCID}/works"
)

headers = {
    "Accept": "application/json"
}


response = requests.get(
    url,
    headers=headers
)

data = response.json()


papers = []


for item in data["group"]:

    summary = item["work-summary"][0]

    title = summary["title"]["title"]["value"]

    year = ""

    if summary.get("publication-date"):
        year = summary["publication-date"].get(
            "year", {}
        ).get(
            "value",
            ""
        )


    papers.append(
        {
            "title": title,
            "year": year
        }
    )


with open(
    "site/data/publications.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        papers,
        f,
        indent=2,
        ensure_ascii=False
    )
