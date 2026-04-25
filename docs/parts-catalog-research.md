# OEM Parts Catalog Data Sources — Source of Truth Research

> Last updated: 2026-04-24
> Scope: OEM-direct sources only. Third-party aggregators (TecDoc, Mitchell1, ALLDATA, etc.) are excluded unless a manufacturer's data is only accessible that way (noted explicitly).
> Purpose: Help a developer building an AI-powered auto shop assistant decide what official parts data to purchase.

---

## How to Read This Document

Each entry covers the manufacturer's **official** EPC (Electronic Parts Catalog) — the system the dealership uses, not aftermarket databases.

| Field | Meaning |
|---|---|
| **Official EPC** | The name of the manufacturer's own catalog system |
| **Access** | Where to get it (URL or description) |
| **Format** | How data is delivered: Windows app, web portal, downloadable file |
| **Pricing** | Cost as accurately known; `~` means approximate; "contact for quote" means not public |
| **Raw data export** | Whether you can get CSV/SQL/JSON instead of being locked in a UI |
| **Coverage** | Vehicle years, brands, regions |
| **Notes** | Gray-market alternatives, known quirks, developer tips |

**On gray-market copies:** Many EPC systems are available as pirated DVD/VMware images sold on eBay, forums, and third-party resellers for $10–$150. These are noted where relevant as "gray-market available" — they are mentioned for research awareness, not endorsement.

---

## American OEMs

### Ford Motor Company

**Brands:** Ford, Lincoln
**Official EPC:** Ford Microcat Live (global); OASIS (dealer internal service/warranty system)
**Access:**
- Microcat Live: dealer-only portal; not sold directly to non-dealers
- OASIS (Online Automotive Service Information System): strictly dealer/Ford-employee only — `fordtechservice.dealerconnection.com` — no public access
- Ford service information (repair manuals, wiring, TSBs — **not parts catalog**) for non-dealers: `motorcraftservice.com` or via third-party resellers (~$3,199/year for a 1-year subscription through AE Solutions)
- For fleet/wholesale parts lookup: Ford Parts and Service hub at `toyotapartsandservice.com` (public-facing parts ordering only)

**Format:** Web portal (Microcat Live); Windows desktop (older Microcat DVD versions still in circulation)
**Pricing:**
- Dealer access: included in dealer agreements — no standalone purchase
- Non-dealer service info (NOT parts catalog): ~$3,199/year (includes repair procedures, wiring, TSBs — no parts EPC)
- Gray-market Ford Microcat DVDs: $30–$150 on eBay
**Raw data export:** No — the official system is a closed web portal; no public API or data export
**Coverage:** All Ford/Lincoln model years; global markets including North America, Europe, Asia
**Notes:**
- OASIS contains warranty/recall/service history per VIN — it is **not a parts catalog**, it is a dealer service record system. They are frequently confused in forums.
- Microcat Live is the genuine parts lookup tool used by dealer parts departments. Non-dealer access is not offered.
- autodb.cc (see Developer Data Sources section) offers a converted Ford Microcat database in MySQL/MSSQL for €1,000 + €250/update. This is the clearest path to raw Ford parts data for a developer.

---

### General Motors

**Brands:** Chevrolet, GMC, Buick, Cadillac, (historically Pontiac, Oldsmobile, Saturn, Hummer)
**Official EPC:** GM Global EPC / GMNA EPC (North America) — built and maintained by Snap-on Business Solutions
**Access:**
- Dealer access: `sbs.snapon.com/automotive/epc/gmglobalepc/` — requires dealer license agreement
- Non-dealer service information (repair manuals, diagnostics): ACDelco TDS at `acdelcotds.com` — available to independent shops and enthusiasts; ~$45/year for programming file access (SI service info tier is separate)
- Parts catalog specifically: accessed through GM dealer parts systems — not available independently

**Format:** Web portal (GM Global EPC Online); also available as offline Windows application
**Pricing:**
- Dealer EPC license: ~$125/license (Snap-on quote, per forum reports)
- ACDelco TDS (service info, not parts EPC): ~$45/year base; higher tiers for diagnostics/programming
- Gray-market GMNA EPC VMware images: $50–$100 from third-party sites
**Raw data export:** No — EPC is a closed Snap-on-hosted system; no API or data dump
**Coverage:** 1953–present; North America (GMNA) and International (GMIO) versions; GMIO covers markets outside North America
**Notes:**
- GM Parts (`gmparts.com`) is the public-facing parts lookup — it shows part numbers but is not the full dealer EPC (no pricing, no supersession chains, limited diagrams)
- autodb.cc lists a "GM Opel/Chevrolet/North America" database conversion — contact them for pricing
- For independent shops needing service info (not parts), ACDelco TDS is the legitimate, affordable route

---

### Stellantis US (FCA group)

**Brands:** Chrysler, Dodge, Jeep, Ram, Fiat (US), Alfa Romeo (US)
**Official EPC:** FCA Snap-on EPC 5 (EPC5); service/repair info via TechAuthority
**Access:**
- EPC5 (parts catalog): dealer-only Snap-on system; no direct non-dealer purchase
- TechAuthority (service info + parts identification): `techauthority.com` — available to non-dealers; 3-day, 30-day, and 1-year subscriptions
- Independent operator registration: `stellantisiop.com` for registering as an independent repair shop

