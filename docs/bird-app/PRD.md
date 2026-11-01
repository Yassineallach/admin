# 1. Product Requirements Document (PRD)

**Product:** Avilex (working title), a multilingual bird dictionary & encyclopedia for Android
**Status:** Draft v1.0 · 2026-11-01
**Data foundation:** IOC World Bird List v15.2 via `huashu-bird-sticker/data` (11,064 species)

---

## 1.1 Vision

The fastest way to find any bird's name in any language, then learn about that bird.
A user types "باشق" or "Épervier" or "Accipiter nisus" and immediately sees the bird's
English, French, Spanish, German, Arabic and scientific names. From there they can open a
full profile, hear names and songs, see the bird's range, save it, and quiz themselves.

**Positioning:** a *multilingual name and knowledge* app first, and an identification app
second. Translators, students, teachers, birders who travel, and people who speak several
languages have no good tool for cross-language bird names. That's where we stand out. Merlin
and eBird lead on identification, and we don't try to beat them there in v1.

## 1.2 Goals & non-goals

| Goals (12 months) | Non-goals (v1) |
|---|---|
| Best-in-class multilingual bird name search (43 languages, scientific names) | Social network / community feed |
| A complete, offline-first profile for all 11,064 species | Our own vision model training in Stage 1–2 |
| Retention through Bird of the Day, collections and quizzes | Subspecies-level identification |
| Sustainable revenue from Premium + optional ads | iOS (planned after Android product-market fit) |
| Strict license compliance with every data source | Use of huashu sticker images (license forbids it, see README) |

## 1.3 Target users & personas

| Persona | Need | Key features |
|---|---|---|
| **Amina, translator/teacher (Rabat)** | Translate bird names between Arabic, French, English for texts/classes | Cross-language search, side-by-side compare, copy/share |
| **Lucas, travelling birder (Lyon)** | Knows French names, birds abroad use other names; wants offline lists | Country Explorer, offline DB, checklist |
| **Kenji, student (Osaka)** | Learn taxonomy & scientific names for exams | Scientific Name Explorer, family tree, flashcards |
| **Sofia, parent (Madrid)** | Fun, safe learning with kids | Bird of the Day, quizzes, sounds |
| **Omar, casual nature lover** | "What bird is this?" | Photo/sound/questionnaire identification |

## 1.4 Success metrics (KPIs)

| Metric | Target at 6 months after launch |
|---|---|
| D1 / D7 / D30 retention | 35% / 18% / 8% |
| Searches per DAU | ≥ 3 |
| Search success (result tapped within 10 s) | ≥ 80% |
| Time to first result | < 100 ms p95 on a mid-range device, offline |
| Crash-free sessions | ≥ 99.5% |
| Premium conversion | 2–4% of MAU |
| Play Store rating | ≥ 4.5 |

## 1.5 Release scope

Priority: **P0** = must ship in that stage, **P1** = should, **P2** = could.

### Stage 1: Initial Release (MVP)

