# Backend Design

**Status:** Living document
**Companion to:** `systems-architecture.md` (what exists), `data-models.md` (the schema), `FRONTEND_DESIGN.md` (how pages look).
**Purpose:** the decision framework for backend work — how to answer "should this be an endpoint, and if so, what shape?" without relitigating first principles every time.

---

## 1. Strategy

The API is two things. Call them by their right names.

1. **REST-shaped projections of the core resources** — `Actor`, `Donation`, `MinisterialMeeting`, `Consultancy`, `Membership`. These are real entities in the database; the API exposes them as addressable, filterable collections. If a new product question is really "show me these rows, optionally filtered", it belongs here.

2. **Named aggregate and summary endpoints** — pre-shaped answers to specific UI questions ("how concentrated are donors to parties?", "what did this minister's activity look like over time?", "which departments host the most meetings?"). These are queries, not resources — naming them as what they are (`/aggregates/top-donors/`, `/actors/{id}/funding-summary/`) is more honest than pretending every URL is a resource.

Both families share the same rules:
- **Resolved identities** — canonical filter on every actor match (see §7).
- **Bounded output** — a query answers the question asked, not a row dump the client sifts through.
- **Deterministic requests are cached** — named queries are cached by default; REST collections with wide parameter spaces are not.

Three things that are always wrong, regardless of family:
- An endpoint sends thousands of rows so the browser can count, sum, or group them — wrong endpoint (should be a named aggregate).
- A page fetches six endpoints to render a header — wrong endpoint set (factor an aggregate).
- Counts on the page disagree with counts in the database because entity resolution was skipped in a filter — the endpoint is incorrect, not slow, incorrect.

---

## 2. Principles

1. **Aggregation belongs in the database.** `.values().annotate(Count, Sum)` in the ORM, not array reductions in the client. The database has indexes and sort-merge; Svelte does not. Donation counts, year distributions, donor roll-ups: all server-side.

2. **Entity resolution is a filter concern, not a display concern.** Every query that reaches `Donation`, `MeetingAttendee`, `Membership`, or `Consultancy` and filters by an actor id must tolerate canonical aliasing. `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)` is the minimum bar — use `Coalesce()` with the canonical id if you need to group by the resolved identity. Missing this produces counts that are quietly too low and disagree with the homepage aggregates.

3. **Read-only, deterministic, cacheable.** The API is a projection of the database, not a controller. No endpoint mutates state. Given the same inputs, the same bytes come back — which means every endpoint is safe to cache, and caching is the default, not the optimisation.

4. **A page is a contract.** Each frontend route declares the data it needs. The backend's job is to satisfy that contract with as few round-trips and bytes as possible. If a route needs the same two aggregates as another route, factor them; if a route needs a shape no endpoint serves, build the endpoint.

5. **Fail loudly, not quietly.** A gate that silently hides UI when data is incomplete is a bug, not a feature (see Career Shape coxcomb, April 2026). If the backend can't answer the question, return an explicit empty shape so the frontend can render a meaningful empty state. Never return a truncated sample and let the client guess.

6. **Data quality is visible.** Concatenated entity names, blank rows, "Director" pseudo-persons — these are upstream import artefacts. The API surfaces them faithfully so the frontend can render them and make the problem discoverable. Fixes belong in the import pipeline, not in endpoint filters. (Narrow exception: structural filters like "exclude rows with NULL actor_id" are fine.)

---

## 3. Endpoint taxonomy

Two families. Five shapes within them. Pick the smallest shape that answers the question.

### Family A — REST resource access

The core database entities, addressable and filterable. Paginated, canonical-aware, polymorphic-prefetched; not cached by default. One collection per core type.

**URL convention.** `/<resource>/?<filters>` for cross-cutting queries, `/actors/{id}/<resource>/?<filters>` for actor-scoped sub-collections. Relationship role goes in query params (`?role=donor` / `?role=recipient`), not URL segments.