**Format:** Web portal (EPC5 Online); older DVD/offline versions available
**Pricing:**
- TechAuthority 1-year subscription: ~$1,978/year (per third-party reseller pricing at Diagnoex)
- 3-day and 30-day subscriptions available at lower price points (exact pricing at `techauthority.com`)
- Gray-market EPC5 VMware images: $50–$100
**Raw data export:** No — closed system
**Coverage:** Chrysler/FCA brands ~1984–present; all major global markets; US, Canada, Mexico, Export
**Notes:**
- TechAuthority is the official, legitimate non-dealer path for service/repair information — includes parts identification but through a UI, not raw export
- Mopar (`mopar.com`) is the consumer-facing parts shopping site — not the dealer EPC
- Fiat/Alfa Romeo EU brands (Fiat, Lancia, Abarth) use a separate system (see Stellantis EU below)

---

## European OEMs

### BMW Group

**Brands:** BMW, MINI, Rolls-Royce, BMW Motorrad
**Official EPC:** ETK (Elektronischer Teile Katalog)
**Access:**
- Official dealer ETK: embedded in BMW dealer DMS — not sold standalone to non-dealers
- Aftersales Online System (AOS) for independent workshops: `aos.bmwgroup.com` — the official path for independent shops; **parts catalog access is free** after registration; paid tiers for repair documentation and software downloads
- Parts catalog (ETK equivalent) within AOS: free registration, free access

**Format:** Web portal (AOS/ETK Online); older ETK was a Windows Transbase application (discontinued for new users)
**Pricing:**
- AOS registration and parts catalog access: **Free**
- AOS repair info / technical documentation: subscription required (pricing at AOS portal)
- Raw ETK database conversion (developer use): €800 one-time + €250/update from autodb.cc
- JSON API on top of ETK data: €2,000 one-time or €200+/month from autodb.cc
- Gray-market ETK DVD/VMware: $30–$100 (outdated data, not recommended)
**Raw data export:** No official export from AOS; autodb.cc offers converted database (MySQL/MSSQL, ~3–5 GB) from the offline ETK Transbase format
**Coverage:** BMW/MINI/Rolls-Royce cars from 1932; motorcycles from 1948; all global markets
**Notes:**
- **AOS is the recommended official path for any non-dealer developer.** The parts catalog is genuinely free — registration is open to independent workshops worldwide.
- ETK data is structured: model → group → subgroup → position → part number, with prices and supersessions
- `realoem.com` and `bmwfans.info/parts-catalog` are free third-party mirrors of ETK data — useful for validation
- BMW has separate car-data APIs (`bmw-cardata.bmwgroup.com`) for connected car data — not parts data
- **Developer recommendation:** Start with AOS (free parts lookup), then evaluate autodb.cc for bulk database if needed (~€800 for a MySQL dump)

---

### Volkswagen Group

**Brands:** Volkswagen, Audi, SEAT, Škoda, Cupra; **Porsche** uses the same structure but a separate system (PET)
**Official EPC:** ETKA (Elektronischer Teile Katalog Audi/VW); as of ETKA 8.6, includes workshop manual pages
**Access:**
- Dealer ETKA: available only to authorized VW Group partners via dealer agreements
- **Partslink24** (`partslink24.com`): the official VW Group solution for non-dealers — "if you are not an authorized partner of the Volkswagen Group, but would still like to access the complete original parts information, partslink24 is the tool for you" (direct quote from etka.com)
- Partslink24 pricing: ~$20/day, ~$50/month, ~$480/year (older forum-reported figures; current pricing at partslink24.com — US access may be free for US market catalog only per some reports)

**Format:** Web portal (Partslink24 for non-dealers); ETKA is a Windows desktop application for dealers
**Pricing:**
- ETKA dealer license: contact VW Group; not publicly priced for outsiders
- Partslink24 non-dealer: ~$480/year (full access); limited US-only access may be free
- Raw ETKA database conversion: €800 one-time + €250/update from autodb.cc; JSON API: €2,500 one-time or €200+/month
- Gray-market ETKA: widely available for $30–$100, typically v8.x
**Raw data export:** No official export; autodb.cc conversion available (MySQL/MSSQL with diagrams)
**Coverage:** VW, Audi, SEAT, Škoda — all global markets; historical data back to 1960s for some models
**Notes:**
- Partslink24 covers 43 brands and 15.3 million parts — it is the official OEM channel for non-dealers
- Porsche PET (Porsche Elektronischer Teile Katalog) is a **separate system** from ETKA, also maintained by LexCom. Porsche dealers use PET2; some versions have been made publicly downloadable by Porsche. autodb.cc offers Porsche PET database for €1,000 + €300/update.
- Lamborghini and Bentley (also VW Group brands) use dealer-internal systems — no confirmed independent access pathway found

---

### Mercedes-Benz

