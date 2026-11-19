from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin
import csv
import json

BASE = "https://www.pib.gov.in/"

class PIBLinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        attrs = dict(attrs)
        href = attrs.get("href", "")

        if "PRID=" not in href.upper():
            return

        self.current = {
            "title": attrs.get("title", "").strip(),
            "url": urljoin(BASE, href)
        }

    def handle_data(self, data):
        if self.current and not self.current["title"]:
            self.current["title"] += data.strip() + " "

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current:
            self.current["title"] = " ".join(
                self.current["title"].split()
            )
            self.links.append(self.current)
            self.current = None

html = Path("pib_all_releases.html").read_text(
    encoding="utf-8",
    errors="replace"
)

parser = PIBLinkExtractor()
parser.feed(html)

unique = {}
for item in parser.links:
    if "PressReleseDetail.aspx?PRID=" in item["url"]:
        unique[item["url"]] = item

records = list(unique.values())

Path("pib_release_links.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

with open(
    "pib_release_links.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["title", "url"]
    )
    writer.writeheader()
    writer.writerows(records)

print("=" * 55)
print("PIB OFFICIAL ARTICLE LINK EXTRACTION")
print("=" * 55)
print("TOTAL UNIQUE ARTICLE LINKS:", len(records))

for item in records[:20]:
    print("\nTITLE:", item["title"])
    print("URL:", item["url"])

print("\nFILES CREATED:")
print("pib_release_links.json")
print("pib_release_links.csv")
print("\nDONE")
