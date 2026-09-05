import os
import json
import requests


# =========================
# ORCID ID
# =========================

ORCID = "0009-0008-4156-6373"


# =========================
# ORCID API
# =========================

ORCID_URL = (
    f"https://pub.orcid.org/v3.0/"
    f"{ORCID}/works"
)


headers = {
    "Accept": "application/json"
}


response = requests.get(
    ORCID_URL,
    headers=headers,
    timeout=20
)


response.raise_for_status()


data = response.json()


papers = []


# =========================
# Parse ORCID works
# =========================

for item in data.get("group", []):


    summary = item.get(
        "work-summary",
        [{}]
    )[0]


    title = (
        summary
        .get("title", {})
        .get("title", {})
        .get("value", "")
    )


    year = ""

    month = ""


    # =========================
    # ORCID publication date
    # =========================

    pub_date = summary.get(
        "publication-date"
    )


    if pub_date:


        year = (
            pub_date
            .get("year", {})
            .get("value", "")
        )


        month = (
            pub_date
            .get("month", {})
            .get("value", "")
        )


        if month:

            month = str(month).zfill(2)



    # =========================
    # DOI extraction
    # =========================

    doi = ""


    external_ids = (
        summary
        .get("external-ids", {})
        .get("external-id", [])
    )


    for eid in external_ids:


        if eid.get(
            "external-id-type"
        ) == "doi":


            doi = (
                eid
                .get(
                    "external-id-value",
                    ""
                )
            )


            break



    journal = ""

    authors = []



    # =========================
    # Crossref enrichment
    # =========================

    if doi:


        try:


            cr_response = requests.get(

                f"https://api.crossref.org/works/{doi}",

                timeout=20

            )


            cr_response.raise_for_status()


            message = (
                cr_response
                .json()
                .get("message", {})
            )



            # -------- journal --------

            journal = (
                message
                .get(
                    "container-title",
                    [""]
                )[0]
            )



            # -------- publication month --------

            date_parts = (
                message
                .get(
                    "published-print",
                    {}
                )
                .get(
                    "date-parts",
                    [[]]
                )
            )


            if not date_parts[0]:


                date_parts = (
                    message
                    .get(
                        "published-online",
                        {}
                    )
                    .get(
                        "date-parts",
                        [[]]
                    )
                )


            if date_parts[0]:


                if len(date_parts[0]) >= 1:


                    year = str(
                        date_parts[0][0]
                    )


                if len(date_parts[0]) >= 2:


                    month = str(
                        date_parts[0][1]
                    ).zfill(2)



            # -------- authors --------

            for author in message.get(
                "author",
                []
            ):


                given = author.get(
                    "given",
                    ""
                )


                family = author.get(
                    "family",
                    ""
                )


                name = (
                    given
                    + " "
                    + family
                ).strip()


                if name:

                    authors.append(name)



        except Exception as e:


            print(
                "Crossref error:",
                doi,
                e
            )



    # =========================
    # Save each paper
    # =========================

    papers.append({


        "title": title,


        "authors": authors,


        "journal": journal,


        "year": year,


        "month": month,


        "doi": doi,


        "doi_url":
            (
                f"https://doi.org/{doi}"
                if doi else ""
            ),


        "url":
            (
                f"https://doi.org/{doi}"
                if doi else ""
            ),


        "code": ""


    })



# =========================
# Save JSON
# =========================


os.makedirs(

    "site/data",

    exist_ok=True

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