Core resources today: `Actor`, `Donation`, `MinisterialMeeting`, `Consultancy`, `Membership`.

#### 3.1 Resource detail
One row by id. `ActorDetailView` is the archetype.

- **Cached** by `actor_detail:{pk}`, 1h — detail views are the one exception to Family A's "not cached by default" because the detail shape changes only on import.
- **Prefetch everything** the default page view needs — party, classification, image, identifiers. If the frontend immediately calls a second endpoint for a field that was always going to be shown, move the field here.
- **Don't embed relationship lists** (donations, meetings). Those paginate separately.
- **Canonical-aware counters.** Any annotation that counts relations must use `Q(...) | Q(canonical_...)` or `Coalesce` — otherwise the detail header disagrees with the collection endpoints.

#### 3.2 Resource collection
Paginated rows of one resource type, optionally scoped to an actor. `ActorDonationsReceivedView`, `ActorMeetingsView`, `PoliticianViewSet` are examples.

- **Pagination is real**, not decorative. `limit=50` is a page size, not "give me the first few". If the UI needs the whole set to compute something, it should be hitting a named aggregate, not paging through a list.
- **Canonical-filter by default.** `Q(donor_id=pk) | Q(canonical_donor_id=pk)` with `.distinct()`.
- **Prefetch the polymorphic chain.** `select_related('donor__polymorphic_ctype', 'recipient__polymorphic_ctype')` is mandatory for any view whose serializer uses `ActorSummarySerializer`. For nested relations like meeting attendees, use `Prefetch('attendees', queryset=MeetingAttendee.objects.select_related('actor__polymorphic_ctype', 'canonical_actor__polymorphic_ctype'))`. Missing these causes hydration freezes the frontend cannot work around.
- **Effective-actor sources** in the serializer — `source='effective_donor'` / `source='effective_recipient'` / `source='effective_actor'` — so canonical-resolved aliases display under the canonical name.
- **Not cached by default.** Parameter space (limit, offset, filters, sorts) is too wide to warm. Exception: a specific always-identical query (e.g. "first 20 donations-received ordered by date desc, no filters") can be cached individually.
- **404 on unknown parent** for actor-scoped sub-collections — return `404`, not `200 {results: []}`. The empty-state distinction matters to the frontend.

### Family B — Named query endpoints

Pre-shaped answers to specific product questions. Always cached. Invalidated on import. Bounded output size.

**URL convention.** Cross-actor queries at `/aggregates/<name>/`. Per-actor queries at `/actors/{id}/<summary-name>/` (e.g. `funding-summary`, `activity-by-year`, `meetings-summary`, `cross-connections`, `agency-clients`).

#### 3.3 Aggregate
Counts, sums, concentrations, rankings across actors. `HomepageStatsView`, `PartyDonationsView`, `TopRecipientsView` are references.

- **Always cached.** Key: `aggregate:{name}:{params_hash}` via `make_aggregate_cache_key`. TTL: `AGGREGATE_CACHE_TTL` (1h).
- **Push all filters into SQL.** If you find yourself `.filter()`-ing in Python after the queryset materialises, you've built the wrong queryset.
- **Return the shape the UI renders.** `[{year, count, total}]` is an aggregate; `{results: [{donation_id, value, year}]}` is a paginated list misnamed.

#### 3.4 Summary
Pre-aggregated view of one actor's activity. `FundingSummaryView` (per party), `ActorActivityByYearView` (per actor), `DepartmentMeetingsSummaryView` (per department), `ActorCrossConnectionsView` are references.

- **Always cached** — same rules as aggregates. Key: `{summary_name}:{pk}`.
- **Key invalidated on import** — add the key to `invalidate_actor()` in `cache_utils.py`.
- **Bounded output.** A summary is O(years), O(departments), O(top 20) — never O(donations). If output grows with input row count, it's a Family A collection in disguise.
- **404 on unknown actor** — return `404`, not `200` with zero counters.

