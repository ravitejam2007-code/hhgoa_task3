# Implementation Plan — End-to-End Build

## 1. Execution Strategy

Build the smallest evaluator-visible path first. Do not start with a website, dashboard, database, authentication, or AI agent framework. The brief explicitly says no website is required and focuses on the pipeline. fileciteturn0file0L20-L24

## 2. Recommended Build Order

### Step 1 — Repository bootstrap

Create the repository and folder structure from `TRD.md`.

Install:
- Python 3.11
- Node.js 20+
- Git
- Hardhat

Create:

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
npm install
```

### Step 2 — Face module

Implement:

```python
def extract_face(image_path) -> FaceResult:
    ...
```

Required output:
- face count
- bbox
- aligned crop path
- model identifier
- embedding metadata

Use a single-face happy path for the MVP. If multiple faces are detected, choose the largest face and report the policy in the CLI.

### Step 3 — Search provider adapter

Implement:

```python
class GoogleLensProvider:
    def search(self, image_path) -> SearchResponse:
        ...
```

Use SerpApi's current image upload flow, then request `exact_matches` first and `visual_matches` second if necessary. citeturn127503search0turn127503search9

Do not hardcode a URL.

### Step 4 — Social candidate selection

Rank candidates:

```text
1. exact_match + social domain
2. visual_match + social domain
3. exact_match + other public web domain
4. visual_match + other public web domain
```

The MVP should only declare the social-match acceptance criterion when a social-domain candidate is actually discovered.

### Step 5 — Evidence extraction

For the selected candidate:

- normalize source URL
- obtain final URL after redirects
- preserve result title/source
- use returned image URL where possible
- download image bytes only when permitted and technically available
- compute `image_sha256`

If the provider only exposes a thumbnail, document that the fingerprint is for the retrieved search-result representation rather than claiming it is the full original post asset.

### Step 6 — Canonical fingerprint

Implement and unit-test:

```python
def evidence_hash(evidence: dict) -> bytes:
    canonical = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).digest()
```

### Step 7 — Smart contract

Create `EvidenceRegistry.sol` with:

- `recordEvidence`
- `getEvidence`
- `verifyEvidence`
- `EvidenceRecorded` event

Use OpenZeppelin only where it adds value; keep the core registry custom and auditable.

### Step 8 — Deploy to Sepolia

Deploy with Hardhat.

Save:
- contract address
- deployment transaction
- ABI
- chain ID

Use a disposable wallet funded only for testnet operation. OpenZeppelin's current documentation describes Sepolia as a development/test network. citeturn819969search6

### Step 9 — Blockchain client

Implement:

```python
def anchor_evidence(evidence_hash, source_url, provider):
    ...

def read_evidence(evidence_id):
    ...

def verify_evidence(evidence_id, computed_hash):
    ...
```

### Step 10 — Orchestrator

Implement a single command:

```bash
python -m app.cli run --image samples/known_good.jpg
```

The command must print the stages clearly:

```text
[1/8] Input accepted
[2/8] Face detected
[3/8] Face embedding generated
[4/8] Reverse image search executed
[5/8] Social post discovered
[6/8] Evidence fingerprint generated
[7/8] Blockchain record confirmed
[8/8] Re-verification: VERIFIED
```

### Step 11 — Failure testing

Explicitly test:
- no face
- unsupported image
- search API timeout
- no social result
- invalid social result
- insufficient Sepolia funds
- wrong hash during verification

### Step 12 — Screen-recording build

Use a clean terminal window and show:

1. command
2. face detection result
3. live search
4. matching social URL
5. hash
6. tx hash + evidence ID
7. on-chain record
8. `VERIFIED`

The task brief requires a plain end-to-end screen recording and says no production editing is required. fileciteturn0file0L25-L36

## 3. Known-Good Test Strategy

Do not start final recording with a random portrait.

Use a test image that has a public web/social occurrence and verify the reverse-search provider returns it reliably. Maintain at least three candidate inputs for rehearsal.

A strong practical strategy is:

```text
candidate_A.jpg  -> expected social match
candidate_B.jpg  -> expected social match
candidate_C.jpg  -> fallback
```

These are test fixtures, not hardcoded results. The application still performs the live search and dynamically selects the returned URL.

## 4. Evidence Quality Rules

For every selected result keep:

- provider name
- provider request/search ID if available
- match type
- rank
- result title
- result source
- candidate URL
- final URL
- retrieved image hash
- retrieval timestamp
- evidence schema version

## 5. Git Commit Plan

```text
chore: bootstrap repository
feat: add face detection and embedding
feat: add reverse image search provider
feat: add social candidate validation
feat: add deterministic evidence hashing
feat: add evidence registry contract
feat: add Sepolia deployment
feat: add chain verifier
feat: add end-to-end CLI
feat: add tests and docs
chore: prepare final recording
```

## 6. Submission Checklist

The brief requires:

- GitHub repository link
- screen-recording link
- submission form

The provided brief identifies the submission form as:

`https://forms.gle/oZbQGuwiNeHVcHWo8`

and states that no resubmissions will be allowed, so the final run should be rehearsed before submission. fileciteturn0file0L25-L29

## 7. Deliverables

```text
Required for evaluator
├─ GitHub repository
├─ README.md
├─ source code
├─ deployed contract address
├─ transaction hash from demonstration
├─ screen recording link
└─ submission form entry

Recommended inside repository
├─ PRD.md
├─ TRD.md
├─ ARCHITECTURE.md
├─ IMPLEMENTATION_PLAN.md
├─ PHASES.md
├─ TEST_PLAN.md
└─ RESEARCH.md
```