**Brands:** Mercedes-Benz passenger cars, Mercedes-Benz Vans, Mercedes-Benz Trucks, Smart, Maybach
**Official EPC:** EWA Net (Electronic Workshop Access Network); the parts module is called EPC within EWA Net
**Access:**
- Dealer system: XENTRY platform — dealer-only, very expensive ($3,500+/year for WIS alone)
- **Independent / non-dealer access**: Mercedes AfterSales Platform at `aftersales.mercedes-benz.com` — registration is open; **EPC (parts catalog) subscription: ~$110/year**
- Alternative: Startek / ISPPI at `startekinfo.com/parts` — ~$92/year, provides EPC access for independent shops

**Format:** Web portal (AfterSales platform and Startek); older EWA Net was a Windows desktop application (discontinued for new users)
**Pricing:**
- EPC-only subscription (non-dealer): ~$110/year via official AfterSales platform
- XENTRY (full dealer diagnostic suite): not available to non-dealers; dealer licensing cost is $3,500+/year for WIS/DAS alone; flash programming is ~$16,000 per 4-year block
- ISPPI/Startek alternative: ~$92/year
- Raw EWA Net database conversion: €800 one-time + updates from autodb.cc; JSON API: €2,000
**Raw data export:** No official export; autodb.cc conversion available
**Coverage:** All Mercedes-Benz passenger cars, vans, trucks, Smart, Maybach — global markets; all model years
**Notes:**
- The ~$110/year AfterSales EPC subscription is the most accessible official path for non-dealers
- `nemigaparts.com` provides free EPC part number lookups — useful for spot-checking but not bulk data
- The official AfterSales portal allows free browsing but requires subscription for full VIN-specific data

---

### Stellantis EU (PSA / FCA merged)

**Brands:** Peugeot, Citroën, DS Automobiles, Opel/Vauxhall; **also Alfa Romeo, Fiat, Lancia, Abarth** (FCA legacy)

#### PSA brands (Peugeot, Citroën, DS, Opel/Vauxhall)
**Official EPC:** ServiceBox (`servicebox.mpsa.com` / `public.servicebox.peugeot.com`)
**Access:** Open registration for independent operators (EU VAT number required; non-EU access is difficult — some users report being blocked without a European business ID)
**Format:** Web portal
**Pricing:** ~€8.80/hour pay-as-you-go; subscription tiers available (contact ServiceBox for current pricing; access from the US is reportedly difficult without an EU VAT ID)
**Raw data export:** No
**Coverage:** Peugeot, Citroën, DS, Opel/Vauxhall — all models, global markets
**Notes:** US-based shops have reported difficulty registering without a European business VAT ID. The official independent operator path is `stellantisiop.com`, but registration may require proof of being an automotive repair business.

#### FCA legacy brands (Fiat, Alfa Romeo, Lancia, Abarth, Maserati)
**Official EPC:** ePER (Fiat Spare Parts Catalog); accessed via `technicalinformation.fiat.com`
**Access:** Requires "Spare Parts" subscription; the older public ePER at `eper.fiatforum.com` has historical data. Registration available at `technicalinformation.fiat.com`.
**Format:** Web-based (formerly Internet Explorer-only; modernized)
**Pricing:** Subscription required — pricing not publicly listed; contact via Stellantis IOP portal
**Raw data export:** No
**Coverage:** Fiat, Alfa Romeo, Lancia, Abarth, Maserati — global markets; historical models available
**Notes:** Maserati technical information is also accessible via the same Stellantis technical information portal. Heritage parts for older models available via `stellantisheritage.com`.

---

### Renault Group

**Brands:** Renault, Dacia, Alpine (Lada, Renault Samsung in historical data)
**Official EPC:** Dialogys / RParts (Renault Parts)
**Access:** `rpartstore.renault.com` — official Renault parts portal; Dialogys EPC Online for dealer/workshop use
**Format:** Web portal (current); older Dialogys was a Windows application with DVDs
**Pricing:** Subscription required — pricing not publicly listed; contact Renault Group dealer relations. Some third-party sites indicate Dialogys access is available through authorized distributor agreements.
**Raw data export:** No known official export
**Coverage:** Renault, Dacia, Alpine, Renault Samsung — all global markets up to present
**Notes:** The public-facing `rpartstore.renault.com` allows part number lookups by model but is designed for ordering, not bulk data. Full Dialogys access is restricted to authorized repair businesses.

---

### Volvo Cars

**Brands:** Volvo Cars (passenger vehicles; separate from Volvo Trucks)
**Official EPC:** VIDA (Vehicle Information and Diagnostics for Aftersales) — includes parts catalog as a module
**Access:** `tis.volvocars.biz` (purchase) and `volvotechinfo.com/vida/purchase` (North America) — open to independent workshops worldwide; 37 markets supported
**Format:** Web portal
**Pricing (North America, from official Volvo TIS):**
| Tier | 3 Days | 30 Days | 365 Days |
|---|---|---|---|
| Parts Catalog only | $11.30 | $34.45 | **$210.80** |
| Parts + Service Info | $21.04 | $184.96 | $2,213.06 |
| Parts + Service + Diagnostics | $48.15 | $417.93 | $4,860.29 |
| All + Software Download | $73.14 | $648.22 | $7,547.76 |

**Raw data export:** No
**Coverage:** All Volvo Cars models — global markets; all years
**Notes:**
- **Best-documented official pricing among all OEMs researched.** The $210.80/year parts-only tier is exceptional value for a developer needing Volvo parts data access.
- Polestar: as a Geely/Volvo sub-brand, Polestar parts are accessible via VIDA; no separate Polestar EPC confirmed.
- Volvo Trucks uses a **separate** system called Volvo IMPACT — do not confuse with VIDA

