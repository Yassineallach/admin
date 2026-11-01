# Avilex: Multilingual Bird Dictionary & Encyclopedia (Android)

> **Avilex** is a working title. It's used in these documents only and can be renamed.

Planning package for an Android app built on the data in
[`alchaincyf/huashu-bird-sticker`](https://github.com/alchaincyf/huashu-bird-sticker)
(IOC World Bird List v15.2, 11,064 living species).

| # | Document | What it answers |
|---|---|---|
| 1 | [PRD.md](PRD.md) | What we build, for whom, and in which release |
| 2 | [TRD.md](TRD.md) | How we build it: stack, architecture, search, offline, third-party APIs |
| 3 | [UI-UX.md](UI-UX.md) | Design system, screen designs, accessibility, RTL |
| 4 | [APP-FLOW.md](APP-FLOW.md) | Navigation graph and user journeys |
| 5 | [BACKEND-SCHEMA.md](BACKEND-SCHEMA.md) | On-device SQLite (Room) schema, cloud Postgres schema, ETL |
| 6 | [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) | Phased plan, milestones, tasks, risks |

## Read this first: licensing findings in the source repo

1. **The sticker images may NOT be used in this app.** `stickers/` and `previews/` are under
   PolyForm Shield 1.0.0. The licensor (Huashu, maker of the *Mingji* app) explicitly excludes
   "a bird-watching, bird-identification or bird field-guide app, website or service, whether
   paid or free". A bird dictionary/encyclopedia with identification falls inside that
   exclusion. Options: (a) ask the licensor for a separate commercial license, (b) use
   openly licensed photos (Wikimedia Commons via Wikidata P18, CC0/CC BY/CC BY-SA only),
   (c) commission or generate our own artwork. The plan assumes **(b) + family silhouettes**
   and treats (a) as an upside.
2. **The data CAN be used commercially, with attribution:**
   - Project compilation (`data/`): MIT
   - Names/taxonomy: IOC World Bird List v15.2, CC BY 3.0
   - Traits: AVONET (Tobias et al. 2022), CC BY 4.0
   - IUCN/CITES/IDs: Wikidata, CC0
   - `field-guide.zh-Hans.json`: CC BY-SA 4.0 (share-alike; ship it as a separate,
     clearly attributed content pack)
3. **Several suggested sources restrict commercial use.** eBird API (non-commercial without
   agreement), BirdLife range maps (by request, non-commercial), most xeno-canto recordings
   (CC BY-NC-SA), BirdNET models (CC BY-NC-SA). The TRD lists a compliant route for each
   feature.

## Answer to "What does your dataset contain?"

It's the **third case**: names, scientific names, classification, *and* extra information.
Measured coverage across the 11,064 species:

| Data | Coverage | Source |
|---|---|---|
| Scientific name, authority, order/family/genus, IOC sequence | 11,064 (100%) | IOC |
| English name | 11,064 | IOC |
| Names in 46 language columns | varies by language, see below | IOC |
| Wikidata / eBird / GBIF / iNaturalist IDs | 10,947 | Wikidata |
| Breeding region + breeding/non-breeding range text | 11,064 | IOC |
| Subspecies with ranges | 4,992 species | IOC |
| Mass, wing, tail, tarsus, bill, habitat, migration, diet (trophic niche), lifestyle | 10,577 | AVONET |
| Body length / wingspan (cm) | ~4,736 | Wikidata/Wikipedia |
| IUCN category / CITES | 10,197 | Wikidata |
| Chinese field-guide notes (appearance, field marks, sex/age, similar species) | 1,596 | CC BY-SA |

Name coverage per language (species with a name):
en 11,064 · sk 11,064 · fr 11,055 · zh-Hans 11,041 · nl/eo/sv 11,040 · pt 11,039 ·
no 11,031 · da 10,996 · pl 10,994 · es 10,877 · de 10,840 · uk 10,793 · hr 10,643 ·
ru 10,614 · tr 10,570 · ja 10,566 · zh-Hant 10,536 · cs 10,193 · ca 10,125 · it 10,038 ·
fi 10,031 · lt 9,903 · sr 8,013 · hu 6,484 · et 5,651 · lv 2,016 · id 1,976 · bg 1,416 ·
he 1,154 · sl 1,107 · th 1,012 · af 978 · is 972 · se 952 · **ar 589** · ko 566 · fa 551 ·
ml 543 · el 516 · ro 414 · mk 389 · be 327

**Arabic has only 589 names.** For the flagship "search in Arabic" use case, the first
enrichment job pulls Arabic labels/aliases from Wikidata (`ids.wikidata`, CC0). This is in
Stage 1 of the implementation plan.
