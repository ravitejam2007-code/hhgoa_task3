# Architecture — Face Identification & Blockchain Verification

## 1. System Context

The application is a local CLI orchestrator with three external trust boundaries:

1. Face-recognition model runtime on the developer machine.
2. Reverse-image search provider over HTTPS.
3. Ethereum Sepolia blockchain through an RPC provider.

No hosted project website is required by the task brief. fileciteturn0file0L20-L24

## 2. Detailed Data Flow

```text
[Input JPG/PNG/WebP]
       |
       v
[Image Validator]
       |
       v
[Face Detector]
       |
       +---- no face ---> [NO_FACE_FOUND]
       |
       v
[Face Crop + Normalize]
       |
       v
[Face Encoder]
       |
       v
[Search Image]
       |
       v
[Google Lens via SerpApi]
       |
       v
[Candidate Ranking]
       |
       v
[Social URL Validator]
       |
       +---- none ---> [NO_SOCIAL_MATCH]
       |
       v
[Evidence Extractor]
       |
       v
[Canonical JSON]
       |
       v
[SHA-256]
       |
       +---------------> [Local run artifact]
       |
       v
[EvidenceRegistry.recordEvidence]
       |
       v
[Tx Receipt + Evidence ID]
       |
       v
[Read EvidenceRegistry]
       |
       v
[Recompute SHA-256]
       |
       v
[COMPARE]
      / \
     /   \
 VERIFIED  MISMATCH
```

## 3. Trust Model

### Trusted locally

- Input file hash
- Model version
- Canonicalization code
- Evidence fingerprint code

### External dependencies

- Search-provider result set
- Social page availability
- RPC/node response
- Public web content

### Blockchain guarantee

The blockchain is used as a tamper-evident timestamp/provenance anchor for a hash. It does **not** prove that the source post is truthful, authentic, or owned by a particular person. It proves that a specific fingerprint was recorded on-chain at a specific transaction/block time.

## 4. Evidence Schema

```json
{
  "schema_version": "1.0",
  "source_url": "...",
  "final_url": "...",
  "search_provider": "google_lens",
  "match_type": "exact_match",
  "title": "...",
  "image_sha256": "...",
  "discovered_at_utc": "2026-09-07T00:00:00Z",
  "pipeline_version": "1.0.0"
}
```

## 5. Hashing Rules

1. Normalize URL.
2. Normalize string whitespace.
3. Exclude fields that are expected to change during re-verification unless they are part of the intended evidence.
4. Sort keys.
5. Serialize compactly.
6. SHA-256 the UTF-8 bytes.
7. Store the 32-byte digest as `bytes32`.

## 6. Blockchain Contract State

```text
EvidenceRegistry
  ├─ nextId
  └─ evidence[id]
       ├─ evidenceHash
       ├─ sourceUrl
       ├─ searchProvider
       ├─ createdAt
       └─ submitter
```

## 7. Re-verification Semantics

`VERIFIED` means:

```text
hash(reconstructed_evidence) == on_chain_evidence_hash
```

It does not mean:

```text
person == identity claimed by source
```

or

```text
source content == truthful/factual
```

This distinction should be visible in the demo.

## 8. Sequence

```text
User -> CLI: run image
CLI -> Face Engine: detect + encode
Face Engine -> CLI: crop + embedding metadata
CLI -> Search Provider: upload/search image
Search Provider -> CLI: candidate URLs
CLI -> Web: validate candidate
Web -> CLI: final URL + metadata
CLI -> Evidence Builder: canonical evidence
Evidence Builder -> CLI: SHA-256
CLI -> Sepolia: recordEvidence(hash, url, provider)
Sepolia -> CLI: tx receipt + id
CLI -> Sepolia: getEvidence(id)
Sepolia -> CLI: stored hash
CLI -> Evidence Builder: recompute
CLI -> User: VERIFIED / MISMATCH
```

## 9. Failure Modes

```text
Face failure       -> stop
Search failure     -> retry/fallback provider
No social result   -> show candidates + fail clearly
Social fetch fail  -> try next candidate
Chain failure      -> preserve local evidence and retry
Hash mismatch      -> mark MISMATCH; never auto-change stored proof
```