---

### Jaguar Land Rover

**Brands:** Jaguar, Land Rover, Range Rover
**Official EPC:** JLR EPC at `jlrepc.com`
**Access:** Open registration for authorized independent users in addition to dealers/retailers; registration required at `jlrepc.com`
**Format:** Web portal
**Pricing:** Not publicly listed; dealer and authorized independent pricing — contact JLR aftersales
**Raw data export:** No
**Coverage:** Jaguar and Land Rover vehicles 1961–present; global markets; multilingual
**Notes:** JLR EPC distinguishes between "JLR Internal," "Retailers," and "Authorized Independent" user tiers. The independent tier requires a registration/verification step. Gray-market versions widely sold on enthusiast forums.

---

### Aston Martin

**Brands:** Aston Martin
**Official EPC:** Aston Martin Parts Catalogue — listed as "factory service technical support engineering department version"
**Access:** Dealer-only; no confirmed independent workshop access path found
**Format:** Windows application (XP through Windows 11 compatible per reseller listings)
**Pricing:** Not publicly available; contact Aston Martin dealer relations
**Raw data export:** No
**Coverage:** All Aston Martin production models 1996–present
**Notes:** The catalog appears to be sold through dealer licensing only. Third-party resellers (cars-technical.com) offer versions for ~$200–$500 — these are gray-market copies. No official non-dealer purchase path confirmed.

---

### Ferrari

**Brands:** Ferrari
**Official EPC:** Ferrari Spare Parts Catalogue (no widely-used branded acronym found)
**Access:** Dealer-only; Ferrari's tight control over technical data means no public independent access path has been confirmed
**Format:** Windows application (multilingual: English, Italian, German, French, Spanish, Chinese, Japanese)
**Pricing:** Not publicly available
**Raw data export:** No
**Coverage:** Ferrari models 1986–present; global markets
**Notes:** Ferrari is notably restrictive about technical data access — even repair manuals are hard to obtain legitimately. Third-party listings (cars-technical.com) offer "2013–2026 Ferrari Spare Parts Catalog" for ~$200, which appear to be gray-market distributions. No official non-dealer path found.

---

### Lotus

**Brands:** Lotus Cars
**Official EPC:** Lotus Parts Online EPC
**Access:** Credentials supplied by Lotus via email — appears to be available to authorized dealers and distributors; limited confirmed information on independent access
**Format:** Web portal
**Pricing:** "Month-to-month contracts" — no specific pricing found publicly
**Raw data export:** No confirmed export
**Coverage:** Current and recent Lotus models
**Notes:** Lotus underwent significant restructuring (now Geely-owned); the EPC infrastructure may be in transition. The knowledge base article was found but is now returning a 404, suggesting the platform is being updated. Contact Lotus Cars directly for current access procedures.

---

## Asian OEMs

### Toyota Group

**Brands:** Toyota, Lexus, Scion (discontinued)
**Official EPC:** Toyota Microcat Live (parts catalog); Toyota TIS (Technical Information System) for repair/service info
**Access:**
- **Microcat Market** (parts ordering): `toyotapartsandservice.com` — **free for independent repair shops**; web-based parts catalog and ordering system
- **Toyota TIS** (service/repair info, includes parts): `techinfo.toyota.com` — open subscriptions; available to anyone
- Microcat Live for dealer ordering: dealer-specific login required

**Format:** Web portal
**Pricing (Toyota TIS):**
- Standard (service info only): ~$505/year or ~$1.39/day
- Professional Diagnostic (service info + Techstream): ~$1,360/year
- Microcat Market: **Free** for independent shops
**Raw data export:** No official export; Microcat data is locked in the portal
**Coverage:** Toyota, Lexus, Scion — all markets; all years; global coverage via separate regional catalogs
**Notes:**
- Toyota dealers can sponsor up to 8 independent shops per year with free TIS subscriptions — worth asking your local Toyota dealer
- Microcat is made by Infomedia Ltd. (Australian company) — they power Toyota's EPC but also sell Microcat to other OEMs (Honda, Hyundai, Nissan, etc.)
- Daihatsu: separate EPC; limited market presence outside Japan and Southeast Asia — no confirmed non-dealer access path

---

### Honda / Acura

**Brands:** Honda, Acura
**Official EPC:** Honda iN (Interactive Network) — the dealer portal; parts lookup is via Honda's internal Microcat-based EPC
**Access:**
- Dealer access: `in.honda.com` — restricted to authorized Honda/Acura dealership staff
- Non-dealer: Honda does not offer a publicly accessible EPC subscription for independent shops (unlike Toyota)
- Parts lookup for customers/shops: authorized Honda dealers provide part numbers; some authorized wholesale portals exist

**Format:** Web portal (dealer-only)
**Pricing:** No public non-dealer pricing; dealer access is part of Honda dealer agreements
**Raw data export:** No
**Coverage:** Honda and Acura — all markets, all years
**Notes:**
- Honda is more restrictive than Toyota for non-dealer parts data access
- Public part number lookup is available through Honda parts dealer websites (e.g., hondapartsnow.com) but these are consumer retail sites, not bulk data
- For independent shops, the Honda parts ordering system is accessed through authorized wholesale accounts at local Honda dealers

