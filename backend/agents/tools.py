import httpx
from langchain_core.tools import tool


@tool
async def web_search(query: str) -> str:
    """Search the web for latest GST notifications, CBIC circulars, GST Council meeting decisions,
    income tax amendments, budget changes, case law updates, advance rulings, and current Indian
    tax news. Use this for any real-time or recent information. This searches across official
    government sites (cbic.gov.in, gst.gov.in, incometax.gov.in), tax portals (taxguru.in,
    caclubindia.com, cleartax.in), and news sources."""
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.responses.create(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=f"Indian tax law: {query}",
    )
    text_parts = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
    return "\n".join(text_parts) if text_parts else "No results found."


@tool
async def search_indian_kanoon(query: str) -> str:
    """Search Indian Kanoon (indiankanoon.org) for Indian case law, statutes, GST Act sections,
    Income Tax Act sections, tribunal decisions (CESTAT/GSTAT), High Court & Supreme Court
    judgments, and advance rulings. This is the primary source for legal text and judicial
    precedents on tax matters."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.indiankanoon.org/search/",
                params={"formInput": query, "pagenum": 0},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "KPMG-AI-TaxResearch/1.0",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for doc in data.get("docs", [])[:5]:
                    title = doc.get("title", "Untitled")
                    headline = doc.get("headline", "")
                    doc_id = doc.get("tid", "")
                    results.append(f"**{title}**\n{headline}\nSource: indiankanoon.org/doc/{doc_id}")
                return "\n\n---\n\n".join(results) if results else "No results found on Indian Kanoon."
            else:
                return await _kanoon_web_fallback(query)
        except Exception:
            return await _kanoon_web_fallback(query)


async def _kanoon_web_fallback(query: str) -> str:
    """Fallback: search Indian Kanoon via web search if API is unavailable."""
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.responses.create(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=f"site:indiankanoon.org {query} GST CGST income tax",
    )
    text_parts = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
    return "\n".join(text_parts) if text_parts else "Could not search Indian Kanoon."


@tool
async def lookup_gst_section(section: str) -> str:
    """Look up a specific section of the CGST Act 2017, SGST Act, IGST Act 2017, or CGST Rules 2017.
    Provide the section/rule reference (e.g., 'Section 16 CGST Act', 'Rule 36(4) CGST Rules',
    'Section 7 IGST Act'). Returns the full legal text, provisos, explanations, and any
    amendments by Finance Acts or notifications. Also searches for relevant CBIC clarificatory
    circulars on that section."""
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.responses.create(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=(
            f"Full text of {section} of GST Act India with all provisos, explanations, "
            f"and latest amendments including Finance Act changes. "
            f"Also find any CBIC circular clarifying {section}."
        ),
    )
    text_parts = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
    return "\n".join(text_parts) if text_parts else f"Could not find {section}."


@tool
async def search_income_tax(query: str) -> str:
    """Search for Income Tax Act 1961 sections, rules, recent Finance Act amendments, TDS/TCS
    rates and provisions, capital gains rules, international taxation, DTAA provisions, CBDT
    circulars, and advance rulings on income tax matters."""
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.responses.create(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=f"India Income Tax Act 1961: {query} latest Finance Act amendment CBDT circular",
    )
    text_parts = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
    return "\n".join(text_parts) if text_parts else "No income tax results found."


@tool
async def search_gst_circulars(query: str) -> str:
    """Search specifically for CBIC circulars, notifications, trade notices, and press releases
    related to GST. This tool focuses on finding the latest CBIC clarifications, policy changes,
    and administrative instructions. Useful for questions about compliance deadlines, procedural
    clarifications, and rate changes."""
    from openai import AsyncOpenAI
    import os

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.responses.create(
        model="gpt-4.1-mini",
        tools=[{"type": "web_search_preview"}],
        input=(
            f"CBIC circular notification GST {query} site:cbic.gov.in OR site:gst.gov.in "
            f"OR site:taxguru.in OR site:caclubindia.com"
        ),
    )
    text_parts = []
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_parts.append(content.text)
    return "\n".join(text_parts) if text_parts else "No circulars found."


ALL_TOOLS = [
    web_search,
    search_indian_kanoon,
    lookup_gst_section,
    search_income_tax,
    search_gst_circulars,
]
