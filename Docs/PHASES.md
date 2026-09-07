# Phases — Build, Test, Demo, Submission

**Deadline from task brief:** September 7, 2026 at 11:59 PM. fileciteturn0file0L37-L39

## Phase 0 — Scope Lock

### Objective
Freeze the MVP to the exact evaluator path.

### Deliverables
- architecture selected
- provider selected
- blockchain selected
- repository created

### Exit criteria
The team agrees that there is no website/dashboard requirement for the MVP.

---

## Phase 1 — Face Pipeline

### Objective
Prove that a user image can be transformed into a face crop/embedding.

### Tasks
- input validation
- face detector
- alignment
- embedding
- output JSON
- timing log

### Exit criteria
A known-good test image produces one detected face and an embedding consistently.

### Failure gate
Do not proceed to final integration until the local face pipeline runs offline.

---

## Phase 2 — Genuine Search

### Objective
Prove live reverse-image search.

### Tasks
- provider credentials
- image upload
- exact-match request
- visual-match fallback
- raw JSON capture
- result ranking

### Exit criteria
A search request made during runtime returns at least one useful candidate.

### Important rule
No hardcoded result URL may be used as the success path. The official brief explicitly rejects pre-picked/hardcoded search results. fileciteturn0file0L11-L14

---

## Phase 3 — Social Match Validation

### Objective
Turn search candidates into a verified public social-media candidate.

### Tasks
- social hostname allowlist
- redirect handling
- HTTP validation
- candidate retry loop
- selected-result artifact

### Exit criteria
The CLI can show a dynamically discovered public social URL in the same run.

### Contingency
If no social result is returned for a particular image, switch test fixtures rather than hardcoding a URL.

---

## Phase 4 — Evidence Fingerprint

### Objective
Create a deterministic fingerprint of the discovered evidence.

### Tasks
- canonical JSON schema
- URL normalization
- image hash
- SHA-256
- unit tests

### Exit criteria
The same evidence produces the same hash across repeated local runs.

---

## Phase 5 — Blockchain Registry

### Objective
Anchor the fingerprint on-chain.

### Tasks
- Solidity contract
- unit tests
- compile
- deploy to Sepolia
- record evidence
- read evidence

### Exit criteria
A real transaction hash and evidence ID are available.

### Blockchain policy
Store only the hash and minimal provenance. The task explicitly permits a hash/fingerprint instead of the full post. fileciteturn0file0L15-L19

---

## Phase 6 — Re-verification

### Objective
Prove the core tamper-evidence concept.

### Tasks
- fetch stored record
- reconstruct evidence
- recompute hash
- compare
- output VERIFIED/MISMATCH

### Exit criteria
The final run shows:

```text
ON-CHAIN HASH == COMPUTED HASH
RESULT: VERIFIED
```

Also test a deliberately modified evidence object and confirm:

```text
ON-CHAIN HASH != COMPUTED HASH
RESULT: MISMATCH
```

---

## Phase 7 — Integration CLI

### Objective
Join all stages into one evaluator-friendly command.

### Target command

```bash
python -m app.cli run --image samples/known_good.jpg
```

### Exit criteria
One command produces the complete pipeline without manual intervention except necessary wallet/network confirmation already configured in advance.

---

## Phase 8 — Reliability Rehearsal

### Objective
Remove demo-day surprises.

### Tasks
- run three known-good images
- run one no-face image
- run with slow network
- confirm testnet wallet balance
- confirm API quota
- confirm contract address
- confirm RPC endpoint
- confirm recording window

### Exit criteria
At least one known-good image completes successfully three times in rehearsal.

---

## Phase 9 — Documentation

### Objective
Make the repository evaluator-readable.

### Required docs
- README.md
- PRD.md
- TRD.md
- ARCHITECTURE.md
- IMPLEMENTATION_PLAN.md
- PHASES.md
- TEST_PLAN.md
- RESEARCH.md

### Exit criteria
A new user can understand what the project does, how to run it, which blockchain was used, and the limitations. The task brief explicitly requires those topics in the README. fileciteturn0file0L22-L24

---

## Phase 10 — Final Recording & Submission

### Recording order

```text
00:00 command starts
00:05 image accepted
00:10 face found + embedding
00:20 live reverse search
00:35 matching social post
00:45 evidence hash
00:55 blockchain transaction
01:10 on-chain readback
01:20 VERIFIED
```

The timing above is a suggested presentation shape, not a requirement.

### Submission gate
Do not submit until:
- recording link opens
- repository is public/accessibly shared as required by the event
- README runs from clean checkout
- contract address is present
- transaction can be inspected
- final pipeline returns VERIFIED

The brief says no resubmissions will be allowed. fileciteturn0file0L25-L29