---

### Nissan / Infiniti

**Brands:** Nissan, Infiniti
**Official EPC:** FAST (Fully Assisted Service Terminal) — also called Nissan EPC; the system handles both Nissan and Infiniti
**Access:**
- Dealer access: dealer DMS-integrated; not available as a standalone non-dealer subscription
- Non-dealer: `nissanfast.info` is a community guide/documentation site; the official FAST system is dealer-internal
- Parts shopping: `parts.nissanusa.com` (consumer retail only)

**Format:** Windows DVD application (FAST); web-based version used internally at dealers
**Pricing:** Dealer-only; not publicly priced for independent access
**Raw data export:** No official export
**Coverage:** Nissan and Infiniti — all markets; Japan, USA, Europe, Asia/Pacific; all years
**Notes:**
- Nissan FAST is a classic DVD-era catalog; gray-market DVD versions are commonly available for $30–$80 (data is dated, typically 2019 or earlier)
- No official non-dealer subscription path confirmed as of this research

---

### Hyundai / Kia Group

**Brands:** Hyundai, Kia, Genesis
**Official EPC:** MOBIS WPC (Web Parts Catalog) — also known as Snap-on EPC version and Microcat version, all reflecting the same underlying Hyundai Mobis parts data
**Access:**
- Dealer access: via Hyundai/Kia dealer DMS; MOBIS WPC is the primary system
- Non-dealer: `globalparts.hyundai.com` for Hyundai; parts lookup available via authorized distributor accounts. No direct independent subscription for raw EPC confirmed.
- Some authorized independent workshop access may be available via regional Hyundai/Kia aftersales portals

**Format:** Web portal
**Pricing:** Not publicly listed for non-dealer access; dealer subscriptions via Hyundai Mobis
**Raw data export:** No confirmed export
**Coverage:** Hyundai, Kia, Genesis — all global markets; all years
**Notes:**
- Hyundai Mobis (`mobis.co.kr`) is the official parts brand/distributor; MOBIS WPC is the dealer parts catalog
- Third-party providers (autopartscatalogue.net, autotech4you.com) sell access to the online EPC — these are likely using shared dealer login accounts, which is a gray area
- GDS (Global Diagnostic System) is a separate diagnostic tool, not the parts catalog

---

### Mazda

**Brands:** Mazda
**Official EPC:** Mazda EPC (no distinct branded name; sometimes called MEPCO internally)
**Access:**
- Dealer access: Mazda dealer DMS; not available as a standalone non-dealer subscription
- Non-dealer: `classicmazdaepc.de` provides free access to older/classic Mazda EPC data (community-maintained)
- Consumer parts ordering: `mazdausa.com` dealer parts locator

**Format:** Web portal (current); older versions were DVD-based Windows applications
**Pricing:** Not publicly available for non-dealer access; dealer pricing via Mazda aftersales agreements
**Raw data export:** No confirmed export
**Coverage:** Mazda — all global markets (RHD and LHD versions); 1985–present in most recent releases
**Notes:**
- Mazda's EPC covers both right-hand-drive (Japan, UK, Australia) and left-hand-drive markets with separate catalog trees
- No confirmed official non-dealer access path for the current EPC system

---

### Subaru

**Brands:** Subaru
**Official EPC:** Subaru Fast EPC / Subaru Snap-on EPC (the official system powering dealer parts lookup; no distinctive brand name widely used)
**Access:**
- Dealer access: Subaru dealer DMS; dealer portal is internal
- Non-dealer: `parts.subaru.com` (Subaru of America official site) — allows parts browsing by VIN/model but is a retail ordering interface, not a full dealer EPC
- No confirmed standalone non-dealer subscription for the dealer-level EPC

**Format:** Web portal
**Pricing:** Not publicly available for non-dealer dealer EPC access
**Raw data export:** No confirmed export
**Coverage:** All Subaru models — North America, Japan, Europe; all years
**Notes:**
- Subaru of America's `parts.subaru.com` is publicly accessible for part number lookup — good for consumer/enthusiast use but not bulk data extraction
- Gray-market Subaru EPC DVD versions are available; typically outdated

---

### Mitsubishi

**Brands:** Mitsubishi
**Official EPC:** Mitsubishi ASA EPC (All Service Access)
**Access:**
- Dealer access: Mitsubishi dealer DMS; not publicly available
- Non-dealer: No confirmed official subscription path; third-party resellers (OBDTotal, autotech4you) sell access
**Format:** Windows application; web-based version for dealers
**Pricing:** Not publicly available for official access; gray-market Windows installs: ~$50–$150
**Raw data export:** No official export; autodb.cc offers Mitsubishi ASA database conversion for €1,000 one-time + €800/update; JSON API €3,000 or €200+/month
**Coverage:** All Mitsubishi passenger cars, SUVs, pickups — all global markets; all years; Japan, Europe, Asia, USA
**Notes:**
- Mitsubishi Fuso (trucks) uses a separate EPC system
- autodb.cc's Mitsubishi ASA conversion is the clearest developer path for raw Mitsubishi parts data

