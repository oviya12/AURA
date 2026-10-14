from app.services.http_client import make_client


async def search_clinical_trials(query: str, limit: int = 5) -> list[dict]:
    params = {"query.term": query, "pageSize": min(max(limit, 1), 10), "format": "json"}
    async with make_client() as client:
        response = await client.get("https://clinicaltrials.gov/api/v2/studies", params=params)
        response.raise_for_status()
        payload = response.json()

    records = []
    for study in payload.get("studies", []):
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        desc = protocol.get("descriptionModule", {})
        outcomes = protocol.get("outcomesModule", {})
        nct = ident.get("nctId", "")
        if not nct:
            continue
        records.append({
            "source_type": "clinicaltrials",
            "title": ident.get("briefTitle") or ident.get("officialTitle") or nct,
            "identifier": nct,
            "url": f"https://clinicaltrials.gov/study/{nct}",
            "status": status.get("overallStatus"),
            "phase": design.get("phases", []),
            "study_type": design.get("studyType"),
            "brief_summary": desc.get("briefSummary", "")[:3500],
            "primary_outcomes": outcomes.get("primaryOutcomes", [])[:5],
            "start_date": status.get("startDateStruct", {}).get("date"),
            "completion_date": status.get("completionDateStruct", {}).get("date"),
            "citation": f"ClinicalTrials.gov. {ident.get('briefTitle', nct)}. Identifier: {nct}.",
        })
    return records
