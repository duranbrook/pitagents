#!/usr/bin/env python3
"""
Scrapes franchise car dealerships in NY and NJ for each major brand,
then extracts staff email addresses from each dealership's staff page.
Outputs one markdown file per brand to docs/marketing/.
"""

import re
import time
import json
import os
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../docs/marketing")

BRANDS = [
    "bmw", "mercedes-benz", "audi", "lexus", "cadillac",
    "infiniti", "acura", "volvo", "porsche", "genesis",
    "toyota", "honda", "ford", "chevrolet", "nissan",
    "hyundai", "kia", "subaru", "mazda", "jeep", "ram", "gmc",
    "volkswagen", "dodge",
]

STATES = ["NY", "NJ"]

# Playwright browser instance (shared across calls)
_playwright = None
_browser = None
_page = None

# Common staff page path patterns to try per dealership
STAFF_PATHS = [
    "/about-us/staff/",
    "/about-us/meet-our-staff/",
    "/about-us/our-team/",
    "/about/staff/",
    "/about/team/",
    "/staff/",
    "/our-team/",
    "/meet-the-team/",
    "/meet-our-team/",
    "/about-us/",
    "/contact-us/",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# ── Cars.com dealer fetcher ───────────────────────────────────────────────────

def get_dealers_carscom(brand: str, state: str) -> list[dict]:
    """
    Fetch franchise dealers from Cars.com for a given brand + state.
    Returns list of {name, address, city, state, zip, url}.
    """
    brand_slug = brand.lower().replace(" ", "-").replace(".", "")
    # Cars.com uses makes[] param; some brands need specific slugs
    brand_map = {
        "mercedes-benz": "mercedes_benz",
        "ram": "ram",
        "gmc": "gmc",
    }
    make_param = brand_map.get(brand, brand_slug)

    dealers = []
    page = 1
    while True:
        url = (
            f"https://www.cars.com/dealers/buy/"
            f"?zip=10001&radius=500&dealer_type=franchised"
            f"&makes[]={make_param}&state={state}&page={page}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(".dealer-card, [data-qa='dealer-card'], .dealer-list-item")
            if not cards:
                # Try alternate selectors
                cards = soup.select("article.dealer, .dealer-result")
            if not cards:
                break
            for card in cards:
                name_el = card.select_one("h2, h3, .dealer-name, [data-qa='dealer-name']")
                addr_el = card.select_one(".dealer-address, address, [data-qa='dealer-address']")
                link_el = card.select_one("a[href*='dealer'], a.dealer-link")
                dealer_url = None
                if link_el:
                    href = link_el.get("href", "")
                    if href.startswith("http"):
                        dealer_url = href
                dealers.append({
                    "name": name_el.get_text(strip=True) if name_el else "Unknown",
                    "address": addr_el.get_text(strip=True) if addr_el else "",
                    "url": dealer_url,
                    "brand": brand,
                    "state": state,
                })
            # Check for next page
            next_btn = soup.select_one("a[rel='next'], .pagination-next, [data-qa='next-page']")
            if not next_btn:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  [warn] cars.com error for {brand}/{state} p{page}: {e}")
            break
    return dealers


# ── Brand locator API fetcher ─────────────────────────────────────────────────

# NY + NJ zip codes spread across the states for broad coverage
NY_NJ_ZIPS = [
    "10001",  # Manhattan
    "11201",  # Brooklyn
    "11101",  # Queens
    "10451",  # Bronx
    "10301",  # Staten Island
    "10601",  # Westchester
    "11901",  # Long Island (Suffolk)
    "11501",  # Long Island (Nassau)
    "12601",  # Hudson Valley
    "12901",  # Albany/North NY
    "13201",  # Syracuse
    "14201",  # Buffalo
    "14601",  # Rochester
    "07001",  # Newark NJ
    "07401",  # Northern NJ
    "07701",  # Monmouth NJ
    "08701",  # Central NJ
    "08401",  # Atlantic City NJ
    "08301",  # South NJ
]


def get_dealers_via_brand_api(brand: str) -> list[dict]:
    """Try brand-specific JSON APIs for dealer lists."""
    dealers = []

    if brand == "bmw":
        for zip_code in ["10001", "07001", "14201", "12901"]:
            try:
                url = (
                    f"https://www.bmwusa.com/dealer/api/v3/dealers/search"
                    f"?zip={zip_code}&radius=150&brands=BMW"
                )
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for d in data.get("dealers", data if isinstance(data, list) else []):
                        state = d.get("address", {}).get("state", d.get("state", ""))
                        if state in ("NY", "NJ"):
                            dealers.append({
                                "name": d.get("name", d.get("dealerName", "")),
                                "address": (
                                    f"{d.get('address', {}).get('street', '')} "
                                    f"{d.get('address', {}).get('city', '')} "
                                    f"{state}"
                                ).strip(),
                                "url": d.get("website", d.get("websiteUrl", "")),
                                "brand": brand,
                                "state": state,
                            })
            except Exception as e:
                print(f"  [warn] BMW API error zip={zip_code}: {e}")

    elif brand == "toyota":
        try:
            for state_code in ["NY", "NJ"]:
                url = (
                    f"https://www.toyota.com/configurator/pub/ext/dealer/search"
                    f"?zipCode=10001&distance=500&brand=TOYOTA&state={state_code}"
                )
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for d in data.get("dealers", []):
                        dealers.append({
                            "name": d.get("name", ""),
                            "address": f"{d.get('address1','')} {d.get('city','')} {d.get('state','')}".strip(),
                            "url": d.get("website", ""),
                            "brand": brand,
                            "state": d.get("state", state_code),
                        })
        except Exception as e:
            print(f"  [warn] Toyota API error: {e}")

    # Deduplicate by name
    seen = set()
    unique = []
    for d in dealers:
        key = d["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


# ── Browser-based staff page scraper ─────────────────────────────────────────

def get_browser_page():
    """Get or create a shared Playwright browser page."""
    global _playwright, _browser, _page
    if _page is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=True)
        context = _browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        _page = context.new_page()
    return _page


def find_staff_page(base_url: str) -> tuple:
    """
    Try common staff page paths on the dealer's website using a real browser.
    Returns (staff_page_url, list of staff dicts).
    """
    if not base_url:
        return None, []

    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    page = get_browser_page()

    for path in STAFF_PATHS:
        url = root + path
        try:
            resp = page.goto(url, timeout=12000, wait_until="domcontentloaded")
            if not resp or resp.status not in (200, 304):
                continue
            page.wait_for_timeout(1500)
            html = page.content()
            if not EMAIL_RE.search(html):
                continue
            staff = extract_staff(html, url)
            if staff:
                return url, staff
        except Exception:
            continue
    return None, []


def extract_staff(html: str, page_url: str) -> list:
    """Extract staff members (name, title, email, phone) from HTML."""
    soup = BeautifulSoup(html, "lxml")
    staff = []

    # Strategy 1: find mailto links with surrounding context
    for a in soup.select("a[href^='mailto:']"):
        email = a["href"].replace("mailto:", "").split("?")[0].strip()
        if not email or "@" not in email:
            continue

        container = a
        for _ in range(5):
            container = container.parent
            if container is None:
                break
            text = container.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if l.strip() and "@" not in l]
            if len(lines) >= 1:
                name = lines[0] if lines else ""
                title = lines[1] if len(lines) > 1 else ""
                if len(name) < 60:
                    phone_match = re.search(r"\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}", text)
                    phone = phone_match.group(0) if phone_match else ""
                    staff.append({"name": name, "title": title, "email": email, "phone": phone})
                    break

    # Strategy 2: regex scan for any remaining emails
    raw_emails = set(EMAIL_RE.findall(html))
    existing_emails = {s["email"].lower() for s in staff}
    for email in raw_emails:
        if email.lower() not in existing_emails:
            staff.append({"name": "", "title": "", "email": email, "phone": ""})

    seen = set()
    unique = []
    for s in staff:
        key = s["email"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def close_browser():
    global _playwright, _browser, _page
    try:
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception:
        pass


# ── Markdown writer ───────────────────────────────────────────────────────────

def dealer_to_section(dealer: dict, staff: list, staff_url) -> str:
    name = dealer.get("name", "Unknown Dealer")
    address = dealer.get("address", "")
    website = dealer.get("url", "")
    state = dealer.get("state", "")

    lines = [f"## {name}"]
    if address:
        lines.append(f"**Address:** {address}")
    if website:
        lines.append(f"**Website:** {website}")
    if staff_url:
        lines.append(f"**Staff page:** {staff_url}")
    lines.append("")

    if not staff:
        lines.append("_No staff directory found._")
        lines.append("")
        return "\n".join(lines)

    # Group by rough department heuristic based on title keywords
    dept_map: dict[str, list[dict]] = {}
    dept_order = []

    dept_keywords = {
        "Service": ["service advisor", "service manager", "service director", "service"],
        "Parts": ["parts manager", "parts advisor", "parts director", "parts"],
        "Sales": ["sales manager", "client advisor", "sales advisor", "sales consultant",
                  "sales", "client", "business manager"],
        "Finance": ["finance", "f&i", "business manager"],
        "General Management": ["general manager", "general sales", "principal", "dealer principal", "gm"],
        "Marketing": ["marketing"],
        "Human Resources": ["human resources", "hr"],
        "Other": [],
    }

    def classify(title: str) -> str:
        t = title.lower()
        for dept, keywords in dept_keywords.items():
            if any(k in t for k in keywords):
                return dept
        return "Other"

    for s in staff:
        dept = classify(s.get("title", ""))
        if dept not in dept_map:
            dept_map[dept] = []
            dept_order.append(dept)
        dept_map[dept].append(s)

    for dept in dept_order:
        members = dept_map[dept]
        lines.append(f"### {dept}")
        lines.append("")
        lines.append("| Name | Title | Email | Phone |")
        lines.append("|------|-------|-------|-------|")
        for m in members:
            lines.append(
                f"| {m.get('name','')} | {m.get('title','')} "
                f"| {m.get('email','')} | {m.get('phone','')} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_brand_file(brand: str, dealer_sections: list[str]):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{brand.replace(' ', '-')}.md")
    brand_display = brand.replace("-", " ").title()
    header = f"# {brand_display} Dealerships — New York & New Jersey\n\n"
    header += f"_Scraped from official dealer staff pages. {len(dealer_sections)} dealerships found._\n\n---\n\n"
    content = header + "\n\n---\n\n".join(dealer_sections)
    with open(path, "w") as f:
        f.write(content)
    print(f"  → Written: {path}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def load_curated_dealers(brand: str) -> list[dict]:
    """Load curated dealer list from JSON file."""
    json_path = os.path.join(os.path.dirname(__file__), "curated_dealers.json")
    if not os.path.exists(json_path):
        return []
    with open(json_path) as f:
        data = json.load(f)
    return data.get(brand, [])


def process_brand(brand: str):
    print(f"\n{'='*60}")
    print(f"  BRAND: {brand.upper()}")
    print(f"{'='*60}")

    unique_dealers = load_curated_dealers(brand)
    print(f"  Curated dealers: {len(unique_dealers)}")

    if not unique_dealers:
        print("  [skip] No dealers in curated list")
        return

    # Step 2: Scrape staff pages
    dealer_sections = []
    for i, dealer in enumerate(unique_dealers):
        name = dealer.get("name", "?")
        url = dealer.get("url", "")
        print(f"  [{i+1}/{len(unique_dealers)}] {name} — {url or 'no URL'}")

        if not url:
            section = dealer_to_section(dealer, [], None)
            dealer_sections.append(section)
            continue

        staff_url, staff = find_staff_page(url)
        if staff:
            print(f"    ✓ {len(staff)} staff found at {staff_url}")
        else:
            print(f"    ✗ No staff page")
        section = dealer_to_section(dealer, staff, staff_url)
        dealer_sections.append(section)
        time.sleep(0.3)  # polite crawl delay

    # Step 3: Write markdown file
    write_brand_file(brand, dealer_sections)


def main():
    brands_to_run = sys.argv[1:] if len(sys.argv) > 1 else BRANDS
    try:
        for brand in brands_to_run:
            try:
                process_brand(brand)
            except Exception as e:
                print(f"  [ERROR] {brand}: {e}")
    finally:
        close_browser()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()
