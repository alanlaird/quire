# API discovery

Capture the exact shape of the Shelfmark and CWA endpoints quire needs to call. Fill in each section by opening browser devtools (Network tab) and performing the action by hand against the real service. Paste the relevant request/response shape here.

Status: **not yet captured** — Phase 2 work.

---

## Shelfmark — search

**Goal**: given `{title, author}`, return a list of available result objects with at least format + an identifier we can pass to the download endpoint.

- URL:
- Method:
- Query params / body:
- Required headers (auth, content-type, etc.):
- Sample response (trimmed):

Notes:

---

## Shelfmark — download

**Goal**: given a result identifier from search, trigger a download into the CWA ingest folder. Shelfmark is already configured with that as its download destination.

- URL:
- Method:
- Query params / body:
- Required headers:
- Sample response (success):
- Sample response (failure / unavailable):

Notes:

---

## CWA — OPDS search

**Goal**: given a title (and optionally an author), return whether the library already contains a match. Any non-empty result = "owned, skip".

- URL (likely `https://cwa.radi8.org/opds/search/<query>` — confirm):
- Method:
- Auth (basic, against the dedicated `quire` viewer user):
- Sample response (hit):
- Sample response (miss):
- Empty-result indicator:

Notes:

---

## Capture process

1. Open the service in a browser; sign in.
2. Open devtools, Network tab; clear; filter to XHR/Fetch.
3. Perform the action (search a known title, click download, etc.).
4. Right-click the relevant request -> Copy as cURL. Paste below, then redact secrets and translate into the sections above.
5. Repeat for each endpoint.