#### 3.5 Graph
Network shapes for D3. `MinisterNetworkView` is the only example today.

- **Always cached**, with a stern payload budget — these are expensive to compute and change rarely.
- **Return nodes and links, not adjacency matrices.** D3 expects `{nodes: [...], links: [...]}`.
- **Keep payloads under ~1 MB gzipped.** Above that, client-side force simulation is the bottleneck, not transport — build a filtered graph endpoint rather than sending the full one.

---

## 4. The shape of a good endpoint

A short checklist. Some rows apply universally; some flip default by family.

| Check | Applies to | Why |
|---|---|---|
| 404 for unknown ids (including unknown parent on scoped sub-collections) | All | Silent 200-with-empty erases the frontend's empty-state / broken-route distinction |
| Actor filters use `canonical_*` via `Q(...) \| Q(canonical_...)` or `Coalesce` | All | Counts match the rest of the site |
| Serializers showing names use `effective_*` sources | All | Canonical-resolved aliases display as the canonical actor |
| Polymorphic children are `select_related` / `prefetch_related` with `polymorphic_ctype` | All | No N+1 on `ActorSummarySerializer` |
| Output shape ≈ UI shape (no row dumps when the UI needs an aggregate) | Family B mostly; also applies when Family A is being asked the wrong question | The frontend doesn't reshape server data |
| Cached + invalidation key | **Family B: default yes, family A: default no** (detail is the Family A exception) | Deterministic repeats should amortise; wide parameter spaces shouldn't |
| Entry in `urls.py` + line in `API_REFERENCE.md` + docstring | All | Discoverable |
| Returns the same bytes twice for the same params | All | Determinism is the contract |

---

## 5. Performance budget

Numbers the backend is expected to meet. Exceeding any of these is a regression.

| Layer | Budget | Measured where |
|---|---|---|
| Aggregate endpoint (cache hit) | < 10 ms | `HomepageStatsView` with warm Redis |
| Aggregate endpoint (cache miss) | < 300 ms | First request after invalidation |
| Actor detail | < 50 ms warm, < 200 ms cold | `ActorDetailView` |
| Relationship list (first page, 50 rows) | < 150 ms | `ActorDonationsReceivedView` |
| Full profile page SSR | < 500 ms end-to-end | Astro request handler |
| Gzipped payload for page load | < 50 KB across all fetches | DevTools Network |

If a page needs more than six fetches to render, combine endpoints (or promote an aggregate). If a single endpoint moves more than ~200 rows for a one-shot SSR render, it is serving the wrong page.

---

## 6. Caching strategy

### Defaults
- **Aggregate, summary, graph** endpoints: cached, 1h TTL, `make_aggregate_cache_key`.
- **Detail** endpoints: cached, 1h TTL, keyed by id.
- **Relationship lists**: not cached by default. Param space is wide and per-user interactions (sort, page) would thrash.

### Keys
Live in `cache_utils.py:CACHE_KEY_PATTERNS`. Any new cached endpoint adds a pattern there. Any per-actor key is added to `invalidate_actor()` so imports bust it.

### Invalidation
- Import commands call `invalidate_actors([...])` for the specific actors they touched, and `invalidate_aggregate_caches()` if they moved homepage totals.
- A bulk reimport uses `invalidate_all_actor_caches()`.
- Never clear the whole cache in application code unless the fallback branch is taken.

### What not to cache
- Anything user-specific (there is no user-specific content today; if that changes, revisit).
- Anything that reads `request.user`, `request.session`, or cookies.
- Schema/docs endpoints (`drf-spectacular` has its own).

---

## 7. Data correctness rules

These are the non-negotiable details that, when missed, produce quiet wrongness — numbers that look reasonable but are wrong.

