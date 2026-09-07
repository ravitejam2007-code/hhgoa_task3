# PRD — Face Identification & Blockchain Verification

**Project:** HH Goa 2026 — Shortlisting Task 3  
**Document:** Product Requirements Document  
**Version:** 1.0  
**Date:** 2026-09-07  
**Status:** Build-ready

## 1. Product Summary

Build a demonstrable end-to-end pipeline that takes a face-scan image, extracts a face embedding, performs a genuine reverse-image/web search, identifies at least one matching public social-media post, fingerprints the discovered evidence, writes the fingerprint to a blockchain, and then independently verifies the discovered evidence against the on-chain record.

The official brief explicitly defines the pipeline as **face scan input → web/social media search → blockchain upload/verification**, requires a genuine search rather than a hardcoded result, permits storing a hash/fingerprint rather than the raw post, does not require a website, and requires a GitHub repository plus an end-to-end screen recording. See the source brief: fileciteturn0file0L3-L24

## 2. Problem Statement

A visual investigation workflow can produce useful evidence but is difficult to audit if the discovered web content can change after discovery. The product demonstrates a chain-of-custody pattern:

1. Convert an input face scan into a machine-readable face representation.
2. Search the open web for visually matching content.
3. Confirm that a returned result is a real, publicly accessible social-media post.
4. Create a deterministic fingerprint of the discovered evidence.
5. Anchor that fingerprint on a blockchain.
6. Recompute the fingerprint later and prove whether the evidence matches the anchored record.

## 3. Goals

### Primary goals

- Detect at least one face in an input image.
- Generate a face embedding and record model/detector metadata.
- Perform a real reverse-image search using an external search provider.
- Return a genuine result discovered at runtime, not a hardcoded URL.
- Prefer and validate a public social-media URL.
- Create a deterministic evidence package and cryptographic fingerprint.
- Store the fingerprint and essential provenance on an EVM testnet.
- Re-run verification from the discovered evidence and report **VERIFIED** or **MISMATCH**.
- Make the entire flow demonstrable in one terminal/CLI run.
- Publish the full source in GitHub with a reproducible README.

### Secondary goals

- Keep the raw face image and raw social-media content off-chain.
- Keep API keys server-side/local in environment variables.
- Make the search provider replaceable.
- Log enough metadata for debugging without exposing unnecessary personal information.

## 4. Non-goals

- No production website is required.
- No large-scale identity database is required.
- No biometric identification of a person by name is required.
- No facial attribute inference such as age, gender, or ethnicity is part of the MVP.
- No mainnet deployment is required.
- No permanent storage of personal images on blockchain is required.
- No automated legal conclusion or assertion of a person’s identity is produced.

## 5. Target Users

### Primary user

Hackathon evaluator reviewing the pipeline and screen recording.

### Secondary users

Developers/investigators who need a reproducible proof-of-discovery and integrity check for publicly available visual evidence.

## 6. User Journey

```text
User selects face image
        ↓
Validate image
        ↓
Detect face(s)
        ↓
Select target face / create embedding
        ↓
Create normalized search image
        ↓
Reverse-image search
        ↓
Rank candidate results
        ↓
Validate social-media URL
        ↓
Extract evidence metadata + image
        ↓
Canonicalize evidence
        ↓
SHA-256 fingerprint
        ↓
Record hash + provenance on Ethereum Sepolia
        ↓
Read record back
        ↓
Re-fetch/reconstruct evidence
        ↓
Recompute hash
        ↓
Compare off-chain hash vs on-chain hash
        ↓
VERIFIED / MISMATCH
```

## 7. Functional Requirements

### FR-01 — Input

The system shall accept JPEG, PNG, or WebP images.

Acceptance:
- Reject unsupported formats.
- Reject corrupt files.
- Reject images that contain no detectable face.

### FR-02 — Face detection and encoding

The system shall detect a face and generate an embedding using a supported face-recognition model. A 1:N/identification framing is appropriate for the recognition stage; NIST explicitly maintains a FRTE 1:N identification evaluation track. citeturn819969search1turn819969search7

Recommended implementation: InsightFace/ArcFace or DeepFace with a fixed model and detector configuration. InsightFace supports detection, recognition, and alignment; DeepFace exposes detection, representation, verification, and search workflows. citeturn486093search1turn486093search0

Acceptance:
- Output includes face bounding box.
- Output includes embedding length/model identifier.
- Output includes a deterministic image/face preprocessing version.

### FR-03 — Genuine reverse-image search

The system shall execute a live search at runtime and must not contain a preselected result URL.

Recommended provider: Google Lens through SerpApi, because the current API supports image upload, exact matches, visual matches, and structured JSON results. citeturn127503search0turn127503search9

Fallback provider: TinEye API, which supports direct image upload and real reverse-image search over a large index; its current commercial API requires purchased search bundles for real searches, while the sandbox does not return real matches. citeturn150875search0turn150875search5turn150875search6

Acceptance:
- Search request occurs during the recorded run.
- Search response is captured in raw JSON for debugging.
- At least one returned candidate is selected dynamically.

### FR-04 — Social-media match

The system shall validate that at least one selected match is a real public social-media post/page.

Recommended validation:
- Normalize the candidate URL.
- Check hostname against an allowlist such as `instagram.com`, `facebook.com`, `x.com`, `twitter.com`, `tiktok.com`, `linkedin.com`, or another evaluator-approved public social domain.
- Perform an HTTP HEAD/GET with redirects enabled.
- Preserve final URL and response timestamp.

Acceptance:
- The screen recording visibly shows the discovered social URL.
- The result was returned by the search engine rather than entered as an application constant.

### FR-05 — Evidence package

Create a canonical JSON object containing only fields needed to reproduce the verification operation:

```json
{
  "source_url": "https://...",
  "final_url": "https://...",
  "search_provider": "google_lens",
  "search_type": "exact_matches",
  "result_title": "...",
  "image_sha256": "...",
  "discovered_at_utc": "...",
  "pipeline_version": "1.0.0"
}
```

Do not store the raw face image or post image on-chain.

### FR-06 — Evidence fingerprint

Compute SHA-256 over canonical UTF-8 JSON with stable key ordering. Store the 32-byte digest as the blockchain evidence fingerprint.

### FR-07 — Blockchain record

Deploy a minimal Solidity contract to Ethereum Sepolia. The record shall include:

- evidence ID
- evidence hash
- source URL or a short provenance reference
- search provider
- block timestamp
- submitter address

Ethereum testnets such as Sepolia are intended for development/testing; OpenZeppelin documents Sepolia as a test network and recommends not using mainnet while developing. citeturn819969search6

### FR-08 — Re-verification

The system shall read the stored record from-chain, reconstruct the evidence fingerprint, and compare it with the stored hash.

Output:

```text
On-chain hash:  <32-byte hash>
Computed hash:  <32-byte hash>
Result: VERIFIED
```

### FR-09 — Audit log

Save a local run artifact containing:

- run ID
- input file hash
- model name/version
- search provider
- returned candidates
- selected social URL
- evidence hash
- transaction hash
- contract address
- verification result

The audit artifact should be safe to share with the evaluator after removing secrets.

## 8. Non-functional Requirements

### NFR-01 — Reproducibility

A new developer should be able to install dependencies, configure environment variables, and run the CLI from a clean checkout.

### NFR-02 — Determinism

The evidence canonicalization and hashing stage shall be deterministic.

### NFR-03 — Security

- Never commit API keys or blockchain private keys.
- Use `.env` locally and `.env.example` in GitHub.
- Use a disposable testnet wallet.
- Store only the minimum required provenance on-chain.

### NFR-04 — Privacy

Treat face images and embeddings as sensitive personal data. The Indian Digital Personal Data Protection Act, 2023 establishes obligations around lawful processing of digital personal data, and MeitY published the DPDP Rules, 2025. The project should therefore use consented/test images and minimize retention for the hackathon demonstration. citeturn467868search0turn467868search30turn467868search2

### NFR-05 — Failure transparency

The application must distinguish:
- `NO_FACE_FOUND`
- `SEARCH_ERROR`
- `NO_SOCIAL_MATCH`
- `SOCIAL_FETCH_ERROR`
- `CHAIN_ERROR`
- `VERIFICATION_MISMATCH`
- `VERIFIED`

## 9. MVP Acceptance Criteria

The MVP is complete only when all of the following can be shown in one uninterrupted screen recording:

1. Input face scan is selected.
2. Face detection/encoding completes.
3. Live reverse-image search executes.
4. A dynamically returned result is shown.
5. A real social-media result is shown.
6. Evidence fingerprint is computed.
7. Blockchain transaction succeeds.
8. Transaction hash and contract address are shown.
9. The record is read from-chain.
10. Recomputed hash equals on-chain hash and the UI reports `VERIFIED`.

The brief explicitly requires the screen recording to show the flow from face scan to social post found to blockchain upload/verification. fileciteturn0file0L25-L36

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Reverse search returns no social result | High | Keep a tested dataset of public images; support provider fallback; test multiple legitimate public images |
| Search provider API unavailable | High | Provider abstraction; cache only for development; do not use cached results in final proof |
| Search result is not accessible | Medium | Validate final URL and retain top 5 candidates |
| Face model packaging failure | High | Pin Python version and dependency versions; run CPU-only baseline |
| Sepolia wallet has no ETH | Medium | Fund test wallet before recording; keep a second funded test wallet |
| On-chain data exposes too much information | High | Store hash + minimal provenance; never store face embeddings/raw images |
| Face-recognition bias/false match | High | Treat embedding as a retrieval feature only; display no identity claim; NIST notes material accuracy variation can exist across demographic groups. citeturn819969search9 |

## 11. Product Decision

**Recommended MVP stack:** Python + InsightFace/ONNX Runtime for local face processing, SerpApi Google Lens API for live reverse-image search, Python `web3.py` for chain interaction, Solidity + Hardhat for the evidence registry, and Ethereum Sepolia for the demonstration network.

This stack is chosen for evaluator visibility, low system complexity, genuine search capability, and straightforward re-verification.

## 12. Definition of Done

- `PRD.md`, `TRD.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `PHASES.md`, and `TEST_PLAN.md` are committed.
- The pipeline works end to end on at least one known-good public test image.
- A real search provider is called.
- The result URL is discovered dynamically.
- A Sepolia transaction is mined.
- Re-verification returns `VERIFIED`.
- README documents setup, blockchain, limitations, and exact run command.
- Screen recording is captured without edits, per the task brief. fileciteturn0file0L30-L36

## 13. External Research Sources

- NIST Face Technology Evaluations: https://www.nist.gov/programs-projects/face-technology-evaluations-frtefate
- NIST FRTE 1:N: https://pages.nist.gov/frvt/html/frvt1N.html
- InsightFace: https://github.com/deepinsight/insightface
- DeepFace: https://github.com/serengil/deepface
- SerpApi Google Lens: https://serpapi.com/google-lens-api
- TinEye API: https://services.tineye.com/TinEyeAPI
- Ethereum/OpenZeppelin deployment guidance: https://docs.openzeppelin.com/contracts/5.x/learn/deploying-and-interacting
- IPFS content addressing: https://docs.ipfs.tech/concepts/content-addressing/
- India Code DPDP Act: https://www.indiacode.nic.in/indiacode/handle/123456789/22037
- MeitY DPDP Rules 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