---

### Suzuki

**Brands:** Suzuki (automotive)
**Official EPC:** Suzuki Snap-on EPC (worldwide automotive EPC)
**Access:**
- Dealer access: Suzuki dealer DMS; Snap-on hosts the system
- `suzuki.snaponepc.com` — appears to be the official Snap-on hosted portal; access terms unclear (may require dealer credential)
**Format:** Web portal (no installation required)
**Pricing:** Not publicly listed; some third-party resellers offer 1-year subscriptions; contact Suzuki aftersales for official pricing
**Raw data export:** No confirmed export
**Coverage:** Global Suzuki automotive lineup — all years; all global markets (Jimny through current hybrid/EV models)
**Notes:**
- Suzuki's automotive EPC is distinct from their motorcycle/ATV catalog
- The official Snap-on portal at `suzuki.snaponepc.com` suggests Suzuki has chosen the Snap-on hosted model similar to GM/Ford

---

### Isuzu

**Brands:** Isuzu (trucks, SUVs, buses, industrial engines)
**Official EPC:** Isuzu EQ-Hit EPC (current); CSS-Net (predecessor); Snap-on EPC (older)
**Access:**
- Dealer access: `isuzutruckepc.com` — appears to be the official US truck EPC portal
- EQ-Hit EPC Online: web-based, described as dealer/workshop system
**Format:** Web portal (EQ-Hit); older versions were DVD Windows applications
**Pricing:** Not publicly listed; contact Isuzu aftersales
**Raw data export:** No confirmed export
**Coverage:** Isuzu trucks, buses, pickups, SUVs, and industrial/marine diesel engines — worldwide; all years
**Notes:**
- Isuzu's catalog is particularly important for commercial/fleet shops given their role in the N-series and F-series truck market
- The CSS-Net system covered Isuzu vehicles and engines comprehensively

---

## Chinese OEMs

### BYD

**Brands:** BYD (EV and PHEV passenger vehicles)
**Official EPC:** BYD EPC — official system at `epc.bydauto.com.cn`
**Access:** Requires dealer login (username, dealer code, dealer name) — not publicly open; technical support via helpdesk-byd@servision.com.cn
**Format:** Web portal (requires dealer credentials)
**Pricing:** Not publicly available; dealer agreement required
**Raw data export:** No confirmed export
**Coverage:** BYD EV and PHEV models 2013–present including Atto2, Atto3, Seal, Seagull, Sealion, Dolphin, Qin, Han, Tang, Song, Yuan; multilingual (English, German, French, Arabic, Chinese)
**Notes:**
- As BYD expands into Western markets (Europe, Australia, Southeast Asia), dealer network infrastructure is being built out — EPC access for independent workshops in those markets is likely immature
- No confirmed path for non-dealer access as of this research

---

### SAIC Motor (MG, Roewe)

**Brands:** MG, Roewe (sold in China, Europe, Southeast Asia, Australia)
**Official EPC:** SAIC Motor EPC system (available as a Windows application)
**Access:** Not publicly available; the system is sold via third-party resellers as a VMware/Windows image (~$50–$100); no confirmed official non-dealer subscription portal
**Format:** Windows application (~3 GB)
**Pricing:** Not publicly available from SAIC directly
**Raw data export:** No confirmed export
**Coverage:** MG, Roewe, EMG6 models — primarily China and export markets; 2022–present in more recent releases
**Notes:**
- SAIC is a major Chinese OEM with growing Western market presence (MG brand especially in Europe and Australia)
- No official independent workshop access path confirmed for Western markets

---

### Geely Group

**Brands:** Geely, (parent company of Volvo Cars, Polestar, Lotus, Lynk&Co)
**Official EPC:** GEPC (Geely Electronic Parts Online Catalog) at `iepc.geely.com`
**Access:** Open registration for dealer network and authorized repair centers; web-based
**Format:** Web portal (no installation required)
**Pricing:** Not publicly listed; contact Geely dealer relations
**Raw data export:** No confirmed export
**Coverage:** Geely passenger vehicles — global markets; current models
**Notes:**
- Volvo Cars, Polestar, and Lotus are Geely subsidiaries but maintain entirely separate EPC systems (see individual entries)
- Lynk&Co uses a dealer-based service model; no separate EPC confirmed for international markets
- Geely's own Chinese-market vehicles are sold in Southeast Asia and some European markets

---

### Great Wall Motor / Haval

**Brands:** Great Wall Motor, Haval, ORA, Wey, Tank
**Official EPC:** No branded system name found; parts data appears to be distributed through regional dealer networks
**Access:** Not publicly available; contact Great Wall/Haval regional distributors
**Format:** Unknown
**Pricing:** Not publicly available
**Raw data export:** Unknown
**Coverage:** Great Wall, Haval SUVs, ORA EVs — primarily China and export markets (Australia, South Africa, Southeast Asia, Europe)
**Notes:**
- Great Wall's Western market presence is still developing; formal EPC infrastructure for independent shops in Western markets is unconfirmed
- Some parts suppliers (eliteparts.org) stock GWM/Haval parts; part number lookups may be available through regional Haval dealers

---

### Chery

