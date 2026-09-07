# TRD — Technical Requirements Document

**Project:** HH Goa 2026 — Task 3: Face Identification & Blockchain Verification  
**Version:** 1.0  
**Date:** 2026-09-07

## 1. Technical Objective

Implement a local-first, CLI-driven pipeline that performs real-time face processing, reverse-image search, social-result validation, deterministic evidence hashing, blockchain anchoring, and independent re-verification.

## 2. Recommended Architecture

```text
┌──────────────────────┐
│ CLI / Orchestrator   │
└──────────┬───────────┘
           │
           v
┌──────────────────────┐
│ Image Ingestion      │
│ Pillow/OpenCV        │
└──────────┬───────────┘
           │
           v
┌──────────────────────┐
│ Face Engine          │
│ InsightFace/ArcFace  │
│ ONNX Runtime         │
└──────────┬───────────┘
           │ normalized face image
           v
┌──────────────────────┐
│ Search Provider      │
│ SerpApi Google Lens  │
└──────────┬───────────┘
           │ candidates
           v
┌──────────────────────┐
│ Candidate Validator  │
│ social-domain check  │
│ HTTP/redirect check  │
└──────────┬───────────┘
           │ selected evidence
           v
┌──────────────────────┐
│ Evidence Builder     │
│ canonical JSON       │
│ SHA-256 fingerprint  │
└──────────┬───────────┘
           │
           ├───────────────┐
           v               v
┌─────────────────┐ ┌──────────────────┐
│ Local Audit Log │ │ Ethereum Sepolia │
│ JSON            │ │ EvidenceRegistry │
└─────────────────┘ └─────────┬────────┘
                              │
                              v
                    ┌──────────────────┐
                    │ Re-verifier      │
                    │ on-chain vs calc │
                    └──────────────────┘
```

## 3. Component Specifications

### 3.1 Image ingestion

**Libraries:** Pillow, OpenCV  
**Responsibilities:**
- read bytes
- validate MIME type and dimensions
- normalize color space
- resize if required
- compute original file SHA-256

Recommended input floor: at least 300 px on the shortest side for search reliability. TinEye documents 300 px as a useful lower bound for its search API and accepts JPEG/PNG/WebP/AVIF/GIF/BMP/TIFF up to 1 MB; for the MVP use a 500 KB–1 MB normalized image. citeturn150875search0

### 3.2 Face engine

**Preferred:** InsightFace + ONNX Runtime  
**Alternative:** DeepFace

Pipeline:

```text
image
 → detector
 → landmarks/alignment
 → normalized crop
 → ArcFace/Buffalo-style embedding
```

Output contract:

```json
{
  "face_count": 1,
  "bbox": [x1, y1, x2, y2],
  "embedding_model": "<pinned-model>",
  "embedding_dim": 512,
  "crop_sha256": "..."
}
```

Do not store the embedding on-chain.

### 3.3 Reverse-image search

**Primary:** SerpApi Google Lens.

Current capabilities include:
- upload an image and search using an `image_id`
- `exact_matches`
- `visual_matches`
- structured JSON response
- optional localization and safety settings

SerpApi currently publishes a free tier as well as paid plans; the current public pricing page lists 250 searches/month for the free plan. citeturn127503search0turn127503search1

Integration abstraction:

```python
class ReverseSearchProvider:
    def search(self, image_path: str) -> SearchResponse:
        ...
```

Response model:

```json
{
  "provider": "google_lens",
  "search_id": "...",
  "candidates": [
    {
      "title": "...",
      "source": "...",
      "url": "https://...",
      "image_url": "https://...",
      "rank": 1,
      "match_type": "exact_match"
    }
  ]
}
```

### 3.4 Social result validator

Algorithm:

1. Parse candidate URL.
2. Remove tracking query parameters for provenance normalization.
3. Extract hostname.
4. Compare against configured social allowlist.
5. Follow redirects.
6. Record HTTP status and final URL.
7. Reject login-only/private pages where practical.
8. Continue to next candidate until a valid social result is found.

Example allowlist:

```python
SOCIAL_DOMAINS = {
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "tiktok.com",
    "www.tiktok.com",
    "linkedin.com",
    "www.linkedin.com",
}
```

This is a validation policy, not a guarantee that a given provider will return those domains for every input.

### 3.5 Evidence builder

The evidence object must be canonical.

Rules:
- UTF-8 encoding
- sorted JSON keys
- no insignificant whitespace
- normalized URL
- ISO-8601 UTC timestamp
- lowercase hex hashes
- versioned schema

Canonicalization pseudocode:

```text
canonical_json = JSON.stringify(evidence, sort_keys=True, separators=(',', ':'))
evidence_hash = SHA256(canonical_json.encode('utf-8'))
```

### 3.6 Blockchain

**Network:** Ethereum Sepolia  
**Contract language:** Solidity  
**Tooling:** Hardhat + OpenZeppelin Contracts  
**Client:** web3.py or ethers.js

OpenZeppelin documents testnet deployment and notes Sepolia as a development/test network. citeturn819969search6 OpenZeppelin Contracts provides reusable, community-vetted Solidity components and role/access-control utilities. citeturn819969search4turn819969search5

### 3.7 Smart contract

Minimal interface:

```solidity
struct Evidence {
    bytes32 evidenceHash;
    string sourceUrl;
    string searchProvider;
    uint64 createdAt;
    address submitter;
}

function recordEvidence(
    bytes32 evidenceHash,
    string calldata sourceUrl,
    string calldata searchProvider
) external returns (uint256 id);

function getEvidence(uint256 id) external view returns (Evidence memory);

function verifyEvidence(uint256 id, bytes32 evidenceHash)
    external
    view
    returns (bool);
```