1. **Canonical on both sides of every actor filter.**
   ```python
   Donation.objects.filter(
       Q(recipient_id=pk) | Q(canonical_recipient_id=pk)
   )
   ```
   For aggregation, `Coalesce('canonical_recipient_id', 'recipient_id')` gives you the resolved identity to group by.

   **Two distinct canonical schemes exist — don't conflate them.**
   - **Edge-level canonical** lives on the relation tables: `Donation.canonical_donor_id`, `Donation.canonical_recipient_id`, `MeetingAttendee.canonical_actor_id`, `Consultancy.canonical_client_id`, `Consultancy.canonical_agency_id`. It says "this particular row really refers to that canonical actor, not the one it was recorded under." Applies to filters on that relation table.
   - **Identity-level canonical** lives on the Actor itself: `Actor.canonical_entry`. It says "this actor is a duplicate of that one." Applies when you need a resolved actor id in contexts where no relation edge exists yet (e.g. cross-connection queries that start from an Actor, not from a donation or meeting).

   `ActorCrossConnectionsView` is the only endpoint today that uses both correctly — `COALESCE(canonical_entry_id, id)` on Actors, `canonical_donor_id`/`canonical_recipient_id`/`canonical_actor_id` on relation tables. Most endpoints only need edge-level. Don't use `canonical_entry` as a substitute for the edge-level field or vice versa — they resolve different things.

2. **Effective actor on every serializer that shows a name.** `MeetingAttendeeSerializer` uses `source='effective_actor'`. `DonationDetailSerializer` does not — currently a bug. Fix is to switch its `donor` / `recipient` sources to `effective_donor` / `effective_recipient`.

3. **Polymorphic prefetch on every endpoint that returns `ActorSummarySerializer`.** Without `select_related('polymorphic_ctype')`, each row triggers a `ContentType` fetch. This is the N+1 that hurts the most.

4. **Partial-date handling.** `Membership.start_date` / `end_date` are `CharField` (YYYY, YYYY-MM, YYYY-MM-DD). `Donation.received_date` / `accepted_date` / `reported_date` are `DateField`. `MinisterialMeeting.meeting_date` is `DateField`. Know which you're on before reaching for `ExtractYear` vs substring.

5. **"Effective donation date".** Prefer `Coalesce('accepted_date', 'reported_date', 'received_date')`. Donors don't always report the actual transaction date; accepted_date is the most reliable signal. `FundingSummaryView` already does this — copy the pattern.

6. **Data-quality filters are a business rule, not a security filter.** Hiding blank-name rows or single-word "Director" pseudo-persons is fine *when the question being asked cares about real people*. When the question is "how many raw rows did we import?", don't filter. Be explicit in the endpoint's docstring about which it is.

---

## 8. Known issues (as of 2026-04-17)

Priority-ordered punch list. Anything shipped from §9 should update this list.

### High — data correctness
1. ~~**`ActorDonationsReceivedView` / `ActorDonationsMadeView` miss canonical matches.**~~ **Fixed 2026-04-17.** Both views now filter `Q(...) | Q(canonical_...)` with `.distinct()`. Counts on Kemi and Johnson unchanged (neither had canonical-only donations); the fix is defensive going forward.
2. ~~**`DonationDetailSerializer` uses `donor` / `recipient` sources.**~~ **Fixed 2026-04-17.** Now uses `source='effective_donor'` / `source='effective_recipient'`. Both donation views expanded their `select_related` to include `canonical_donor` / `canonical_recipient` (and their polymorphic_ctype) so the switch doesn't introduce lazy fetches — 4 SQL queries for a 50-row page, no regression.

### High — blocks current UX work
3. ~~**No `/api/v2/actors/{pk}/activity-by-year/` endpoint.**~~ **Shipped 2026-04-17.** `ActorActivityByYearView` in `api/v2/views.py`, cached via `activity_by_year:{pk}` in `cache_utils.py`. Returns four series (donations_received, donations_made, meetings, consultancies) with canonical filtering on every actor match. Cold ~250 ms, warm ~95 ms. Unblocked the Career Shape coxcomb on Kemi (the audit trigger case).