| ID | Feature | Pri | Acceptance criteria |
|---|---|---|---|
| F1.1 | **Offline species database** (11,064 species, all names, taxonomy, traits, range text, IUCN) bundled in APK | P0 | App works fully in airplane mode on first launch |
| F1.2 | **Multilingual search**: any of 43 languages + scientific name, simultaneous, accent-, case- and diacritic-insensitive, prefix + typo-tolerant | P0 | "epervier", "Épervier", "accipiter nis", "باشق" all return *Accipiter nisus* in the top 3 |
| F1.3 | **Search result card** shows the match, the language it matched in, plus primary-language and scientific names | P0 | Matched language shown as a chip |
| F1.4 | **Primary display language** + **pinned compare languages** (default: device language + en + sci) | P0 | Changing language re-renders lists instantly |
| F1.5 | **Bird profile**: identification, classification, measurements, habitat, diet, migration, lifestyle, range text, subspecies, IUCN/CITES, external links | P0 | Missing fields hidden, never shown as "null" |
| F1.6 | **Name Explorer**: all names for one bird, grouped by language, with copy and share per name and "copy all" | P0 | Share produces text: "Eurasian Sparrowhawk · Épervier d'Europe · … (Accipiter nisus)" |
| F1.7 | **Language Comparison**: pick 2–6 languages, table view for a bird / a family | P1 | Exportable as CSV share |
| F1.8 | **Name pronunciation** via on-device Text-to-Speech where the voice exists | P1 | Button hidden if no TTS voice for that language |
| F1.9 | **Advanced filters**: order, family, habitat, diet, size (from mass), region, IUCN, migration, lifestyle | P0 | Filters combine with AND, show live result count |
| F1.10 | **Browse by taxonomy**: orders → families → genera → species | P0 | |
| F1.11 | **Favorites** | P0 | Persist offline |
| F1.12 | **Home / Discovery**: Bird of the Day, Random bird, Rare & endangered, Browse by habitat/family, Recently viewed | P0 | Bird of the Day is the same for everyone on a given UTC date |
| F1.13 | **Settings**: language, theme (light/dark/system), units (metric/imperial), data attribution screen | P0 | Attribution lists every source and license |
| F1.14 | **Arabic & RTL**: full RTL UI; Arabic names enriched from Wikidata to > 5,000 species | P0 | Layout mirrored correctly |
| F1.15 | **Crash reporting + privacy-friendly analytics** (opt-in in EU) | P0 | |

### Stage 2: Enriched Encyclopedia

| ID | Feature | Pri |
|---|---|---|
| F2.1 | **Photographs** from openly licensed sources (Wikimedia Commons CC0/BY/BY-SA) with per-photo credit | P0 |
| F2.2 | **Descriptions**: Wikipedia summary in the user's language (online, cached), with link and license | P0 |
| F2.3 | **Distribution map**: GBIF occurrence density tiles + IOC region overlay; **Country Explorer** (birds by country, from GBIF country facets) | P0 |
| F2.4 | **Bird sounds**: xeno-canto recordings (license shown per recording, commercial-safe filter), multiple recordings, waveform + **spectrogram** | P0 |
| F2.5 | **Similar birds** (same genus + trait similarity) and **Bird Comparison** (two species side by side) | P1 |
| F2.6 | **Quizzes**: picture quiz, sound quiz, multilingual name match, scientific-name challenge, flashcards (spaced repetition), daily fact | P0 |
| F2.7 | **Personal collection**: Seen / Want to see lists, life-list counter | P0 |
| F2.8 | **Offline content packs** (photos + sounds) by region: Europe, North Africa & Middle East, Sub-Saharan Africa, etc. | P1 |
| F2.9 | **Bird Family Tree** visual explorer (order → family → genus) | P1 |
| F2.10 | **Premium subscription** + optional AdMob in free tier | P0 |
| F2.11 | Account + cloud sync (optional sign-in) | P1 |
| F2.12 | Filter by **color** (curated dominant colors per species) | P2 |

### Stage 3: Advanced Features

| ID | Feature | Pri |
|---|---|---|
| F3.1 | **Photo identification** (camera/gallery): top-3 suggestions with confidence; location-aware re-ranking | P0 |
| F3.2 | **Sound identification**: record → top-3 suggestions; spectrogram with highlighted segment | P0 |
| F3.3 | **Questionnaire identification** (size, colors, habitat, location, behavior) | P0 |
| F3.4 | **Birdwatching journal**: observations with date, GPS, photos, notes; private by default | P0 |
| F3.5 | **Personal observation map** and statistics | P1 |
| F3.6 | **Migration / seasonal maps** (GBIF month facets) | P1 |
| F3.7 | **Community observations** (moderated, opt-in) | P2 |
| F3.8 | Export journal (CSV / eBird-compatible format) | P1 |

## 1.6 Free vs Premium