Emit an event:

```solidity
event EvidenceRecorded(
    uint256 indexed id,
    bytes32 indexed evidenceHash,
    string sourceUrl,
    string searchProvider,
    address indexed submitter
);
```

### 3.8 Local audit storage

Directory layout:

```text
runs/
  <run_id>/
    input.json
    search_response.json
    selected_evidence.json
    blockchain_receipt.json
    verification.json
```

Avoid storing full external images unless needed for debugging and legally/ethically appropriate.

## 4. Repository Structure

```text
face-blockchain-verifier/
├─ app/
│  ├─ cli.py
│  ├─ config.py
│  ├─ pipeline.py
│  ├─ models.py
│  ├─ face/
│  │  ├─ engine.py
│  │  └─ preprocess.py
│  ├─ search/
│  │  ├─ base.py
│  │  └─ serpapi_lens.py
│  ├─ evidence/
│  │  ├─ canonicalize.py
│  │  └─ fingerprint.py
│  ├─ social/
│  │  └─ validator.py
│  └─ blockchain/
│     ├─ client.py
│     └─ abi.py
├─ contracts/
│  └─ EvidenceRegistry.sol
├─ scripts/
│  └─ deploy.ts
├─ tests/
│  ├─ test_canonicalization.py
│  ├─ test_social_validation.py
│  ├─ test_search_adapter.py
│  └─ test_fingerprint.py
├─ runs/
├─ docs/
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ package.json
├─ hardhat.config.ts
└─ README.md
```

## 5. Configuration

`.env.example`:

```env
SERPAPI_KEY=
SEPOLIA_RPC_URL=
WALLET_PRIVATE_KEY=
CONTRACT_ADDRESS=
SEARCH_TIMEOUT_SEC=30
SOCIAL_TIMEOUT_SEC=15
MAX_SEARCH_RESULTS=10
```

Never commit a real `.env`.

## 6. Python Runtime

Use a pinned Python version with broad ML package compatibility, preferably Python 3.11 for the hackathon build. Do not make Python 3.14 a hard requirement for this project because computer-vision dependency wheels can lag new interpreter versions.

## 7. APIs / Interfaces

### CLI

```bash
python -m app.cli run --image ./samples/input.jpg
python -m app.cli verify --evidence-id 1 --run ./runs/20260907_123456
```

### Internal pipeline result

```json
{
  "status": "VERIFIED",
  "run_id": "...",
  "face_count": 1,
  "selected_url": "https://...",
  "evidence_hash": "0x...",
  "tx_hash": "0x...",
  "contract_address": "0x...",
  "evidence_id": 1,
  "verified": true
}
```

## 8. Error Handling

All external dependencies shall be wrapped with:

- timeout
- retry with bounded attempts
- structured exception
- human-readable CLI error
- no secret leakage

Do not silently substitute a hardcoded social result when the live search fails. The task specifically requires a genuine search and a real matching post. fileciteturn0file0L11-L19

## 9. Privacy and Security Controls

- Use only consented/test face images.
- Delete raw face files after the demo where possible.
- Hash evidence instead of putting raw images on-chain.
- Do not store embeddings on-chain.
- Use a disposable testnet account.
- Limit the smart contract to non-sensitive provenance.
- Add a visible disclaimer: “A visual match is not proof of identity.”

The DPDP Act and 2025 Rules should be reviewed with counsel for any real deployment; this document is an engineering control list, not legal advice. citeturn467868search0turn467868search2

## 10. Performance Targets for MVP

These are engineering targets, not claims about actual final performance:

| Stage | Target |
|---|---:|
| Image preprocessing | < 1 s |
| Face inference on CPU | < 10 s |
| Search API round trip | < 20 s |
| Evidence fingerprinting | < 0.5 s |
| Blockchain transaction submission | < 30 s excluding network congestion |
| Local verification | < 2 s |

Record actual timings in the run artifact rather than inventing benchmark claims.

## 11. Technology Decision Matrix

| Option | Pros | Cons | Decision |
|---|---|---|---|
| InsightFace + ONNX | Local, strong recognition stack, no per-request face API fee | Model licensing/dependency management needs care | **Primary** |
| DeepFace | Simple Python API, multiple backends | Heavier dependency surface | Fallback |
| TinEye API | Real reverse-image search; direct upload | Paid search bundles for real API usage | Fallback/alternative |
| SerpApi Google Lens | Current image upload + exact/visual match API | Third-party paid service; must manage API key | **Primary** |
| Google Custom Search JSON | Official Google API | Current documentation says it is closed to new customers; not suitable as new-project primary choice | Reject |
| Ethereum Sepolia | Familiar EVM flow, public explorer, suitable for demos | Requires funded test wallet | **Primary** |
| Local simulated chain | Cheapest and offline | Less convincing public proof | Emergency fallback |

Google's current Custom Search JSON API page states the API is closed to new customers, so it should not be selected for a new implementation. citeturn142345search0

## 12. Optional IPFS Extension

IPFS can be added later if a content-addressed evidence bundle is needed. IPFS CIDs are derived from content hashes, so changing content changes its content identifier; however, CIDs are not identical to a raw file hash in all cases. citeturn819969search0

For the hackathon MVP, IPFS is optional because the task can be satisfied with an on-chain hash alone.
