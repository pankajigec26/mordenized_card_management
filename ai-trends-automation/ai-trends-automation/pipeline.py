"""
easyaiml.com — Daily AI Trends Automation Pipeline (FREE-TIER VERSION)
========================================================================

Uses only free services:
  - Gemini API free tier (ai.google.dev) for writing the reports and the LinkedIn post
  - Tavily free tier (tavily.com) for web search — Gemini's OWN built-in search
    tool is billed per query even on the free plan, so this script does the
    searching itself with Tavily and hands Gemini the results as plain text.
  - WordPress REST API (your own site, free)
  - Buffer free/beta API (optional) for LinkedIn posting

Flow:
  1. For each of the 3 beats (QA, Graph, AI Tech), run a handful of Tavily
     searches, collect result snippets.
  2. Hand those snippets + your original editorial instructions to Gemini,
     which writes the WordPress-ready report using ONLY those results.
  3. Publish the combined report to WordPress as a draft.
  4. Repurpose the AI Tech report into a LinkedIn post via Gemini.
  5. Push it to Buffer (or save it locally if Buffer isn't configured).

Free-tier limits to know about (check current numbers before relying on this):
  - Gemini free tier: rate-limited per minute/day, and (per Google's terms for
    the no-cost tier) your prompts/outputs may be used to improve Google's
    products. Fine for public news content like this; worth knowing.
  - Tavily free tier: ~1,000 search credits/month. This script uses ~15
    searches per run (5 per beat x 3 beats), so a daily run uses ~450/month —
    comfortably inside the free allowance.
"""

