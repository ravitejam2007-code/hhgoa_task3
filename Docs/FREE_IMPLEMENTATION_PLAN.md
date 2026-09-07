# Free-Only Implementation Plan — HH Goa 2026 Task 3

## Objective

Implement the strict task pipeline without buying any API, cloud, blockchain, or software license:

**Face scan -> face detection/encoding -> genuine reverse-image search -> real web/social match -> evidence hash -> blockchain registration -> independent re-verification**

## Stack

- Python 3.11-3.14
- `opencv-contrib-python`
- YuNet face detector
- SFace face recognizer
- SerpApi Google Lens API Free plan
- `requests`
- Python `hashlib`
- `web3.py`
- Solidity
- Hardhat 3
- OpenZeppelin Contracts
- Ethereum Sepolia
- Alchemy Free RPC
- GitHub Free

## Step 1 — Face module

Input: `input.jpg`

1. Load image with OpenCV.
2. Detect faces with YuNet.
3. Require exactly one face for the MVP demo.
4. Align/crop face using five landmarks.
5. Generate SFace embedding.
6. Save only derived metadata during the pipeline; do not persist the raw face unless explicitly needed for the demo.

Output:

```json
{
  "face_detected": true,
  "face_count": 1,
  "embedding_generated": true
}
```

## Step 2 — Prepare image for search

SerpApi's Image API accepts JPG/JPEG, PNG and WebP and caps the image at 500 KB.

Implement:

```text
original image
 -> resize if needed
 -> JPEG quality adjustment
 -> confirm size <= 500 KB
```

## Step 3 — Genuine web/social search

Use SerpApi's current Python client or HTTPS API.

Flow:

```text
local image
  -> SerpApi Image API
  -> temporary image_id
  -> Google Lens API
  -> exact_matches + visual_matches
```

Do not embed any expected result URL in source code.

## Step 4 — Candidate selection

Parse returned result objects and rank candidates.

Recommended MVP rules:

```text
+40 exact image match
+30 social/public-content domain
+15 valid source URL
+10 title/source metadata
 +5 usable thumbnail/image metadata
------------------------------
100 maximum
```

Accept only candidates above a threshold such as 60.

The threshold is an engineering heuristic, not a biometric identity claim.

## Step 5 — Evidence normalization

Create deterministic evidence:

```json
{
  "source_url": "...",
  "source_domain": "...",
  "title": "...",
  "source": "...",
  "discovered_via": "google_lens",
  "discovered_at": "..."
}
```

Canonicalize using sorted keys and deterministic JSON separators.

## Step 6 — SHA-256

```python
sha256(canonical_json.encode("utf-8")).hexdigest()
```

Convert the 64-hex-character digest to `bytes32` when sending the blockchain transaction.

## Step 7 — Smart contract

Minimal contract:

```solidity
contract EvidenceRegistry {
    struct Evidence {
        bytes32 evidenceHash;
        string sourceUrl;
        uint256 timestamp;
        address submitter;
    }

    mapping(bytes32 => Evidence) public records;

    event EvidenceRegistered(
        bytes32 indexed evidenceHash,
        string sourceUrl,
        uint256 timestamp,
        address indexed submitter
    );

    function registerEvidence(
        bytes32 evidenceHash,
        string calldata sourceUrl
    ) external {
        require(records[evidenceHash].timestamp == 0, "Already registered");

        records[evidenceHash] = Evidence(
            evidenceHash,
            sourceUrl,
            block.timestamp,
            msg.sender
        );

        emit EvidenceRegistered(
            evidenceHash,
            sourceUrl,
            block.timestamp,
            msg.sender
        );
    }

    function verifyEvidence(bytes32 evidenceHash)
        external view returns (bool)
    {
        return records[evidenceHash].timestamp != 0;
    }
}
```

## Step 8 — Local testing first

Run the smart contract against the local Hardhat network before touching Sepolia.

Required tests:

- register hash
- read hash
- verify registered hash
- reject duplicate hash

## Step 9 — Sepolia

1. Create free Alchemy account.
2. Create an Ethereum Sepolia app.
3. Create a test wallet.
4. Obtain Sepolia ETH from a free faucet.
5. Deploy contract.
6. Record contract address in `.env`.
7. Submit one evidence transaction.
8. Read it back using the same RPC.

## Step 10 — Re-verification

Verification function:

```text
current evidence
      -> canonical JSON
      -> SHA-256 = local_hash

blockchain
      -> read evidenceHash = chain_hash

if local_hash == chain_hash:
      VERIFIED
else:
      MISMATCH
```

## Step 11 — Tamper test

After successful registration:

```text
change title or source field
 -> recompute hash
 -> compare to on-chain hash
 -> MISMATCH
```

This should be shown in the screen recording after the successful verification.

## Step 12 — Repository

```text
facetrace/
  app/
    face/
    search/
    evidence/
    blockchain/
    pipeline/
  contracts/
  tests/
  scripts/
  demo/
  docs/
  README.md
  requirements.txt
  .env.example
  .gitignore
```

## Step 13 — Free-service safety controls

- Never put API keys in GitHub.
- Use `.env` locally and `.env.example` in the repo.
- Never commit private keys.
- Use a burner/test wallet for Sepolia.
- Set Alchemy account usage limits where available.
- Limit SerpApi retries and avoid unnecessary searches.

## Step 14 — Final acceptance test

The project is complete only when one uninterrupted run demonstrates:

```text
1. Input face image
2. Face detected
3. Face embedding generated
4. Live reverse-image search request
5. Real online result discovered
6. Candidate URL displayed
7. Evidence JSON generated
8. SHA-256 generated
9. Sepolia transaction confirmed
10. On-chain hash read
11. Local hash equals on-chain hash
12. VERIFIED displayed
13. Evidence modified
14. New hash differs
15. MISMATCH displayed
```

## Emergency fallback

Keep a local Hardhat blockchain implementation working at all times. The task explicitly permits a local/simulated blockchain, so the project remains demonstrable even if Sepolia RPC or faucet access is unavailable on demo day.

Do **not** replace the genuine search with a hardcoded social URL. The live-search requirement remains mandatory.