### Medium — performance
4. ~~**`ActorMeetingsView` prefetches are incomplete.**~~ **Fixed 2026-04-17.** Expanded to `select_related` polymorphic_ctype on minister/department and `Prefetch('attendees', …select_related('actor', 'canonical_actor', …polymorphic_ctype))`. Now 3 SQL queries for a 200-meeting page (was N+1 via lazy polymorphic + canonical fetches). Hydration freeze cause addressed.
5. **`DetailPagination.max_limit = 200` silently clamps meetings fetches.** Frontend sends `limit=300` but gets 200. Not a bug, but means long-serving ministers (Johnson: 335 meetings) are truncated to the first 200. If raising this matters, measure first — the frontend needs to tolerate the extra ~50 KB and re-test hydration.
6. **Homepage concentration calc still materialises ~21k donor rows.** Candidate for a materialised view. Not urgent — Redis hides the cold path.

### Medium — graph / discoverability
6. **Department pages have no aggregate endpoint.** Department actors exist but meetings belong to ministers, not departments. Needs a `/aggregates/department-meetings/{id}/` or a per-actor summary extension. Blocks the department-pages UX tier.
7. **No attendee-resolution endpoint.** Meeting attendee names are raw strings (`actor_name_raw`) with a best-effort `actor` FK. No endpoint lets the frontend ask "resolve this raw name to a canonical actor" which is what the concatenated-names data quality problem would need.

### Low — consistency
8. ~~**Two URL families for per-actor data**~~ — resolved 2026-04-17. Formalised as Family A (REST) vs Family B (named queries) in §3; migration to consistent Family A URLs is in §11.

### From the 2026-04-17 full audit

Findings from the independent review of every endpoint against this doc. Grouped by severity.

**High — data correctness (canonical filter gaps, scattered)**

9. **`ActorConsultanciesView`** filters `Q(client_id=pk) | Q(agency_id=pk)` with no `canonical_*` and uses `ConsultancyDetailSerializer` whose `agency`/`client` fields do NOT use `effective_*` sources (only the simpler `ConsultancySerializer` does). Same two-part fix that shipped for donations on 2026-04-17 applies verbatim — highest-impact single-view fix.
10. **`ActorDetailView`** has ten annotation subqueries (`donor_id`, `recipient_id`, `client_id`, `agency_id`, `actor_id` in various combinations) that all filter by raw ids. Merged actors see counts of 0 on the detail header while relationship-list endpoints show the real number. Wrap each with `Q(...) | Q(canonical_...)`.
11. **`FundingSummaryView.base_qs = Donation.objects.filter(recipient_id=pk)`** — the reference summary endpoint misses canonical on the pivot. Every downstream computation (yearly totals, top donors, public funds, largest donation) rides on this queryset. One-line fix, wide correctness effect.
12. **`AgencyClientsView`** (raw SQL) filters `WHERE agency_id = %s` only. Merged agencies silently show "no clients". Needs `OR canonical_agency_id = %s` plus `COALESCE(canonical_..._id, ..._id)` in the CTEs.
13. **`NetworkStatsView` canonical-naive** on all four unique_* counters (`unique_donors`, `unique_recipients`, `unique_agencies`, `unique_clients`). Also uncached — see below. Counts disagree with the homepage aggregates.
14. **`DonorConcentrationView`** uses raw `donor_id` in `.values()`. Gini/HHI across merged duplicates is wrong. Also uncached.

**Medium — caching gaps**

15. **`TopDonorsView` uncached** while twin `TopRecipientsView` is cached. Not clearly intentional.
16. **`DualInfluenceView` uncached** — materialises two `distinct()` sets into Python on every call; the most expensive uncached aggregate.
17. **`DonorConcentrationView` uncached** — same cold-path cost as the homepage concentration.

**Medium — §4 checklist violations**