import os
import sys
import base64
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("pipeline.log"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ai_trends_pipeline")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

WP_URL = os.environ["WP_URL"].rstrip("/")
WP_USER = os.environ["WP_USER"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]
WP_STATUS = os.environ.get("WP_STATUS", "draft")

BUFFER_API_KEY = os.environ.get("BUFFER_API_KEY")
BUFFER_LINKEDIN_CHANNEL_ID = os.environ.get("BUFFER_LINKEDIN_CHANNEL_ID")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
TODAY = datetime.now().strftime("%B %d, %Y")

# ---------------------------------------------------------------------------
# Search queries per beat — static lists so no extra LLM call is needed just
# to decide what to search for. Edit these anytime to tune coverage.
# ---------------------------------------------------------------------------
SEARCH_QUERIES = {
    "qa": [
        "AI agentic software testing research arXiv",
        "Qodo Diffblue Applitools new release",
        "self-healing test automation LLM 2026",
        "Playwright Cypress AI test generation update",
        "GraphRAG requirement to test traceability",
    ],
    "graph": [
        "GraphRAG research paper arXiv",
        "Neo4j Memgraph TigerGraph new release",
        "graph neural network research 2026",
        "LangChain LlamaIndex GraphRAG update",
        "knowledge graph agent memory research",
    ],
    "ai": [
        "new AI model release this week",
        "Anthropic OpenAI Google DeepMind research announcement",
        "AI agent framework release 2026",
        "open source AI model release",
        "AI reasoning benchmark research paper",
    ],
}

EDITORIAL_INSTRUCTIONS = {
    "qa": f"""Role: You are an AI in Quality Engineering & Software Testing Intelligence Editor.
Focus only on meaningful technical developments in AI-driven QA, autonomous test generation, agentic testing, self-healing automation, and AI-assisted software quality assurance.
Exclude: funding/acquisitions/stock news; beginner tutorials/opinion pieces; vendor press releases without whitepapers/benchmarks/repos; manual QA news without AI/ML integration.
Output Format (strictly for WordPress, ready to copy-paste):
AI Quality Engineering Watch — {TODAY}
Prerequisite: a short storyline for context, do not mention the date.
1. [Short Technical Headline]
What happened: 2-3 sentences.
Why it matters: 1-2 sentences.
Tech Stack/Concepts: [list]
Source: [Website / arXiv ID + Direct Link]
(repeat for each item found in the search results, up to 10)
Final Section — Emerging QA AI Trends: 3-4 sentences.
Label each item's status (Research Paper / Open-Source Framework / Beta Feature / GA Production Release) and include its date.
If the search results contain nothing substantive, say: "No major emerging AI Quality Engineering developments identified today." Do not pad with low-value items.""",
    "graph": f"""Role: You are a Graph Technology & Graph AI Intelligence Editor.
Focus only on meaningful developments in Graph AI, Knowledge Graphs, GNNs, Graph RAG, and Graph Database Engines.
Exclude: funding/acquisitions/earnings; marketing press releases without technical substance; general AI news lacking graph integration; duplicate coverage (consolidate to the primary source).
Output Format (strictly for WordPress, ready to copy-paste):
Graph Tech & AI Watch — {TODAY}
Prerequisite: a less-than-50-word storyline.
1. [Short Technical Headline]
What happened: 2-3 sentences.
Why it matters: 1-2 sentences.
Tech Stack/Concepts: [list]
Source: [Website / arXiv ID + Direct Link]
(repeat for each item found in the search results, up to 10)
Final Section — Emerging Graph Trends: 3-4 sentences.
Label each item's status and include its date.
If the search results contain nothing substantive, say: "No major emerging Graph AI or Knowledge Graph developments identified today." Do not pad with low-value items.""",
    "ai": f"""Role: You are an AI Emerging Technology News Editor.
Focus only on meaningful emerging AI technology developments: new models/architectures, reasoning/inference advances, agents, RAG/memory, multimodal AI, AI coding, evaluation, safety, infrastructure, open-source, robotics, generative media, new research techniques.
Exclude: acquisitions, funding, stock news, earnings, leadership changes, partnerships without technical substance, pure marketing, generic commentary, repetitive already-reported news.
Output Format (strictly for WordPress, ready to copy-paste):
AI Technology Watch — {TODAY}
A storyline in less than 50 words.
1. [Short Technology Headline]
What happened: 2-3 sentences.
Why it matters: 1 sentence.
Source: [Website Name + Article Link]
(repeat for each item found in the search results, up to 10)
Final Section — Emerging Trends: 2-3 major trends as 2-4 descriptive pointers.
Distinguish research/prototype/GA and give each item's date.
If the search results contain nothing substantive, say: "No major emerging AI technology developments identified today." Do not pad the report.""",
}

LINKEDIN_PROMPT_TEMPLATE = """Role: You are an expert B2B social media strategist and executive ghostwriter known for creating highly engaging, scannable, and thought-provoking LinkedIn content.
Structure & Formatting Rules:
a. The Hook: 1-2 scroll-stopping sentences on the most surprising/impactful insight.
b. The Setup: one brief sentence on why this matters right now.
c. The Core Insights: top 3-5 points as a numbered list.
d. Visual Appeal: generous line breaks; bold key concepts/metrics; 1-2 professional emojis per section, not overdone.
e. The Bottom Line: 1-2 sentence "Emerging Takeaway".
f. Call to Action: point readers to read the full details via this link: {link}
g. Tags: 4-6 relevant hashtags.
Tone: professional, authoritative, conversational, short and punchy, no corporate fluff.

Source Text to Summarize:
{source_text}

Output ONLY the finished LinkedIn post text (no preamble, no notes)."""


# ---------------------------------------------------------------------------
# Step 1a — Tavily web search
# ---------------------------------------------------------------------------
def tavily_search(query: str, max_results: int = 4, days: int = 3) -> list[dict]:
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "days": days,
                "include_answer": False,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        log.exception(f"Tavily search failed for query: {query}")
        return []


def gather_search_context(beat: str) -> str:
    seen_urls = set()
    blocks = []
    for query in SEARCH_QUERIES[beat]:
        for result in tavily_search(query):
            url = result.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = result.get("title", "")
            content = result.get("content", "")[:1500]
            blocks.append(f"SOURCE: {title}\nURL: {url}\nCONTENT: {content}\n")
    if not blocks:
        return "(No search results were returned for this beat.)"
    return "\n---\n".join(blocks)


# ---------------------------------------------------------------------------
# Step 1b — Gemini writes the report from the gathered search context
# ---------------------------------------------------------------------------
def generate_report(beat: str) -> str:
    log.info(f"Gathering search results for beat: {beat}")
    context = gather_search_context(beat)

    prompt = f"""{EDITORIAL_INSTRUCTIONS[beat]}

Use ONLY the search results below as your factual source — do not add facts
from general knowledge, and do not invent sources or links. If a search
result doesn't clearly belong to this beat's focus, skip it rather than
forcing it in.

=== SEARCH RESULTS ===
{context}
"""
    log.info(f"Generating report via Gemini: {beat}")
    resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return (resp.text or "").strip()


# ---------------------------------------------------------------------------
# Step 2 — publish to WordPress
# ---------------------------------------------------------------------------
def plain_text_to_wp_html(text: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)


def publish_to_wordpress(title: str, html_content: str) -> dict:
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    payload = {"title": title, "content": html_content, "status": WP_STATUS}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Step 3 — LinkedIn post via Gemini
# ---------------------------------------------------------------------------
def generate_linkedin_post(source_text: str, link: str) -> str:
    prompt = LINKEDIN_PROMPT_TEMPLATE.format(source_text=source_text[:12000], link=link)
    resp = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return (resp.text or "").strip()


# ---------------------------------------------------------------------------
# Step 4 — Buffer (optional)
# ---------------------------------------------------------------------------
BUFFER_ENDPOINT = "https://api.buffer.com"


def buffer_graphql(query: str, variables: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {BUFFER_API_KEY}", "Content-Type": "application/json"}
    r = requests.post(BUFFER_ENDPOINT, headers=headers, json={"query": query, "variables": variables or {}}, timeout=60)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"Buffer API error: {data['errors']}")
    return data["data"]


def push_to_buffer(text: str):
    if not BUFFER_API_KEY or not BUFFER_LINKEDIN_CHANNEL_ID:
        log.warning("Buffer not configured — saving LinkedIn post to linkedin_post_pending.txt instead.")
        with open("linkedin_post_pending.txt", "w") as f:
            f.write(text)
        return None
    query = """
    mutation CreatePost($text: String!, $channelId: String!) {
      createPost(input: { text: $text, channelId: $channelId, schedulingType: automatic, mode: customSchedule }) {
        ... on PostActionSuccess { post { id text } }
        ... on MutationError { message }
      }
    }
    """
    return buffer_graphql(query, {"text": text, "channelId": BUFFER_LINKEDIN_CHANNEL_ID})


def list_buffer_channels():
    org_query = "query { account { organizations { id name } } }"
    orgs = buffer_graphql(org_query)["account"]["organizations"]
    for org in orgs:
        chan_query = """
        query Channels($organizationId: String!) {
          channels(input: { organizationId: $organizationId }) { id name service }
        }
        """
        channels = buffer_graphql(chan_query, {"organizationId": org["id"]})["channels"]
        print(f"Organization: {org['name']} ({org['id']})")
        for c in channels:
            print(f"  service={c['service']:<10} name={c['name']:<25} channelId={c['id']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    try:
        ai_report = generate_report("ai")
        qa_report = generate_report("qa")
        graph_report = generate_report("graph")
    except Exception:
        log.exception("Report generation failed — aborting before publishing anything.")
        sys.exit(1)

    combined = "\n\n<hr>\n\n".join([ai_report, qa_report, graph_report])

    if all("no major" in r.lower() for r in [ai_report, qa_report, graph_report]):
        log.info("Nothing significant identified today across all three beats — skipping publish.")
        return

    wp_title = f"AI Trends Digest — {TODAY}"
    html = plain_text_to_wp_html(combined)

    try:
        wp_result = publish_to_wordpress(wp_title, html)
    except Exception:
        log.exception("WordPress publish failed.")
        sys.exit(1)

    post_link = wp_result.get("link", WP_URL)
    log.info(f"WordPress post created ({WP_STATUS}): {post_link}")

    try:
        linkedin_text = generate_linkedin_post(ai_report, post_link)
        push_to_buffer(linkedin_text)
        log.info("LinkedIn post generated and handed to Buffer (or saved locally).")
    except Exception:
        log.exception("LinkedIn step failed — WordPress post still succeeded.")

    log.info("Pipeline run complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list-buffer-channels":
        list_buffer_channels()
    else:
        main()