**Brands:** Chery, Omoda, Jaecoo
**Official EPC:** No confirmed EPC system name for international markets
**Access:** Not publicly available for Western markets
**Format:** Unknown for Western markets
**Pricing:** Unknown
**Raw data export:** Unknown
**Coverage:** Primarily China-market vehicles; expanding internationally with Omoda/Jaecoo
**Notes:** Chery's Western market presence is very new. No formal independent workshop EPC access path found. Contact regional distributors.

---

### NIO / Li Auto / Xpeng

**Brands:** NIO, Li Auto, Xpeng (Chinese EV brands; limited US presence)
**Official EPC:** No publicly confirmed EPC system for Western markets; all three brands operate direct-to-consumer service models
**Access:** Proprietary service apps and portals for owners; no dealer-style EPC system confirmed
**Format:** Mobile apps / web portals for owner services
**Pricing:** Not applicable (no aftermarket parts market established in Western countries)
**Raw data export:** No
**Coverage:** China-market vehicles primarily; some NIO vehicles sold in Europe via NIO Houses
**Notes:**
- All three brands use software-defined vehicle architectures with OTA updates; traditional EPC systems may not apply
- NIO, Li Auto, and Xpeng have no significant US sales as of 2026 (various tariff/regulatory barriers)
- For Chinese-market parts lookup, the brands' official apps (NIO App, Li Auto App, Xpeng App) are the service gateways

---

## Summary Table

| Manufacturer | EPC Name | Non-Dealer Access? | Official Cost (parts catalog) | Raw Data Export? | Notes |
|---|---|---|---|---|---|
| Ford | Microcat Live / OASIS | No (dealer-only) | N/A | No | Service info (not parts): ~$3,199/yr |
| General Motors | GMNA EPC (Snap-on) | Limited (dealer/ACDelco TDS) | Not separately priced | No | ACDelco TDS ~$45/yr (SI, not parts EPC) |
| Stellantis US | FCA Snap-on EPC5 | Via TechAuthority (~$1,978/yr) | ~$1,978/yr | No | Includes parts ID via TechAuthority |
| BMW Group | ETK / AOS | **Yes — Free** (AOS) | **Free** | No (officially) | autodb.cc: €800 for MySQL dump |
| VW Group | ETKA | Via Partslink24 | ~$480/yr (Partslink24) | No (officially) | autodb.cc: €800 for MySQL dump |
| Porsche | PET2 | Limited (some public downloads) | N/A | No (officially) | autodb.cc: €1,000 for database |
| Mercedes-Benz | EWA Net / EPC | **Yes** (AfterSales platform) | **~$110/yr** | No | Startek: ~$92/yr alternative |
| Stellantis EU | ServiceBox / ePER | Yes (EU VAT required) | ~€8.80/hr or subscription | No | US access is difficult without EU VAT |
| Renault Group | Dialogys / RParts | Via authorized distributors | Not publicly listed | No | |
| Volvo Cars | VIDA | **Yes** (open subscription) | **$210.80/yr** (parts only) | No | Best-documented official pricing |
| JLR | JLR EPC | Yes (authorized independent tier) | Not publicly listed | No | Register at jlrepc.com |
| Aston Martin | AM Parts Catalogue | Dealer-only (unconfirmed) | Not available | No | Gray-market copies exist |
| Ferrari | Ferrari Parts Catalogue | Dealer-only | Not available | No | Very restrictive |
| Lotus | Lotus Parts Online EPC | Via email credentials | Not publicly listed | No | Platform may be in transition |
| Toyota | Microcat / TIS | **Yes** (Microcat Market free) | **Free** (Microcat Market) | No | TIS: ~$505/yr for repair info |
| Honda | Honda iN | Dealer-only | Not available | No | Less open than Toyota |
| Nissan/Infiniti | FAST | Dealer-only | Not available | No | Gray-market DVDs available |
| Hyundai/Kia | MOBIS WPC | Limited (dealer focus) | Not publicly listed | No | |
| Mazda | Mazda EPC | Dealer-only | Not available | No | Classic EPC: free via community site |
| Subaru | Subaru Snap-on EPC | Dealer-only | Not available | No | parts.subaru.com for retail lookups |
| Mitsubishi | ASA EPC | Dealer-only | Not available | No | autodb.cc: €1,000 DB + €800/update |
| Suzuki | Suzuki Snap-on EPC | Likely via suzuki.snaponepc.com | Not publicly listed | No | |
| Isuzu | EQ-Hit EPC | Via isuzutruckepc.com | Not publicly listed | No | |
| BYD | BYD EPC | Dealer-only | Not available | No | |
| SAIC/MG | SAIC EPC | Not officially | Not available | No | Windows app via resellers |
| Geely | GEPC (iepc.geely.com) | Yes (open registration) | Not publicly listed | No | |
| Great Wall/Haval | Unknown | No confirmed path | Not available | No | |
| Chery | Unknown | No confirmed path | Not available | No | |
| NIO/Li Auto/Xpeng | Owner apps only | No EPC system | N/A | No | Direct service model |

---

## Developer Data Sources (Raw Database Access)

For a developer who needs **structured parts data** (not just a web UI), the following are the most actionable paths:

### autodb.cc — Automotive EPC Database Conversion Service
**What it is:** A service that converts official EPC databases (extracted from dealer systems) into SQL/MySQL/MSSQL/CSV/JSON formats, plus JSON APIs.
**Brands covered:** ETKA (VW/Audi/Seat/Skoda), Porsche PET, BMW ETK, Mercedes-Benz EPC, Mitsubishi ASA, Ford Microcat (Europe/Asia/Africa/NA), FIAT ePER, GM (Opel/Chevrolet/NA), TecDoc, Bosch ESI[tronic]
**Contact:** autodb@list.ru

| Product | One-Time Price | Update Cost | API Option |
|---|---|---|---|
| ETKA (VW Group) | €800 | €250 | €2,500 or €200+/mo |
| Porsche PET | €1,000 | €300 | (included in ETKA API) |
| BMW ETK | €800 | N/A listed | €2,000 |
| Mercedes-Benz EPC | €800 | N/A listed | €2,000 |
| Mitsubishi ASA | €1,000 | €800 | €3,000 or €200+/mo |
| Ford Microcat | €1,000 | N/A listed | €3,000 or €200+/mo |
| FIAT ePER | €500 | N/A listed | N/A listed |

**Format:** MySQL / MSSQL / PostgreSQL with images converted to PNG; JSON API available (OpenAPI 3)
**Legal note:** Autodb.cc states "for backup purposes only" — the legal status of their conversions is ambiguous. The underlying data was extracted from dealer software. Consult a lawyer before building a commercial product on it.

### Partslink24 (VW Group official, non-dealer)
- Official URL: `partslink24.com`
- Covers all VW Group brands (43 brands, 15.3M parts)
- ~$480/year for full access; some markets may have free access to local catalog
- This is **legitimate and official** — VW Group explicitly positions it as the non-dealer option

### BMW AOS (BMW Group official, free)
- Official URL: `aos.bmwgroup.com`
- Parts catalog access is **free** after registration
- Designed for independent workshops but open to anyone with a legitimate need
- No raw data export, but free UI access to ETK data

### Mercedes-Benz AfterSales Platform (official, ~$110/yr)
- Official URL: `aftersales.mercedes-benz.com`
- ~$110/year for EPC (parts catalog) access
- VIN-specific parts lookup, pricing, diagrams
- No raw data export

### Volvo VIDA (official, $210.80/yr for parts-only)
- Official URL: `tis.volvocars.biz` or `volvotechinfo.com`
- Parts-catalog-only subscription is the cheapest official OEM EPC for any major brand
- No raw data export

### Toyota Microcat Market (official, free)
- Official URL: `toyotapartsandservice.com`
- Free for independent repair shops
- Web UI only; no data export

---

## Key Findings for Decision-Making

1. **BMW is the most developer-friendly OEM**: Free AOS access + affordable ETK database from autodb.cc (€800 one-time). If you're starting with one brand's data, BMW is the obvious choice.

2. **Mercedes is the best value for official subscription access at ~$110/year** — far cheaper than any other European luxury OEM.

3. **VW Group (ETKA / Partslink24) is the correct official channel at ~$480/year** — covers VW, Audi, SEAT, Skoda across 43 brands.

4. **Toyota Microcat Market is the only major OEM offering a completely free parts catalog** to independent shops.

5. **Volvo VIDA has the most transparent official pricing** — $210.80/year for parts-only is well-documented and straightforward.

6. **Ford, GM, and Stellantis US parts catalogs are effectively dealer-only** — no legitimate standalone non-dealer parts EPC access; service info (repair procedures) has separate subscriptions but not parts catalog per se.

7. **Chinese OEMs (BYD, SAIC, Geely, etc.) have immature Western market EPC infrastructure** — BYD's official EPC is dealer-locked; Geely has an open portal (iepc.geely.com) but pricing is unclear.

8. **Raw database access is a gray market** — autodb.cc is the main known provider of converted EPC databases in MySQL/SQL form. Legal use for a commercial AI product requires careful review.

9. **No OEM offers a public API for parts data** — BMW's AOS portal hints at API capabilities but details are not publicly documented. The closest thing is autodb.cc's JSON API service.

10. **Gray-market EPC software is widely available** — DVD and VMware images of most major EPC systems sell for $30–$150 on eBay, forums, and third-party sites. The data in these is real OEM data but obtained without license; using it commercially carries legal risk.

---

## Sources Consulted

- `etka.com` — official VW Group ETKA information
- `aos.bmwgroup.com` — BMW Aftersales Online System
- `volvotechinfo.com/vida/purchase` — Volvo VIDA pricing (official)
- `aftersales.mercedes-benz.com` — Mercedes AfterSales platform
- `techauthority.com` — Stellantis/FCA TechAuthority
- `techinfo.toyota.com` — Toyota TIS
- `toyotapartsandservice.com` — Toyota Microcat Market
- `jlrepc.com` — JLR EPC
- `rpartstore.renault.com` — Renault RParts
- `stellantisiop.com` — Stellantis Independent Operator Portal
- `autodb.cc` — EPC database conversion (third-party)
- `bimmerforums.com` — ETK Transbase extraction community discussion
- `mbworld.org` — Mercedes EPC access forum discussion (non-dealer pricing)
- Forum sources: VW Vortex, Rennlist, Passatworld, MHH Auto, Diagnostic Network