| Free | Premium (≈ €2.99/month · €19.99/year · €39.99 lifetime; price to validate) |
|---|---|
| All 11,064 species, all names, all languages | Offline photo & sound packs |
| Multilingual search, basic filters (family, habitat, IUCN) | Advanced filters (combined, size, diet, lifestyle, color, country) |
| Profiles, online photos/sounds | Unlimited identification (free: 5/day) |
| Favorites, Seen list | Custom collections, statistics, journal export |
| 3 quiz modes, Bird of the Day | All quiz modes + spaced-repetition flashcards |
| Banner ads (no ads on profile media or quiz answers) | Advanced maps (seasonal, country), no ads |

**Rule:** never paywall names, the core of the product. Free users must be able to search
every species in every language.

## 1.7 Functional requirements: details

**Search (F1.2)**
- Input normalization: lowercase, Unicode NFKD, strip combining marks (é→e, ä→a), unify
  apostrophes (’ → '), hyphens/spaces equivalent, ß→ss, Arabic normalization (strip
  tashkeel/tatweel, أ/إ/آ→ا, ى→ي, ة→ه), Hebrew/Persian equivalents, Traditional↔Simplified
  Chinese match, kana-insensitive Japanese (hiragana↔katakana).
- Ranking: exact > prefix of full name > prefix of any word > substring > fuzzy (edit
  distance ≤ 1 for queries ≥ 4 chars, ≤ 2 for ≥ 8). Boost: primary language,
  compare languages, recently viewed, common species (by GBIF occurrence count).
- Scope selector: *All languages* (default) · *My languages* · a single language · *Scientific*.
- Results ≤ 50 ms for typed input on a Snapdragon 6-class device.
- Empty state shows recent searches and "Try: باز, Robin, Turdus…".

**Profile (F1.5)** sections in order: Header (photo/silhouette, primary name, sci name,
IUCN badge) → Names (top languages + "All 43 languages") → Classification → Appearance &
size → Habitat & ecology → Distribution → Conservation → Subspecies → Sounds (S2) → Similar
species (S2) → Sources & credits.

**Bird of the Day:** deterministic `seed = hash(UTC date)` over a curated pool (≥ 1 photo,
≥ 10 languages). Push notification opt-in at user-chosen time.

## 1.8 Non-functional requirements

| Area | Requirement |
|---|---|
| Platform | Android 8.0 (API 26)+, phones & tablets, foldables |
| APK/AAB size | Base install ≤ 40 MB; packs downloaded on demand |
| Performance | Cold start < 1.5 s; profile open < 300 ms; 60 fps lists |
| Offline | 100% of Stage 1 features offline |
| Accessibility | WCAG 2.2 AA; TalkBack labels; dynamic font to 200% |
| Localization | UI in 12 languages at launch (en, ar, fr, es, de, pt, it, nl, ru, zh-Hans, ja, tr); content in 43 |
| Privacy | GDPR/Play Data Safety; location only on explicit action; journal private by default |
| Licensing | Every displayed photo/sound/text carries its author + license; CC BY-SA content kept separable |

## 1.9 Risks & assumptions

| Risk | Mitigation |
|---|---|
| Sticker images can't be used | Wikimedia Commons photos + silhouettes; ask the licensor for a license |
| Low name coverage in ar/ko/fa/el/… | Wikidata label enrichment; "Suggest a name" form; mark non-IOC names as "regional / Wikidata" |
| Identification APIs are non-commercial | Stage 3 uses a licensed vendor or a self-trained model on commercially licensed data (see TRD §2.9) |
| IUCN data in Wikidata may lag | Show "as of" date; link to iucnredlist.org |
| Scope creep | Stage gates in Implementation Plan |

## 1.10 Open questions
1. Final app name and brand.
2. Will we approach Huashu for a commercial sticker license?
3. Launch markets: Morocco/MENA + EU first?
4. Budget for an identification vendor in Stage 3.