18. **No 404 on relationship-list views for unknown actors.** `ActorMeetingsView`, `ActorMembershipsView`, `ActorConsultanciesView`, `AgencyClientsView` return `200 {results: []}`. Summary endpoints (funding-summary, activity-by-year, meetings-summary, cross-connections) do it right. Violates §4 row 1.
19. **`ActorMembershipsView` prefetches miss polymorphic_ctype** on `person`, `organization`, and `on_behalf_of`. `MembershipDetailSerializer` uses `ActorSummarySerializer` → N+1 on ContentType per membership.
20. **`TopLobbyingClientsView` doesn't canonicalise the agencies sub-list** (`agency_id`, `agency__name`). Client side is correct; agency side isn't.
25. ~~**`DepartmentMeetingsSummaryView` returns 200 with zeros for non-department actors.**~~ **Fixed 2026-04-18 (Option A).** URL renamed to `/api/v2/departments/{id}/meetings-summary/`. View now requires `Organization` with `classification in ('Government Department', 'Legislature')` — non-department actors 404. URL name changed to `department-meetings-summary`.

**Medium — latent correctness in filters**

21. **Partial-date lexicographic comparison in membership filters.** `PoliticianFilter` / `MembershipFilterSet` compare `start_date__lte=today_iso_string` against a CharField. Lexicographic comparison is only correct for YYYY-MM-DD. ParlParse rows with YYYY-only end dates silently misclassify as historic. §7 #4 states the rule; enforcement isn't in place.
22. **`PartyViewSet` hardcodes `'2026-01-01'` as the "current" cutoff.** Silently rots — mp_count/lord_count will drift as real time passes the hardcoded date. Move to `timezone.now()` or a setting.

**Low — documentation**

23. **Two canonical schemes need disambiguation in §7.** `MeetingAttendee.canonical_actor_id` is edge-level resolution (this particular attendee is really that canonical actor). `Actor.canonical_entry` is identity-level resolution (this actor is a duplicate of that one). `ActorCrossConnectionsView` correctly mixes both; most other endpoints only touch one. Future refactors could collapse them incorrectly — worth a §7 paragraph distinguishing "edge canonical" (on the relation table) from "identity canonical" (on the Actor itself) and when each applies.
24. **`HomepageStatsView` consultancy slice ignores `received_after`/`received_before`.** Honest comment in code; arguably wrong. Either honour the filter or document the exception.

---

## 9. Roadmap

Ordered by "what unblocks the most frontend work per hour of backend work".

### Next
1. ~~**`activity-by-year/` endpoint**~~ — shipped 2026-04-17.
   - ~~**Pending extension: `category_breakdown` field.**~~ **Shipped 2026-04-18.** `.values('donation_type').annotate(count=Count('id'), total=Sum('value'))` on the same canonical-filtered donations-received queryset. NULL/empty → `'Unknown'`. Same cache key, same TTL. Unblocks the politician-profile waffle. Verified: Kemi (546) returns 4 categories; 227ms cold.
2. ~~**Canonical filter fix** on donations-received/made~~ — shipped 2026-04-17.
3. ~~**Meeting prefetch expansion**~~ — shipped 2026-04-17. Verified 3 queries for 200 meetings.

### After that
4. ~~**`DonationDetailSerializer` effective-actor sources**~~ — shipped 2026-04-17.
5. ~~**Department summary endpoint**~~ — shipped 2026-04-17 at `/api/v2/actors/{id}/meetings-summary/`; URL moved 2026-04-18 to `/api/v2/departments/{id}/meetings-summary/` and scoped to `Government Department` / `Legislature` classifications (non-department actors 404). Returns `{total_meetings, unique_attendees, unique_ministers, by_year, top_attendees, top_ministers}`. Canonical-resolved via `Coalesce(canonical_actor_id, actor_id)` on attendees. Cached 1h, invalidated in `cache_utils.invalidate_actor()`.

### Next wave (from 2026-04-17 audit)

Ordered as the audit recommended — highest impact per hour first. All five fix canonical / correctness gaps:

6. **`ActorConsultanciesView`** — canonical filter + `effective_*` serializer sources + polymorphic prefetch + 404 existence check. Mirrors the donation fix shipped 2026-04-17.
7. **`ActorDetailView` ten annotation subqueries** — wrap each with `Q(raw_id) | Q(canonical_..._id)`. Eliminates the detail/list count disagreement on merged actors.
8. **`FundingSummaryView` base_qs** — `Q(recipient_id=pk) | Q(canonical_recipient_id=pk)`. One line, corrects six downstream computations.
9. **`NetworkStatsView`** — canonical on `unique_*` counters + add `make_aggregate_cache_key` wrapper.
10. **`AgencyClientsView` raw SQL** — `WHERE agency_id = %s OR canonical_agency_id = %s` (both slots) + `COALESCE(canonical_..._id, ..._id)` in CTEs + 404 + cache.

### After that (audit follow-ups)

11. **Cache the three uncached aggregates** — `TopDonorsView`, `DualInfluenceView`, `DonorConcentrationView`. TopDonorsView inconsistency with TopRecipientsView is the cheapest; DualInfluenceView is the most valuable (most expensive uncached).
12. **404 on every relationship-list view** — `ActorMeetingsView`, `ActorMembershipsView`, `ActorConsultanciesView`, `AgencyClientsView` should all do the existence check that summary endpoints already do. §4 row 1.
13. **`ActorMembershipsView` polymorphic prefetch** — add `person__polymorphic_ctype`, `organization__polymorphic_ctype`, `on_behalf_of__polymorphic_ctype`.
14. **Membership temporal filter correctness** — `PoliticianFilter`/`MembershipFilterSet` do lexicographic comparison of ISO strings against CharField dates. Rows with YYYY-only dates silently misclassify. Needs a helper that handles partial dates correctly.
15. **`PartyViewSet` hardcoded `'2026-01-01'`** — replace with `timezone.now()` or a setting. Silent drift every year.
16. **OpenAPI polish** — tags, examples, response shapes for the endpoints that exist. `drf-spectacular` is already wired up; most views lack docstrings.
17. **Membership canonicalisation for the per-date party/role lookup.** `_DonationContextMixin` uses `d.recipient_id` to fetch memberships, but if the effective recipient differs from the stored recipient, memberships may live on the canonical side. Low impact today (most politicians aren't merged) but worth revisiting when entity resolution runs on politicians. Same concern for `get_donor_key_people` (key people keyed by original donor_id, now shown under the canonical name).

### Later
7. **Materialised view for homepage concentration calc** — only if the cold-cache path becomes visible to users.
8. **Test suite foundation** — the one exception to "we move fast because we don't test" is entity resolution. A regression on the canonical filter would silently corrupt everything downstream. Start here before any other test work.

---

## 10. Decisions that should stop getting relitigated

- **Hybrid API shape: REST-shaped core resources + named aggregate/summary endpoints.** Neither a pure-REST resource model nor a pure-RPC/GraphQL one. §1 and §3 formalise the split. Adding a new endpoint: decide which family it belongs in first.
- **Popolo-based schema.** Lived with it long enough to know the trade-offs; not changing it.
- **Polymorphic Actor.** Makes ForeignKey-to-any-actor work cleanly; the prefetch cost is accepted in exchange.
- **Read-only API.** No mutations via the API. Imports own the write path.
- **Redis, 1h TTL, on-import invalidation.** Works. Don't switch to a different caching strategy without a concrete reason.
- **Partial-date CharFields for `Membership` and `Consultancy`; real `DateField`s for Donation and Meeting.** The mismatch is deliberate — political roles genuinely have fuzzy dates, financial transactions don't.
- **One API version, `v2`.** No `v3` until a breaking change is forced.

---

## 11. URL migration plan (page-keyed, opportunistic)

Some existing URLs don't match §3's convention — most notably `donations-received/` and `donations-made/`, which should collapse to one collection with a `?role=` filter. Rather than a big-bang rename, we cut over **as each frontend page comes up in UX rotation**. When a page is being touched, its endpoints are migrated in the same pass; when it isn't, they stay.

Rule of thumb: **Family A URLs are fair game for migration; Family B URLs don't need to move** (they're already named queries, which is honest).

