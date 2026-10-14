import xml.etree.ElementTree as ET
from urllib.parse import quote
from app.config import get_settings
from app.services.http_client import make_client


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


async def search_pubmed(query: str, limit: int = 5) -> list[dict]:
    settings = get_settings()
    params = {"db": "pubmed", "term": query, "retmax": min(max(limit, 1), 10),
              "retmode": "json", "sort": "relevance"}
    if settings.ncbi_tool_email:
        params["email"] = settings.ncbi_tool_email
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key

    async with make_client() as client:
        response = await client.get(f"{EUTILS}esearch.fcgi", params=params)
        response.raise_for_status()
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        if settings.ncbi_tool_email:
            fetch_params["email"] = settings.ncbi_tool_email
        if settings.ncbi_api_key:
            fetch_params["api_key"] = settings.ncbi_api_key
        detail = await client.get(f"{EUTILS}efetch.fcgi", params=fetch_params)
        detail.raise_for_status()

    root = ET.fromstring(detail.text)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//PMID") or "").strip()
        title = " ".join("".join(article.find(".//ArticleTitle").itertext()).split()) if article.find(".//ArticleTitle") is not None else "Untitled article"
        abstract_parts = []
        for node in article.findall(".//Abstract/AbstractText"):
            label = node.attrib.get("Label")
            value = " ".join("".join(node.itertext()).split())
            if value:
                abstract_parts.append(f"{label}: {value}" if label else value)
        authors = []
        for author in article.findall(".//AuthorList/Author")[:6]:
            last = author.findtext("LastName")
            initials = author.findtext("Initials")
            if last:
                authors.append(f"{last} {initials or ''}".strip())
        journal = article.findtext(".//Journal/Title") or ""
        year = article.findtext(".//PubDate/Year") or article.findtext(".//PubDate/MedlineDate") or ""
        citation = f"{'; '.join(authors)}. {title}. {journal}. {year}. PMID: {pmid}." if pmid else ""
        records.append({
            "source_type": "pubmed",
            "title": title,
            "identifier": f"PMID:{pmid}",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "abstract": " ".join(abstract_parts)[:5000],
            "journal": journal,
            "published_date": year,
            "citation": citation,
        })
    return records
