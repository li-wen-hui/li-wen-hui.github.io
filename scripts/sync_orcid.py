import requests
import json


ORCID = "0009-0008-4156-6373"


ORCID_URL = (
    f"https://pub.orcid.org/v3.0/"
    f"{ORCID}/works"
)


headers = {
    "Accept": "application/json"
}


response = requests.get(
    ORCID_URL,
    headers=headers
)

data = response.json()


papers = []


for item in data.get("group", []):

    summary = item["work-summary"][0]


    title = (
        summary
        .get("title", {})
        .get("title", {})
        .get("value", "")
    )


    year = ""

    if summary.get("publication-date"):

        year = (
            summary["publication-date"]
            .get("year", {})
            .get("value", "")
        )


    doi = ""

    if summary.get("external-ids"):

        for eid in summary["external-ids"].get(
            "external-id", []
        ):

            if eid.get(
                "external-id-type"
            ) == "doi":

                doi = eid.get(
                    "external-id-value",
                    ""
                )


    # Crossref补充信息

    journal = ""
    authors = []
    url = ""


    if doi:

        try:

            cr = requests.get(
                f"https://api.crossref.org/works/{doi}"
            )

            cr_data = cr.json()["message"]


            journal = (
                cr_data
                .get("container-title", [""])[0]
            )


            url = (
                cr_data
                .get("URL", "")
            )


            for author in cr_data.get(
                "author",
                []
            ):

                name = (
                    author.get("given", "")
                    + " "
                    +
                    author.get("family", "")
                )

                authors.append(name)


        except Exception:

            pass



    papers.append(
        {
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": year,
            "doi": doi,
            "url": url
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


print(
    "Updated publications:",
    len(papers)
)
