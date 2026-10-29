# Local SEO Analysis — Lys Montage (`index.html`)

Date: 2026-10-29 · Scope: local file `index.html` + repo docs (`docs/sources.md`, `deploy/nginx-lys-montage.conf`) · Live site: **not reachable** (see Critical #1)

## Local SEO Score: 20/100

| Dimension | Weight | Score | Weighted | Main reason |
|---|---|---|---|---|
| GBP signals | 25% | 15 | 3.8 | No Google Business Profile evidence, no hours, no Maps link |
| Reviews & reputation | 20% | 15 | 3.0 | 1 testimonial + 5 Instagram comments; no Google reviews |
| Local on-page SEO | 20% | 50 | 10.0 | Good title, tel: links, area stated; H1 has no service/city; single page |
| NAP consistency & citations | 15% | 20 | 3.0 | Name differs between site and Instagram; no citations found |
| Local schema markup | 10% | 0 | 0.0 | No JSON-LD at all |
| Local links & authority | 10% | 5 | 0.5 | Domain not registered; no local mentions found |
| **Total** | | | **20.3** | |

The score is low mainly because the off-site layer (domain, GBP, reviews, citations) does not exist yet. The page itself is a reasonable starting point.

## Business type and vertical

- **Type: Service Area Business (SAB).** No street address anywhere; geography is "Львів та область" (sourced: post DW9F5T8DOZG). Embedded map and physical-address checks are skipped.
- **Vertical: Home Services.** Signals: plumbing, heating, heat pumps, warm floors, solar (СЕС), air conditioning; Instagram category "Plumbing service" (`docs/sources.md` §2).
- Recommended schema subtype: `Plumber` + `HVACBusiness`.

## Critical #1: the domain is not registered

`deploy/nginx-lys-montage.conf` and `deploy/bootstrap.sh` use `lysmontage.com`. On 2026-10-29:

- `dig` returns no A or NS records.
- `whois lysmontage.com` returns `No match for domain "LYSMONTAGE.COM"`.

Until a domain is registered and pointed at the server, Google cannot crawl or index anything, and the remaining recommendations have no effect. Anyone could also register this name first. Every absolute URL in the schema below depends on the final domain.

## GBP optimization checklist

| Signal | Status | Note |
|---|---|---|
| GBP exists / linked from site | ❌ Not detected | No Maps link, place ID or reviews widget |
| Primary category | — | Suggest **Сантехнік / Plumber**: it matches the Instagram category and the brief |
| Secondary categories | — | Candidates: heating contractor, air conditioning contractor, solar energy contractor, HVAC contractor (check the exact category names in the GBP interface) |
| SAB setup (address hidden, service area = Львів + Львівська обл.) | — | Matches the confirmed geography; don't publish an address that isn't confirmed |
| Photos | ⚠️ Available, unused | 7 sourced project photos plus the Instagram feed can go straight into GBP |
| Business hours | ❌ Missing | Not confirmed anywhere. Ask Andriy; don't invent hours |
| Website link | — | Once the domain exists, link GBP to the homepage (it's the only page) |
| Q&A | n/a | Put common questions on the website instead (Google is phasing out GBP Q&A) |

## Review health snapshot

| Metric | Value |
|---|---|
| Google reviews | 0 detected (no GBP) |
| On-site testimonials | 1 client testimonial (unattributed, per brief) + 5 Instagram comments with handles and source posts |
| Rating / `aggregateRating` | None. **Don't add one from these comments**: Google treats ratings a business publishes about itself on its own site as self-serving and won't show them |
| Recency / velocity | n/a |
| Owner responses | n/a |
| Review gating | None detected ✅ |

The on-site review section is honest and well sourced (`docs/sources.md` §6). The gap is the lack of reviews on a third-party platform. Once GBP exists, Andriy can send a plain review link to recent clients after each job, the same link to everyone (no screening by satisfaction first), and keep a steady pace.

## NAP consistency audit

| Field | Visible HTML | JSON-LD | Instagram (source) | Status |
|---|---|---|---|---|
| Name | **Lys Montage** (title, logo alt, footer) | none | **Lys Montag \| Інженерні рішення** | ⚠️ Mismatch |
| Address | "Львів та область" (no street, correct for SAB) | none | Lviv, "Львову та області" | ✅ Consistent |
| Phone | `068 624 08 27` / `tel:+380686240827` | none | 0686240827 | ✅ Same number |

The name mismatch matters more than it looks. Search engines and AI assistants connect the website, Instagram and a future GBP by name, and "Montage" vs "Montag" splits that into two entities. Choose one canonical spelling and use it in GBP, Instagram's display name and the site. If both have to stay, declare the other as `alternateName` in schema (included below). This is a decision for you and Andriy, not something to fix silently.

## Citation presence check

| Platform | Status | Note |
|---|---|---|
| Google Business Profile | ❌ Not found | Highest priority |
| Instagram @lys_montag | ✅ Active | The only established presence |
| Facebook business page | ❌ Not detected | |
| Bing Places | ❌ Not detected | Feeds Bing, Copilot and ChatGPT's local results |
| Apple Business Connect (Apple Maps) | ❌ Not detected | |
| Ukrainian service marketplaces (e.g. Kabanchik.ua, OLX "Послуги") | ❌ Not detected | Check which ones actually bring Andriy clients before listing |
| Web mentions of the name or phone | ❌ None found | Searches for `"Lys Montag" Львів` and the phone number returned nothing relevant |

Yelp, BBB and Thumbtack (the plugin's US defaults) aren't relevant for the Ukrainian market, so they're left out.

## Local schema status: missing

No JSON-LD is present. Ready-to-use block below. It uses only facts confirmed in `docs/sources.md`; `https://lysmontage.com/` is a placeholder until the real domain exists.

Deliberately left out: `openingHoursSpecification` (hours not confirmed), `priceRange` (prices are kept off the site on purpose), `aggregateRating` (self-serving), `streetAddress` and `geo` (SAB with no confirmed address). Add a GBP `sameAs` link once the profile exists.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": ["Plumber", "HVACBusiness"],
  "@id": "https://lysmontage.com/#business",
  "name": "Lys Montage",
  "alternateName": "Lys Montag",
  "description": "Продаж, монтаж та обслуговування систем опалення, сантехніки, сонячних електростанцій та кондиціонерів у Львові та Львівській області.",
  "url": "https://lysmontage.com/",
  "telephone": "+380686240827",
  "logo": "https://lysmontage.com/assets/images/logo-lys.png",
  "image": [
    "https://lysmontage.com/assets/images/project-warm-floor-hero.jpg",
    "https://lysmontage.com/assets/images/project-boiler-room.jpg",
    "https://lysmontage.com/assets/images/project-solar-dolobiv.jpg"
  ],
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Львів",
    "addressRegion": "Львівська область",
    "addressCountry": "UA"
  },
  "areaServed": [
    { "@type": "City", "name": "Львів", "sameAs": "https://uk.wikipedia.org/wiki/Львів" },
    { "@type": "AdministrativeArea", "name": "Львівська область", "sameAs": "https://uk.wikipedia.org/wiki/Львівська_область" }
  ],
  "founder": { "@type": "Person", "name": "Андрій" },
  "sameAs": ["https://www.instagram.com/lys_montag/"],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Послуги",
    "itemListElement": [
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Монтаж опалення: котли, теплові насоси, тепла підлога, радіатори" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Сантехніка та водопостачання" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Сонячні електростанції (СЕС)" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Кондиціонери: продаж, монтаж, обслуговування" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Продаж і доставка обладнання та матеріалів" } }
    ]
  }
}
</script>
```

## Local on-page findings

| Element | Current | Assessment |
|---|---|---|
| `<title>` | "Lys Montage — опалення, сантехніка, СЕС та кондиціонери у Львові" | ✅ Brand + services + city, 64 chars |
| Meta description | Services + "Львові та області" + Instagram | ✅ Good |
| H1 | "Lys Montage — інженерні рішення для дому" | ⚠️ No service or city. E.g. "Lys Montage — опалення, сантехніка та СЕС у Львові" (all confirmed facts) |
| Click-to-call | `tel:+380686240827` in hero, supply block, contacts | ✅ Above the fold on mobile |
| Service area in copy | Eyebrow "Львів та область", contacts | ✅ |
| Local proof in gallery | Долобів, Скнилівський міст, Львів captions | ✅ Real, sourced locations; more named locations from `docs/sources.md` (Рудки, Пасіки-Зубрицькі, Підбірці, Lviv residential complexes) could be added |
| Dedicated service pages | None (single page, anchors only) | ⚠️ Biggest on-page gap for local organic search |
| `<link rel="canonical">`, Open Graph tags | Missing | ⚠️ Instagram/Viber/Telegram previews will be bare; add once the domain is known |
| `robots.txt`, `sitemap.xml` | Missing | ⚠️ Add once the domain is known |
| Hours on page | Missing | Only if Andriy confirms them |

**Location pages:** none, so doorway-page risk is zero. Don't create per-village pages; the quality gates would flag them unless each has a real project.

## Top 10 prioritized actions

| # | Priority | Action | Why (first principle) | Depends on | How we'd know it failed | Leading indicator |
|---|---|---|---|---|---|---|
| 1 | **Critical** | Register a domain, point A/AAAA records at the server, run certbot | Nothing unreachable can be indexed | — | `dig +short <domain>` empty; HTTPS errors | Domain resolves; HTTPS returns 200 |
| 2 | **Critical** | Create a Google Business Profile as a service-area business (Львів + область, address hidden), primary category Plumber | GBP is the top factor in the local map pack; with no profile there's no map-pack presence | 1 (for the website link) | Profile stuck unverified, or suspended for an invented address | Verified profile; GBP impressions appear in Insights |
| 3 | **High** | Choose one brand spelling (Lys Montage vs Lys Montag) and use it across GBP, Instagram and the site | Engines link entities by name; a mismatch splits signals | — | Searching the brand shows two unrelated entities | Searching the brand name returns site + Instagram + GBP together |
| 4 | **High** | Add the LocalBusiness JSON-LD above | Machine-readable name, phone, area and services for Google and AI assistants | 1, 3 | Rich Results Test / Schema validator errors | Search Console "Enhancements" shows no errors |
| 5 | **High** | Add canonical, Open Graph tags, `robots.txt`, `sitemap.xml`; submit to Search Console | Basic indexing hygiene; OG makes links shared in messengers look trustworthy | 1 | Search Console "Discovered – not indexed" | Homepage indexed within ~1–2 weeks |
| 6 | **High** | Start collecting Google reviews: the same plain link to every recent client after each job, no screening | Reviews are about 20% of local pack weight and are what visitors check first | 2 | <10 reviews after 3 months | One or two new reviews a month, no gaps longer than ~3 weeks |
| 7 | **Medium** | Rewrite the H1 with services + city | Strongest on-page relevance signal, and currently generic | — | Ranks for brand only, never "монтаж опалення Львів" | GSC impressions for service + city queries |
| 8 | **Medium** | Build dedicated service pages (опалення/тепла підлога, СЕС, сантехніка, кондиціонери, продаж матеріалів), each with that service's real sourced projects | Dedicated service pages are the #1 local organic factor; one page can't rank well for five service intents | 1, 5 | Pages ranking for nothing after ~3 months, or thin pages with no unique projects | Per-page impressions in GSC |
| 9 | **Medium** | Claim Bing Places, Apple Business Connect and a Facebook page with the same name/phone/area; add their URLs to `sameAs` | Consistent citations feed AI assistants (ChatGPT uses Bing) and Apple Maps | 2, 3 | Different names/phones across listings | Brand appears in Bing/Copilot answers |
| 10 | **Low** | Ask Andriy for working hours; add them to GBP, the page and schema only if he confirms | "Open now" affects local ranking, but invented hours break the project's integrity rule | 2 | Calls outside the stated hours | — |

## Limitations

This analysis could **not** assess:

- **Live site behaviour.** The domain doesn't resolve, so there was no HTTP header, Core Web Vitals or rendered-crawl check. Run `/seo technical` once it's live.
- **GBP data, local pack position, geo-grid ranking.** There's no profile, and no DataForSEO or Google API access was configured. Run `/seo maps` after GBP verification for geo-grid tracking.
- **Backlinks and domain authority.** Nothing to measure on an unregistered domain.
- **Directory coverage.** Checked with two web searches only (which returned no relevant results); the search tool is US-centric, so Ukrainian directories may be under-covered.
- **Instagram-rendered gallery.** The JS gallery only runs on the server; this analysis saw the static fallback.

Paid tools that fill these gaps: DataForSEO (live local pack + business listings), BrightLocal/Whitespark (citation audit, geo-grid), Google Search Console + GBP Insights (free, once set up).
