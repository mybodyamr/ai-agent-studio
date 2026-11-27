import httpx
from html.parser import HTMLParser

class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.results=[]; self.current=None; self.capture=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == "a" and "result__a" in a.get("class",""):
            self.current={"title":"","url":a.get("href","")}
            self.capture=True
    def handle_data(self, data):
        if self.capture and self.current: self.current["title"] += data
    def handle_endtag(self, tag):
        if tag == "a" and self.capture and self.current:
            if self.current["title"].strip(): self.results.append(self.current)
            self.current=None; self.capture=False

async def search_public_web(query: str):
    # Only the explicitly entered query is sent. No conversation, files, or memory are attached.
    headers={"User-Agent":"AI-Agent-Studio/0.1 (local research)"}
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
        r=await client.get("https://html.duckduckgo.com/html/", params={"q":query})
        r.raise_for_status()
    parser=ResultParser(); parser.feed(r.text)
    return parser.results[:8]
