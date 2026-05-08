# Backend Constraints Snapshot

**Status:** Living doc — updated whenever substantive backend state changes (new endpoint, fixed canonical gap, new silent-200, changed prefetch, new always-fetched field per page).
**Companion to:** `BACKEND_DESIGN.md` (decision framework + punch list) — this doc is the *current-state surface area*, not the plan.
**Owned by:** the backend/Python architect. Frontend skills read it first.
**Last reviewed:** 2026-04-18.

---

## How to read this doc

This is the canonical publication surface the UX skills (`/ux-audit`, `/ux-constraints`, `/ux-design`, `/ux-mockup`, `/d3-viz`, and the `frontend-designer` agent) consult before proposing design work. The intent is that skills read this doc *first* and only ask the architect directly about things it doesn't already answer.

Each section is framed with **"when to read this"** so you can skip to the one that matches your pass:

- §1 — the one-paragraph state-of-the-backend (read first every time).
- §2 — per-endpoint reference cards (read when proposing to fetch or extend a specific endpoint).
- §3 — per-page fetch map (read when designing or auditing a specific frontend page — *this is the thing that was wrong last session*).
- §4 — available aggregate fields (read before proposing new fields; grep-friendly).
- §5 — data-quality constants (read when your design renders entity names, categories, or raw fields).
- §6 — performance characteristics (read when making hydration / SSR / prefetch decisions).
- §7 — what is NOT available today (read before writing "just pull X from the API").
- §8 — open architectural questions + verdicts (read when the question you're about to ask might already be answered).
- §9 — maintenance rule (read if you're touching this doc).

**Cross-references.** `§8 #n` refers to numbered entries in `BACKEND_DESIGN.md §8` (Known Issues) — punch list items, not sections here. `§9 #n` refers to the same file's roadmap. Those two are the canonical plan; this doc is the canonical observation of current state.

---

## §1. State of the backend — 2026-04-18

Ten detail endpoints and ten aggregates in `api/v2/`, all read-only, all serving a decoupled Astro frontend on a different port. Two families formalised in `BACKEND_DESIGN.md §3`: **Family A REST resource access** (actor detail + relationship lists — not cached by default, except actor detail) and **Family B named queries** (aggregates + per-actor summaries + one graph — always cached, 1-hour TTL, invalidated on import). `donations-received` + `donations-made` collapsed into `/actors/{id}/donations/?role=` on 2026-04-18 — `BACKEND_DESIGN.md §11` rows 1–2 closed.

Canonical entity resolution is the defining correctness concern and is in the middle of a **2026-04-17 sweep**. Donations-received, donations-made, activity-by-year, meetings prefetching, and `DonationDetailSerializer` were fixed. Still open: `ActorConsultanciesView`, `ActorDetailView` annotation subqueries, `FundingSummaryView.base_qs`, `NetworkStatsView`, `AgencyClientsView`, and the three uncached aggregates (`TopDonorsView`, `DualInfluenceView`, `DonorConcentrationView`). See `BACKEND_DESIGN.md §8` for the punch list, `§9` for the ordered roadmap.

Performance is budgeted in `BACKEND_DESIGN.md §5`. Warm Redis reads clear every budget comfortably; the cold-cache path on homepage concentration still materialises ~21k donor rows but is hidden by the 1-hour TTL. The one recurring pain point is **`ActorDetailView` on merged parties** — the ten annotation subqueries filter by raw ids, so merged-actor counts in the detail header disagree with the relationship-list counts (§8 #10). Factor that into any design pass that puts detail-header counts next to list counts on the same page.

Frontend fetch maps were partly stale last session — the waffle-chart spec assumed `funding-summary` was on the wire for every profile, when in fact it's fetched only under the party branch at `person/[id].astro:32-39`. §3 below has the corrected map.

---

## §2. Per-endpoint reference cards

Use when proposing to fetch or extend a specific endpoint. Cards are grouped by family (`BACKEND_DESIGN.md §3`). Every card: URL, family, serves (which pages *actually fetch* it), canonical status, cache status, known issues.

### Family A — REST resource access

#### `GET /api/v2/actors/{pk}/` — `ActorDetailView`
- **File:** `api/v2/views.py:930-1047`. Serializer: `ActorDetailSerializer` at `api/v2/serializers.py:218-266`.
- **Family:** A (Resource detail, §3.1 — the one Family A exception that IS cached).
- **Serves:** Every profile page (`person/[id].astro:26`, and by rewrite `party/[id].astro:1-5`, `organisation/[id].astro:1-5`).
- **Payload:** scalar fields + ten aggregate counts (donations_made_count, donations_received_count, total_donated, total_received, consultancies_as_client, consultancies_as_agency, unique_donors_count, unique_meeting_orgs_count, meeting_attendance_count, unique_ministers_met_count).
- **Canonical:** NOT canonical-aware — **§8 #10 OPEN**. The ten Subquery annotations (`views.py:970-1034`) filter by raw `donor_id`/`recipient_id`/`actor_id`. Merged actors see counts of 0 on the detail header while collection endpoints show the real number. **Don't design UI that juxtaposes header counts with list counts on merged actors** until this is fixed.
- **Cache:** 1h per actor, key `actor_detail:{pk}` (`views.py:949`). `?bust_cache=1` skips.
- **404:** yes (inherits from `RetrieveAPIView`).

#### `GET /api/v2/actors/{pk}/donations/?role=<donor|recipient>` — `ActorDonationsView`
- **File:** `api/v2/views.py:1692-1742`. Serializer: `DonationDetailSerializer` at `serializers.py:269-360`.
- **Family:** A (Resource collection, §3.2). Single consolidated view.
- **Serves:** `person/[id].astro:44` with `role=recipient&limit=50` (non-party branch), `:45` with `role=donor&limit=200`, and `ActorTimeline.svelte:306` lazy yearly fetch with `role=recipient`.
- **Canonical:** YES — `recipient` branch filters `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)`; `donor` branch filters `Q(donor_id=pk) | Q(canonical_donor_id=pk)` with `.distinct()`. Serializer uses `effective_donor`/`effective_recipient` sources (§8 #2 fixed 2026-04-17).
- **Prefetch:** `select_related('donor', 'donor__polymorphic_ctype', 'recipient', 'recipient__polymorphic_ctype', 'canonical_donor', 'canonical_donor__polymorphic_ctype', 'canonical_recipient', 'canonical_recipient__polymorphic_ctype')`. 4 SQL queries for a 50-row page.
- **Cache:** none (Family A collection default).
- **Required query param:** `role` must be `donor` or `recipient` — missing/invalid returns **400**. Unlike the relationship-list 404 family (§8 #18 OPEN), this endpoint validates the query-param contract strictly because the role determines which side of the relation is being queried.
- **404 on unknown actor:** no — same §8 #18 pattern (returns `200 {results: []}` when the actor id doesn't exist but role is valid).
- **Context enrichment:** via `_DonationContextMixin` (`views.py:1617-1661`) — batched `actor_context` (party + memberships at donation date) and `key_people_map` (donor directors/PSCs). `recipient_role_at_date` is computed on the server from memberships at `Coalesce(accepted_date, received_date, reported_date)`.
- **Frontend contract notes:** `donation_type` is a free-text field — long-tail values, see §5.
- **Migration history:** replaced `/actors/{pk}/donations-received/` (`ActorDonationsReceivedView`) and `/actors/{pk}/donations-made/` (`ActorDonationsMadeView`) on 2026-04-18. Old URLs unmounted — no deprecation alias. `BACKEND_DESIGN.md §11` rows 1–2 closed.

#### `GET /api/v2/actors/{pk}/meetings/` — `ActorMeetingsView`
- **File:** `api/v2/views.py:2094-2145`. Serializer: `MinisterialMeetingSerializer` at `serializers.py:91-105`.
- **Family:** A (Resource collection).
- **Serves:** `person/[id].astro:46` (non-party branch only — `limit=300`, clamped to 200 by `DetailPagination.max_limit`).
- **Canonical:** YES — filters `Q(minister_id=pk) | Q(attendees__actor_id=pk) | Q(attendees__canonical_actor_id=pk)` with `.distinct()`. Attendee prefetch resolves via `effective_actor`.
- **Prefetch:** minister + department + polymorphic_ctype on both, plus `Prefetch('attendees', queryset=MeetingAttendee.objects.select_related('actor', 'actor__polymorphic_ctype', 'canonical_actor', 'canonical_actor__polymorphic_ctype'))`. **3 SQL queries for a 200-meeting page** — the hydration-freeze cause was addressed 2026-04-17 (§8 #4).
- **Cache:** none.
- **404:** no — §8 #18 OPEN.
- **Silent truncation:** `DetailPagination.max_limit = 200` (`pagination.py:29`). Frontend sends `limit=300` but gets 200. Long-serving ministers (e.g. Johnson, ~335 meetings) are truncated. See §5 for the downstream coxcomb consequence and `activity-by-year` (Family B) for the correct aggregate source.

#### `GET /api/v2/actors/{pk}/memberships/` — `ActorMembershipsView`
- **File:** `api/v2/views.py:2039-2091`. Serializer: `MembershipDetailSerializer` at `serializers.py:381-395`.
- **Family:** A (Resource collection).
- **Serves:** `person/[id].astro:45` (non-party branch — `limit=50`). Drives the role/party/tenure lookup for the header, the Key People block for orgs, and the Lobbyists block for agencies.
- **Canonical:** partial. Edge-level canonical doesn't exist on `Membership` (there is no `canonical_person_id`); identity-level canonical via `Actor.canonical_entry` isn't joined in. Low impact today (most politicians aren't merged); flagged in `BACKEND_DESIGN.md §9 #17`.
- **Prefetch:** `select_related('person', 'organization', 'post', 'on_behalf_of')` — **missing polymorphic_ctype on all three**. N+1 per row via `ActorSummarySerializer`. §8 #19 OPEN.
- **Cache:** none.
- **404:** no — §8 #18 OPEN.
- **Temporal filter caveat:** `?at_date=YYYY-MM-DD` exists (`filters.py:215-230`) but does lexicographic comparison on `start_date`/`end_date` CharFields — only correct for full `YYYY-MM-DD`. Partial dates (YYYY-only) silently misclassify. §8 #21 / §9 #14 OPEN.

#### `GET /api/v2/actors/{pk}/consultancies/` — `ActorConsultanciesView`
- **File:** `api/v2/views.py:1721-1750`. Serializer: `ConsultancyDetailSerializer` at `serializers.py:363-378`.
- **Family:** A (Resource collection).
- **Serves:** `person/[id].astro:47` (non-party branch — `limit=200`).
- **Canonical:** NO — **§8 #9 OPEN (highest-impact single-view fix remaining)**. Filters `Q(client_id=pk) | Q(agency_id=pk)` with no `canonical_*`. Serializer uses plain `agency`/`client` fields, not `effective_agency`. (The simpler `ConsultancySerializer` does use `effective_agency`.) Merged agencies see incomplete client lists on their page.
- **Role filter:** `?role=client` or `?role=agency` supported.
- **Cache:** none.
- **404:** no — §8 #18 OPEN.

#### `GET /api/v2/politicians/` — `PoliticianViewSet`
- **File:** `api/v2/views.py:2974-3009`. Serializer: `PoliticianSerializer` at `serializers.py:458-520`. Filter: `PoliticianFilter` at `filters.py:360-464`.
- **Family:** A (Resource collection, router-mounted).
- **Serves:** `directory.astro:17`.
- **Canonical:** N/A for the list itself (no merged entity resolution on persons today); filters reach through memberships.
- **Temporal caveat:** `filter_party` / `filter_role_type` / `filter_is_current` all compare `today_iso_string` lexicographically against `Membership.start_date`/`end_date` (CharFields). YYYY-only dates misclassify. §8 #21 / §9 #14 OPEN.
- **Cache:** none.

#### `GET /api/v2/parties/` — `PartyViewSet`
- **File:** `api/v2/views.py:3012-3063`. Serializer: `PoliticalPartySerializer` at `serializers.py:440-455`.
- **Family:** A (Resource collection, router-mounted).
- **Serves:** `parties.astro:14` (partially — that page uses `party-donations` aggregate as primary source), directory-style pages.
- **Hardcoded cutoff:** `'2026-01-01'` used as "current" reference in three places (`views.py:3047, 3059`). **Silent drift every year** — once real time passes this date, `mp_count`/`lord_count` behave oddly. §8 #22 / §9 #15 OPEN.
- **Pagination:** disabled (`pagination_class = None`) — parties are bounded.
- **Cache:** none.

### Family B — Named query endpoints

All cached 1h via Redis unless explicitly noted as UNCACHED. Cache keys live in `cache_utils.py:CACHE_KEY_PATTERNS` (`cache_utils.py:19-28`). Per-actor keys are invalidated by `invalidate_actor(pk)` in `cache_utils.py:31-47`; aggregate keys by `invalidate_aggregate_caches()` at `cache_utils.py:87-105`.

#### `GET /api/v2/actors/{pk}/funding-summary/` — `FundingSummaryView`
- **File:** `api/v2/views.py:1050-1324`.
- **Family:** B (Summary, §3.4). The reference summary endpoint.
- **Serves:** `person/[id].astro:35` — **party branch only** (`isPartyActor` at `:30`). Not fetched for non-party actors. See §3 fetch map and §8 decision.
- **Returns:** `total_received`, `donation_count`, `unique_donors`, `yearly_totals[]` (each row carries `top_donors[]` of 5), `top_donors[]` (top 20 private — excludes `donation_type='Public Funds'` and Trade Union donors), `public_funds` (separated bucket), `union_funding` (separated bucket), `category_breakdown[]` by `donation_type`, `largest_donation`. Full field inventory in §4.
- **Canonical:** **PARTIAL — §8 #11 OPEN**. `base_qs = Donation.objects.filter(recipient_id=pk)` at `views.py:1090` misses `canonical_recipient_id`. Every downstream computation (yearly totals, top donors, public funds, largest donation, category_breakdown) rides on this queryset. Top-donor sub-aggregation DOES use `Coalesce('canonical_donor_id', 'donor_id')` (donor side canonical), but recipient-side pivot is raw.
- **Cache:** 1h, key `funding_summary:{pk}`. Invalidated by `invalidate_actor()`.
- **404:** yes (`views.py:1086-1087`).
- **Cross-funding enrichment:** donors who also give to individual party MPs get `to_party_mps` + `mps_funded` fields attached (`views.py:1172-1190`). This is why the party page can render "Cross-Funding of MPs" without another call.

#### `GET /api/v2/actors/{pk}/activity-by-year/` — `ActorActivityByYearView`
- **File:** `api/v2/views.py:1327-1438`.
- **Family:** B (Summary).
- **Serves:** `person/[id].astro:50` (non-party branch — **every other profile type**). Drives Career Shape coxcomb and ActivityBeeswarm.
- **Returns:** four series `{donations_received, donations_made, meetings, consultancies}`, each `[{year, count, total?}]` sorted most-recent-first, plus `category_breakdown[]` by `donation_type` on donations-received (added 2026-04-18). `year` is string, `total` is stringified Decimal (donations only).
- **Canonical:** FULL — every series uses `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` style on its relation table. Meetings include `Q(minister_id=pk) | Q(attendees__actor_id=pk) | Q(attendees__canonical_actor_id=pk)` with `Count('id', distinct=True)` to avoid double-count across multi-matching attendees.
- **Date handling:** donations use `Coalesce(accepted_date, reported_date, received_date)`; meetings use `meeting_date` (DateField); consultancies use `Substr(start_date, 1, 4)` on CharField YYYY[-MM[-DD]].
- **Cache:** 1h, key `activity_by_year:{pk}`. Invalidated by `invalidate_actor()`.
- **404:** yes (`views.py:1371-1372`).
- **Latency:** cold ~250 ms, warm ~95 ms (shipped 2026-04-17 note in §8 #3).

#### `GET /api/v2/departments/{pk}/meetings-summary/` — `DepartmentMeetingsSummaryView`
- **File:** `api/v2/views.py:1459-1597`.
- **Family:** B (Summary).
- **Serves:** **Nothing yet.** The department page tier in `UX_IMPLEMENTATION_PLAN.md` is blocked and this endpoint is designed for it. Shipped 2026-04-17; URL moved 2026-04-18 from `actors/{id}/meetings-summary/` (the silent-zeros-for-non-department bug in §8 #25, now closed).
- **Returns:** `total_meetings`, `unique_attendees`, `unique_ministers`, `by_year[]`, `top_attendees[]` (top 20 with actor_type + classification), `top_ministers[]` (top 20).
- **Canonical:** YES — `Coalesce(canonical_actor_id, actor_id)` on attendees.
- **Cache:** 1h, key `meetings_summary:{pk}`. Invalidated by `invalidate_actor()`.
- **404:** yes — requires `Organization` with `classification in ('Government Department', 'Legislature')`. Non-department actors 404.

#### `GET /api/v2/actors/{pk}/cross-connections/` — `ActorCrossConnectionsView`
- **File:** `api/v2/views.py:1833-2036`. Raw SQL (two CTEs, bidirectional).
- **Family:** B (Summary).
- **Serves:** `person/[id].astro:36, :49` — both branches. Powers the "Corporate Connections" / "Staff With Political Ties" section.
- **Response shape is direction-dependent:** `{direction: 'person_to_orgs', count, results: [{id, name, role, classification, consultancy_count, meeting_count, donations_made_count, total_donated, donations_received_count, total_received}]}` OR `{direction: 'org_to_persons', count, results: [{id, name, role, donation_count, total_donated, meeting_count, parliamentary_roles, other_directorships, party}]}`. Frontend branches on `direction` — see `person/[id].astro:383-410`.
- **Canonical:** FULL — uses both schemes. `COALESCE(canonical_entry_id, id)` on Actors for identity-level resolution, plus `canonical_donor_id`/`canonical_recipient_id`/`canonical_actor_id` on relation tables for edge-level. The only endpoint that mixes both correctly. See `BACKEND_DESIGN.md §7 #1` for the distinction.
- **Data-quality filter:** `_org_to_persons` excludes single-word names and role-title pseudo-persons like "Director" / "Secretary" via regex (`views.py:1966-1968`). Documented exception to the "render faithfully" rule (§5).
- **Cache:** 1h, key `cross_connections:{pk}`. Invalidated by `invalidate_actor()`.
- **404:** yes (`views.py:1862-1865`).

#### `GET /api/v2/actors/{pk}/agency-clients/` — `AgencyClientsView`
- **File:** `api/v2/views.py:1753-1830`. Raw SQL (5 CTEs).
- **Family:** B (Summary).
- **Serves:** `person/[id].astro:48` (non-party branch — `limit=20`). Top Clients block on agency pages.
- **Returns:** `{count, results: [{id, name, meeting_count, donation_count, other_agencies_count, engagement_count}]}`. Sorted by a weighted sum of meetings + donations + other-agency-count.
- **Canonical:** NO — **§8 #12 OPEN**. Raw SQL filters `WHERE agency_id = %s` only. Merged agencies silently show "no clients". The sub-CTEs inside also filter by raw `actor_id`/`donor_id`/`recipient_id`.
- **Cache:** NONE — also §9 #10 OPEN.
- **404:** no — §8 #18 OPEN.

#### `GET /api/v2/aggregates/stats/` — `HomepageStatsView`
- **File:** `api/v2/views.py:2282-2390`.
- **Family:** B (Aggregate).
- **Serves:** `index.astro:60`, `analysis.astro:10`.
- **Returns:** `total_donations`, `total_value`, `concentration_top_1_percent`, `concentration_donors_count`, `dual_influence_count`, `timestamp`.
- **Canonical:** YES — `Coalesce(canonical_donor_id, donor_id)` in both concentration and dual-influence calcs.
- **Cache:** 1h, key via `make_aggregate_cache_key('homepage_stats', params)`.
- **Cold-path cost:** materialises ~21k donor rows in Python for concentration and dual-influence. Hidden by Redis. See §6.
- **Known exception:** consultancy slice ignores `received_after`/`received_before` (§8 #24).

#### `GET /api/v2/aggregates/top-recipients/` — `TopRecipientsView`
- **File:** `api/v2/views.py:156-306`.
- **Family:** B (Aggregate).
- **Serves:** `index.astro:61` (`limit=100`, frontend slices to persons only then top 20).
- **Returns:** `{actor, total_received, donation_count, current_party}` per row. `current_party` resolved via active `Membership.on_behalf_of` (party lookup at `views.py:199-221`).
- **Canonical:** YES — `Coalesce(canonical_recipient_id, recipient_id)`.
- **Cache:** 1h.

#### `GET /api/v2/aggregates/top-donors/` — `TopDonorsView`
- **File:** `api/v2/views.py:24-153`.
- **Family:** B (Aggregate).
- **Serves:** **Nothing today.** (Symmetric twin to `top-recipients` but not wired into any page.)
- **Canonical:** YES (donor side).
- **Cache:** **NONE** — §8 #15 / §9 #11 OPEN. Inconsistency with the cached twin `top-recipients`.

#### `GET /api/v2/aggregates/party-donations/` — `PartyDonationsView`
- **File:** `api/v2/views.py:372-488`.
- **Family:** B (Aggregate).
- **Serves:** `index.astro:62`, `parties.astro:14`.
- **Returns:** `{party, total_received, donation_count, donor_count}` per row.
- **Canonical:** YES — `Coalesce(canonical_recipient_id, recipient_id)` with in-SQL filter to party ids.
- **Cache:** 1h.

#### `GET /api/v2/aggregates/top-lobbying-clients/` — `TopLobbyingClientsView`
- **File:** `api/v2/views.py:656-765`.
- **Family:** B (Aggregate).
- **Serves:** `index.astro:63`, `lobbying.astro:20`.
- **Returns:** `{actor, agency_count, agencies: [{id, name}]}` (top 10 agencies per client).
- **Canonical:** PARTIAL — client side uses `Coalesce(canonical_client_id, client_id)`. Agency sub-list (`agency_id`, `agency__name`) does not canonicalise. §8 #20 OPEN.
- **Cache:** 1h.

#### `GET /api/v2/aggregates/department-meetings/` — `DepartmentMeetingsView`
- **File:** `api/v2/views.py:768-923`.
- **Family:** B (Aggregate).
- **Serves:** `index.astro:64`, `meetings.astro:12`.
- **Returns:** `{department, total_meetings, top_attendees: [{actor, meeting_count}]}`.
- **Canonical:** YES on attendee side — `Coalesce(canonical_actor_id, actor_id)`. Department side uses raw `department_id` (no merged departments exist today).
- **Cache:** 1h.

#### `GET /api/v2/aggregates/dual-influence/` — `DualInfluenceView`
- **File:** `api/v2/views.py:491-653`.
- **Family:** B (Aggregate).
- **Serves:** `lobbying.astro:21`.
- **Returns:** `{organization, total_donated, donation_count, lobbying_count, first_activity, last_activity}`.
- **Canonical:** YES — set-intersection of `Coalesce(canonical_donor_id, donor_id)` and `Coalesce(canonical_client_id, client_id)`.
- **Cache:** **NONE** — §8 #16 / §9 #11 OPEN. The most expensive uncached aggregate (materialises two `distinct()` sets in Python every call).

#### `GET /api/v2/aggregates/network-stats/` — `NetworkStatsView`
- **File:** `api/v2/views.py:309-369`.
- **Family:** B (Aggregate — though API-class based).
- **Serves:** `analysis.astro:11`.
- **Returns:** totals + `unique_donors`, `unique_recipients`, `unique_agencies`, `unique_clients`, date range.
- **Canonical:** NO — **§8 #13 OPEN**. All four unique_* counters use raw ids. Numbers disagree with homepage aggregates.
- **Cache:** **NONE** — §9 #9 OPEN.

#### `GET /api/v2/aggregates/donor-concentration/` — `DonorConcentrationView`
- **File:** `api/v2/views.py:2148-2279`.
- **Family:** B (Aggregate).
- **Serves:** Nothing fetched today.
- **Returns:** HHI, top-10% share, top-donor share, Gini, concentration_category.
- **Canonical:** NO — **§8 #14 OPEN**. `.values('donor_id')` uses raw id. Gini/HHI across merged duplicates is incorrect.
- **Cache:** **NONE** — §8 #17 / §9 #11 OPEN.

#### `GET /api/v2/aggregates/minister-network/` — `MinisterNetworkView`
- **File:** `api/v2/views.py:2393-2971`.
- **Family:** B (Graph, §3.5 — the only graph endpoint).
- **Serves:** `index.astro:224`, `network.astro:27`.
- **Returns:** `{nodes: [...], links: [...], stats: {...}}` D3-shaped. Node types: `minister`, `organization`, `person`, `director`, `psc`. Link types: `donation`, `meeting`, `role`.
- **Canonical:** YES on donors (`Coalesce(canonical_donor_id, donor_id)`) and on attendees via a two-pass resolution (`MeetingAttendee.canonical_actor_id` + fallback to `Actor.canonical_entry_id` for attendees where edge-canonical wasn't set). Also dedups director nodes via `canonical_entry`.
- **Cache:** 1h.
- **Payload budget:** ~1 MB gzipped ceiling per `BACKEND_DESIGN.md §3.5`. Current default response fits; don't raise `limit` past 50 without measuring.

---

## §3. Per-page fetch map

Use this when designing or auditing a specific page. This section is the **authoritative list of what each frontend page actually requests** — not what endpoints exist, what endpoints are actually on the wire. Stale assumptions here are the thing that blocked the waffle-chart spec last session.

### `/` — `frontend/src/pages/index.astro`
5 aggregate fetches in parallel (`index.astro:59-65`):
- `aggregates/stats/`
- `aggregates/top-recipients/?limit=100` (frontend filters to persons, slices top 20)
- `aggregates/party-donations/?limit=10`
- `aggregates/top-lobbying-clients/?limit=20`
- `aggregates/department-meetings/?limit=5&top_attendees=3`

MinisterNetwork hydrates `aggregates/minister-network/` on visibility (`index.astro:224`).

### `/person/[id]` — `frontend/src/pages/person/[id].astro`
**This page handles all actor types.** Two code paths branching on `isPartyActor = actor.actor_type === 'organization' && actor.classification === 'Political Party'` (`[id].astro:30`).

**Always fetched (both branches):**
- `actors/{id}/` — `[id].astro:26`

**Party branch (`isPartyActor` true, `[id].astro:32-39`):**
- `actors/{id}/funding-summary/`
- `actors/{id}/cross-connections/`

**Non-party branch (everything else — politicians, orgs, lobbying agencies, trade unions, departments, `[id].astro:40-60`):**
- `actors/{id}/donations/?role=recipient&limit=50`
- `actors/{id}/donations/?role=donor&limit=200`
- `actors/{id}/memberships/?limit=50`
- `actors/{id}/meetings/?limit=300` (clamped to 200 by `DetailPagination.max_limit`)
- `actors/{id}/consultancies/?limit=200`
- `actors/{id}/agency-clients/?limit=20`
- `actors/{id}/cross-connections/`
- `actors/{id}/activity-by-year/`

Also: `ActorTimeline.svelte:306` lazy-loads `actors/{id}/donations/?role=recipient&received_after=YYYY-01-01&received_before=YYYY-12-31&limit=500` per-year on party profile year expansion.

**Correction from last session's spec pass:** `funding-summary` is NOT available to politicians or organisations on this route today. Any design that wants `category_breakdown` or `yearly_totals` on a non-party profile either needs (A) an added fetch in the non-party branch, or (B) a new field on `activity-by-year`. See §8 decision on the waffle.

### `/party/[id]` — `frontend/src/pages/party/[id].astro`
Pure rewrite (5 lines, `party/[id].astro:1-5`) → `/person/[id]`. Same fetch map, party branch.

### `/organisation/[id]` — `frontend/src/pages/organisation/[id].astro`
Pure rewrite → `/person/[id]`. Same fetch map, non-party branch (because orgs are not parties).

### `/directory` — `frontend/src/pages/directory.astro`
- `politicians/?limit=<N>&offset=<N>&search=...` (`directory.astro:17`).

### `/parties` — `frontend/src/pages/parties.astro`
- `aggregates/party-donations/?limit=20` (`parties.astro:14`).

### `/lobbying` — `frontend/src/pages/lobbying.astro`
- `aggregates/top-lobbying-clients/?limit=30` (`lobbying.astro:20`)
- `aggregates/dual-influence/?limit=20` (`lobbying.astro:21`)

### `/meetings` — `frontend/src/pages/meetings.astro`
- `aggregates/department-meetings/?limit=20&top_attendees=10` (`meetings.astro:12`).

### `/analysis` — `frontend/src/pages/analysis.astro`
- `aggregates/stats/` (`analysis.astro:10`)
- `aggregates/network-stats/` (`analysis.astro:11`)

### `/network` — `frontend/src/pages/network.astro`
- `aggregates/minister-network/` via client-side hydration (`network.astro:27`).

### Static pages (no fetches)
- `/data` (`data.astro`) — reference only.
- `/privacy`, `/terms` — static content.

---

## §4. Available aggregate fields

Inventory of pre-computed fields already on the wire. **Grep this before proposing a new field** — many designs already have their data source and don't know it.

### On `actors/{pk}/` (ActorDetailView)
Per-actor counts, canonical-naive today (§8 #10):
- `donations_made_count`, `donations_received_count`, `total_donated`, `total_received`
- `consultancies_as_client`, `consultancies_as_agency`
- `unique_donors_count` (distinct donors who gave to this actor)
- `unique_meeting_orgs_count` (ministers: distinct orgs that attended their meetings)
- `meeting_attendance_count` (orgs: distinct meetings attended)
- `unique_ministers_met_count` (orgs: distinct ministers met)

### On `actors/{pk}/funding-summary/` (party branch only today)
- `total_received`, `donation_count`, `unique_donors`
- `yearly_totals[]`: `{year, total, count, unique_donors, avg_donation, top_donors[5]}` — most recent first. `top_donors[]` carries `{id, name, total, count}`.
- `top_donors[]` (top 20 private, excludes Public Funds and Trade Unions): `{id, name, total, count, actor_type, to_party_mps?, mps_funded?}`. The last two are set only for donors who also funded individual party MPs.
- `public_funds`: `{total, count, sources, top_sources: [{id, name, total, count}]}`. Split-out bucket.
- `union_funding`: `{total, count, sources, top_sources: [{id, name, total, count}]}`. Split-out bucket.
- `category_breakdown[]`: `{category, total, count}` — by `Donation.donation_type`. See §5 for data-quality notes.
- `largest_donation`: `{value, donor_name, donor_id, date}`.
- `computed_in_ms` — cold-path telemetry.

### On `actors/{pk}/activity-by-year/`
Four series + one compositional slice. Grep the frontend for which to feed to which visualisation:
- `donations_received[]`: `{year, count, total}`.
- `donations_made[]`: `{year, count, total}`.
- `meetings[]`: `{year, count}`. No `total` — meetings don't have a value.
- `consultancies[]`: `{year, count}`.
- `category_breakdown[]`: `{category, count, total}` — by `Donation.donation_type` over donations-received only, sorted descending by `total`. NULL/empty → `'Unknown'`. Added 2026-04-18 as the waffle chart source (see `BACKEND_DESIGN.md §9 #1`, verdict in §8 of this doc). Canonical-correct by construction — rides on the same `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` queryset as `donations_received`.

### On `departments/{pk}/meetings-summary/` (not yet consumed by any page)
- `total_meetings`, `unique_attendees`, `unique_ministers`
- `by_year[]`: `{year, count}`
- `top_attendees[]`: `{id, name, actor_type, classification, meeting_count}` (top 20)
- `top_ministers[]`: `{id, name, meeting_count}` (top 20)

### On `actors/{pk}/cross-connections/`
Direction-branched (see card in §2). Shape is either `person_to_orgs` or `org_to_persons`.

### On `aggregates/stats/`
Homepage metrics. See card in §2 for fields.

### On `aggregates/department-meetings/`
`{department, total_meetings, top_attendees: [{actor, meeting_count}]}` per row.

---

## §5. Data-quality constants

Durable project rule: **render faithfully, don't hide**. Data-quality artefacts surface to the frontend on purpose so the upstream problems are discoverable; fixes belong in the import pipeline (`BACKEND_DESIGN.md §2 rule 6`, `§7 rule 6`). Narrow exceptions exist (structural filters, the `cross-connections` single-word-name filter) but should be documented when added.

### Concatenated entity names (upstream)
From `import_ministerial_meetings` — "Crick Institute Eton College" style rows where two entities were concatenated on import. Surfaces in `MeetingAttendee.actor_name_raw` and occasionally in resolved `actor.name`. Frontend should display them as-is. Fix belongs upstream.

### NULL and blank `donation_type`
`donation_type` is a CharField, not a choice field. Import-time values include blanks, "Unknown", and historical variants. `FundingSummaryView.category_breakdown` emits `category: row['donation_type'] or 'Unknown'` (`views.py:1276`), so the frontend will see a row labelled "Unknown". Render it — don't filter.

### Long-tail `donation_type` values
Known buckets include `'Public Funds'`, `'Cash'`, `'Non Cash'`, `'Visit'`, `'Sponsorship'`, `'Exempt Trust'`, `'Permissible Donor Exempt Trust'`, and others. `FundingSummaryView` carves out `'Public Funds'` and `classification='Trade Union'` donors into their own buckets *explicitly*, because they are structurally not private political donations. Don't replicate that carve-out in a new endpoint without understanding why.

### Single-word "Director" / "Secretary" pseudo-persons
Companies House imports sometimes yield `Person` rows where `name` is just "Director" or "Secretary". `ActorCrossConnectionsView._org_to_persons` filters these out via regex (`views.py:1966-1968`) because they produce misleading "Staff With Political Ties" entries. **Only that one endpoint filters them**; everywhere else they render faithfully, which is correct — they're real rows in the database.

### `MeetingAttendee.actor_name_raw` vs resolved `actor`
`actor_name_raw` is the raw string from GOV.UK; `actor` is a best-effort FK set at import, `canonical_actor` is set by the entity-resolution review process. The `effective_actor` helper returns `canonical_actor or actor`. Some attendees have `actor_name_raw` but no resolved `actor` — the serializer renders the raw string; frontend should too.

### Silent-200 patterns (relationship-list endpoints)
`ActorMeetingsView`, `ActorMembershipsView`, `ActorConsultanciesView`, `AgencyClientsView` return `200 {results: []}` on unknown parent id instead of 404. `§8 #18` OPEN. This erases the "unknown actor" / "known actor, no activity" distinction for these four endpoints. Summary endpoints (funding-summary, activity-by-year, meetings-summary, cross-connections) and `ActorDetailView` correctly 404.

### Merged-actor effects on counts
The merged-actor effect is real and visible on Kemi / Conservative Party / Unite. Today: `funding-summary` for a merged party under-counts on the recipient pivot but the donor side is canonical (§8 #11). `ActorDetailView` annotation subqueries are canonical-naive and under-count on the header (§8 #10). Relationship lists (donations-received, donations-made, meetings, activity-by-year) are canonical-correct as of 2026-04-17. **If you're juxtaposing header counts with list counts, the header is currently wrong on merged actors.**

### `DonationDetailSerializer` historically used raw donor/recipient
Fixed 2026-04-17 (§8 #2) — now uses `effective_donor` / `effective_recipient`. Older screenshots / audits that show merged-alias names on donation lists were taken before the fix.

### `DetailPagination.max_limit = 200` silent clamp
`pagination.py:29`. Frontends sending `limit=300` (as `person/[id].astro:46` does) silently get 200. For long-serving ministers (Johnson ~335 meetings), this truncates. **For distribution-dependent visualisations (coxcomb, beeswarm), use the aggregate endpoint** (`activity-by-year`) rather than re-deriving counts from the truncated list — the aggregate doesn't truncate.

### Department actors exist but have no aggregate fetches
Department pages currently render almost empty — the actor exists, but meetings belong to ministers. `DepartmentMeetingsSummaryView` exists (§9 #5 shipped) but no frontend page fetches it. `BACKEND_DESIGN.md §8 #6` OPEN until the page is built.

---

## §6. Performance characteristics

Read when making hydration / SSR / prefetch decisions. Budgets are in `BACKEND_DESIGN.md §5`; the numbers below are the observed current state that affects design choices.

### Latency
- **Cached aggregate / summary endpoints (warm):** sub-10 ms — negligible for SSR.
- **Cached aggregate / summary endpoints (cold):** 100-300 ms, except the outliers below. Hidden by 1h TTL.
- **`HomepageStatsView` cold:** ~1-2 s on first request after invalidation — materialises ~21k donor rows for concentration calc. §8 #6 (docs) / §9 #7 (materialised view later).
- **`FundingSummaryView` cold:** ~150-250 ms. Has its own `computed_in_ms` telemetry in the response.
- **`ActorActivityByYearView`:** cold ~250 ms, warm ~95 ms.
- **Relationship list endpoints (not cached):** first-page typically 40-120 ms with warm OS caches. `ActorMeetingsView` at `limit=200` with full prefetch: 3 SQL queries, ~100 ms warm.
- **`ActorDetailView`:** warm ~15 ms, cold ~150 ms (ten annotation subqueries — but all run in one SQL round-trip via Subquery).

### Payload sizes
- **Homepage `stats`:** <1 KB.
- **Party profile SSR (party branch — 2 fetches):** typically 30-80 KB. `funding-summary` dominates.
- **Politician profile SSR (non-party branch — 8 fetches):** 40-120 KB for most; heavier for long-serving ministers where `meetings` dominates. The `limit=300` (clamped to 200) meeting fetch can be 40-70 KB alone.
- **`aggregates/minister-network/`:** 150-400 KB depending on parameters. Budget ceiling is ~1 MB gzipped.

### Hydration implications
- Non-party profile performs 8 parallel fetches (`[id].astro:42-51`). Astro awaits them all before SSR — slowest dictates page load. `meetings/?limit=300` is usually the slowest; parallelism keeps total under ~500 ms warm.
- Party profile performs only 2 fetches. Much faster SSR. The non-party page is heavier by design because the timeline consumes the paginated rows.
- Any design that adds a ninth fetch to the non-party branch should ask whether `activity-by-year` already has the aggregate (it often does — see §4).

### Cache-warming
`cache_utils.warm_actor_cache(actor_id)` at `cache_utils.py:138-159` warms `funding-summary` on demand (typically post-import). No equivalent for `activity-by-year` or `meetings-summary` today — they warm naturally on first page load.

---

## §7. What is NOT available today

Guard rail against re-inventing. If design proposals keep trying to use these things, surface here.

- **No `funding-summary` for non-party actors today.** Politicians, orgs, lobbying agencies, trade unions, departments don't get `funding-summary` on profile pages. §8 has the decision.
- **No raw-name resolution endpoint.** The frontend cannot ask "resolve this `actor_name_raw` to a canonical actor". `BACKEND_DESIGN.md §8 #7` OPEN. The concatenated-names data quality problem would need this.
- **No department aggregate page-level data wired in.** `meetings-summary` exists (§9 #5 shipped) but no page fetches it. `BACKEND_DESIGN.md §8 #6` OPEN.
- **No graph endpoint other than minister-network.** If a design calls for a filtered or scoped network (per-party, per-department), it's a new endpoint — don't try to filter the current one client-side past its built-in `limit` / `min_value` / `min_meetings` / `current_only` params.
- **No per-actor consultancy summary.** `ActorConsultanciesView` returns rows; there's no `consultancy-summary` with top-clients / top-agencies / by-year. Designs for lobbying-agency profiles that need aggregates will have to either fetch `consultancies/?limit=500` (risks max_limit=200 silent clamp) or drive a new endpoint.
- **No cross-page donation breakdown for non-party actors.** Only `funding-summary` has `category_breakdown` and it's party-only today.
- **No membership-active filter that handles partial dates correctly.** `?at_date=` exists but does lexicographic comparison on CharField dates. Partial dates misclassify. §8 #21 OPEN.
- **No write endpoints.** API is read-only by design (`BACKEND_DESIGN.md §10`). Import commands own writes.
- **No user-specific content.** No auth, no session, no user-keyed cache. Design proposals that assume "show only data relevant to the logged-in user" are outside the current architecture.
- **No search endpoint beyond politicians.** `PoliticianViewSet` supports `?search=name`; there's no cross-actor free-text search via the API (the legacy Django `SearchView` exists but is not used by the Astro frontend).
- **No OpenAPI polish.** `drf-spectacular` is wired (`urls.py:21-23`) — `/api/v2/schema/`, `/docs/`, `/redoc/` — but most views lack decorator tags / examples / response shapes. §9 #16 OPEN.

---

## §8. Open architectural questions + verdicts

Land decisions here so future designers read them, not me.

### Waffle chart data source (politician profile "Funding by Type")

**Context.** Last session's architect verdict recommended `FundingSummaryView.category_breakdown`. Today's `frontend-designer` spec pass discovered that endpoint is **only fetched under the party branch** at `person/[id].astro:32-39`. For politicians (the audit trigger case), it is not on the wire.

**Options.**
- **A.** Add a `funding-summary` fetch to the non-party branch of `person/[id].astro`. Inherits the canonical gap at §8 #11 (`FundingSummaryView.base_qs` uses raw `recipient_id`). On merged politicians the category breakdown would undercount silently.
- **B.** Extend `ActorActivityByYearView` with a `category_breakdown` field (~10 LOC — add a fifth aggregation annotated by `donation_type` on the same `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` base). Canonical-correct by construction because `activity-by-year` already uses the canonical filter. Shares cache with the coxcomb (same key `activity_by_year:{pk}`). No new fetch on the frontend.

**Verdict: B.**

Rationale:
- Canonical correctness without having to also land §8 #11 first.
- No new request on a page that already runs 8 parallel fetches.
- Cache coherence — waffle and coxcomb live on the same invalidation lifecycle.
- `FundingSummaryView` stays focused on its party-profile use case where the full funding decomposition (public funds, union funding, top donors, cross-funding) makes sense. Politicians don't receive public funds or union money directly; exposing those buckets on a personal profile would be misleading even if zero.
- If later we decide politicians also need top-donors/largest-donation/etc., that's the point to reconsider Option A (and land §8 #11 at the same time).

**Action for the next backend pass.** Add `category_breakdown: [{donation_type, count, total}]` to `ActorActivityByYearView` response. Update this snapshot's §4 inventory.

### Department pages still blocked despite endpoint existing

`DepartmentMeetingsSummaryView` shipped 2026-04-17 (`BACKEND_DESIGN.md §9 #5`). No frontend page fetches it. Next step is a department-profile variant of `/person/[id]` — not a backend concern but worth flagging here so designers don't propose the endpoint *again*.

### Consultancy summary for lobbying-agency profiles

Proposals for a `consultancy-summary` endpoint keep coming up. Today there's `AgencyClientsView` (Family B) which answers part of it, but not top-agencies, not by-year, not revenue (because `Consultancy` has no value field). Before proposing a new endpoint, confirm the design genuinely needs something beyond `agency-clients` + `activity-by-year.consultancies`.

---

## §9. Maintenance

**Single-line update rule:** when substantive backend state changes — new endpoint, fixed canonical gap, new silent-200, changed prefetch, new always-fetched field per page, new data-quality artefact — update the affected section of this doc in the same PR. Don't let this drift.

Most common updates:
- New endpoint → new card in §2, row in §4 if it exposes aggregate fields.
- New frontend fetch → row update in §3.
- Fixed canonical gap → strike through the "OPEN" note in the relevant §2 card, cross-reference the §8 punch-list entry in `BACKEND_DESIGN.md` getting its strikethrough.
- New data-quality artefact → section in §5.
- New "not available" mention surfaced by an audit → row in §7.

Do **not** duplicate `BACKEND_DESIGN.md §8` / §9 here — cross-reference. This doc owns observation, that one owns plan. If an audit finds something that's neither observation nor plan, it's a net-new §8 item and should land there first.

---

## References

- `BACKEND_DESIGN.md` — decision framework, taxonomy §3, correctness rules §7, punch list §8, roadmap §9, URL migration §11.
- `api/v2/views.py` — endpoint implementations (3062 lines).
- `api/v2/serializers.py` — response shapes.
- `api/v2/cache_utils.py` — cache keys + invalidation.
- `api/v2/pagination.py` — pagination classes + silent clamps.
- `api/v2/filters.py` — django-filter sets.
- `datafetch/models/influence_mapping.py` — Donation, Consultancy, MinisterialMeeting, MeetingAttendee + canonical fields.
- `datafetch/models/models.py` — Actor + `canonical_entry` (identity-level canonical).
- `frontend/src/pages/person/[id].astro` — the profile page covering politicians / orgs / parties / agencies / unions.
- `frontend/src/pages/index.astro` — the homepage.
- `UX_IMPLEMENTATION_PLAN.md` — page hierarchy, actor-type variants, build order.
- `API_REFERENCE.md` — endpoint catalogue (less opinionated than this doc).
