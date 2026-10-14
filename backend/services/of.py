from app.config import get_settings
from app.services.http_client import make_client


def _first(record: dict, *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str) and value:
            return value
    return ""


async def search_openfda(drug: str, limit: int = 5) -> list[dict]:
    settings = get_settings()
    # Search normalized generic/brand names. FDA search syntax requires escaping quotes.
    safe = drug.replace("\\", " ").replace('"', " ").strip()
    if not safe:
        return []
    params = {
        "search": f'openfda.generic_name:"{safe}" OR openfda.brand_name:"{safe}"',
        "limit": min(max(limit, 1), 5),
    }
    if settings.openfda_api_key:
        params["api_key"] = settings.openfda_api_key

    async with make_client() as client:
        response = await client.get("https://api.fda.gov/drug/label.json", params=params)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()

    records = []
    for record in payload.get("results", []):
        openfda = record.get("openfda", {})
        brand = _first(openfda, "brand_name")
        generic = _first(openfda, "generic_name")
        display_name = brand or generic or drug
        spl_set_id = _first(openfda, "spl_set_id")
        # This URL is a search link, not a fabricated record URL.
        url = "https://open.fda.gov/apis/drug/label/"
        if spl_set_id:
            url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={spl_set_id}"
        sections = {}
        for key in ("indications_and_usage", "boxed_warning", "warnings_and_cautions",
                    "contraindications", "dosage_and_administration", "adverse_reactions",
                    "drug_interactions", "use_in_specific_populations"):
            value = record.get(key)
            if value:
                sections[key] = " ".join(value)[:2500] if isinstance(value, list) else str(value)[:2500]
        identifier = f"SPL:{spl_set_id}" if spl_set_id else f"FDA-LABEL:{display_name}"
        records.append({
            "source_type": "openfda",
            "title": f"{display_name} — FDA drug label",
            "identifier": identifier,
            "url": url,
            "generic_name": generic,
            "brand_name": brand,
            "label_sections": sections,
            "effective_time": record.get("effective_time"),
            "citation": f"U.S. Food and Drug Administration. {display_name} drug labeling. openFDA.",
        })
    return records