### Cut-over table

| Page (UX tier) | Endpoint today | Target | Family | Notes |
|---|---|---|---|---|
| Politician profile | ~~`/actors/{id}/donations-received/`~~ | `/actors/{id}/donations/?role=recipient` | A | ✅ **Shipped 2026-04-18.** Consolidated into `ActorDonationsView`; old URL unmounted. §8 #10 canonical subqueries remain open as a separate item. |
| Politician profile | ~~`/actors/{id}/donations-made/`~~ | `/actors/{id}/donations/?role=donor` | A | ✅ **Shipped 2026-04-18.** Same view, `?role=donor`; old URL unmounted. Missing/invalid `role` → 400. |
| Politician profile | `/actors/{id}/meetings/` | unchanged | A | Already correct shape |
| Politician profile | `/actors/{id}/memberships/` | unchanged | A | Add polymorphic_ctype prefetch (§9 #13) while in the file |
| Politician profile | `/actors/{id}/activity-by-year/` | unchanged | B | Summary endpoint — named query, stays |
| Org / lobbying agency | `/actors/{id}/consultancies/` | unchanged (Family A) | A | Fix canonical + effective-sources (§9 #6) in the same pass |
| Org / lobbying agency | `/actors/{id}/agency-clients/` | unchanged (Family B named query) | B | Fix canonical SQL + add cache + 404 (§9 #10) in the same pass |
| Party profile | `/actors/{id}/funding-summary/` | unchanged | B | |
| Homepage | `/aggregates/*` | unchanged | B | All named queries, correctly shaped |
| Network page | `/aggregates/minister-network/`, `/aggregates/network-stats/` | unchanged | B | Fix §9 #9 canonical + cache on NetworkStatsView |
| Directory | `/politicians/`, `/parties/` (router-backed ViewSets) | unchanged | A | Fix §9 #14 partial-date filter, §9 #15 hardcoded date |

### Implementation rules for each cut-over

1. **Add the new URL first**, leave the old one wired. No 410s. Two URL rows pointing at the same view class is fine — the view doesn't care which URL dispatched it.
2. **Update the frontend page to use the new URL** in the same PR. Both URLs are live in prod, the page uses the new one.
3. **Leave the old URL alive for a release cycle.** Removing it is a separate, clearly-labelled PR.
4. **When removing the old URL**, grep the whole repo first. If anything besides the frontend page we just migrated is still calling it, that caller gets its own migration ticket.

---

## 12. Audit stance

When the audit agent reviews new or existing endpoints, recommendations must reference **current code, the §11 migration plan, and the §9 roadmap**. Concretely:

- Don't recommend a new URL shape that §11 already has planned — reference the migration row instead.
- Don't recommend a correctness fix that's already in §9 — mark it as already-queued.
- When flagging a Family A / Family B misclassification (e.g. "this endpoint is named like an aggregate but returns rows"), propose either a rename (Family B → proper summary shape) or a migration to Family A, not both.
- Audit findings that don't map to §9, §11, or an existing §8 entry are net-new and should be proposed as additions to §8.

This keeps reviews grounded: the doc is the canonical plan, audits annotate it, nothing escapes as a one-off recommendation that disappears into chat.

---

## References

- `systems-architecture.md` — what exists (components, deployment, diagrams).
- `data-models.md` — the Popolo schema.
- `API_REFERENCE.md` — endpoint catalogue.
- `DATA_PIPELINE.md` — import + quality + entity resolution.
- `api/v2/cache_utils.py` — cache keys + invalidation helpers.
- `api/v2/views.py:FundingSummaryView` — reference summary endpoint pattern.
