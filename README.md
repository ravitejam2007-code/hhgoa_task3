# HH Goa 2026 — Task 3: Face Identification & Blockchain Verification

A CLI-based proof-of-concept pipeline that links facial recognition and live reverse-image search results to the Ethereum blockchain for tamper-evident provenance verification.

---

## 1. What It Does

This pipeline runs entirely from the command line:

```text
Input Face Image
      ↓
Face Detection + Face Encoding (YuNet + SFace)
      ↓
Reverse Image Search (SerpApi Google Lens)
      ↓
Find Genuine Web / Social Media Match
      ↓
Validate and Select Social Evidence (Domain, URL reachability, Match score)
      ↓
Canonicalize Evidence (Deterministic Schema & JSON)
      ↓
SHA-256 Evidence Fingerprint (32-byte digest)
      ↓
Write Fingerprint + Provenance to Blockchain (EvidenceRegistry.sol on Sepolia)
      ↓
Read Blockchain Record
      ↓
Recompute Fingerprint & Verify
      ↓
VERIFY / MISMATCH
```

---

## 2. Architecture

```text
+-------------------+
|  Input Image      | (JPG / PNG / WebP)
+---------+---------+
          |
          v
+-------------------+
|  Face Detection   | YuNet ONNX (face detection & bounding box)
|  & Embedding      | SFace ONNX (128-dimensional embedding vector)
+---------+---------+
          |
          v
+-------------------+
| Reverse Search    | SerpApi Google Lens API (no hardcoded URLs)
| Provider          | Fetches exact_matches and visual_matches
+---------+---------+
          |
          v
+-------------------+
| Candidate         | Filter: Instagram, Facebook, X, Twitter, TikTok, LinkedIn
| Validator         | Bounded HTTP reachability + deterministic scoring
+---------+---------+
          |
          v
+-------------------+
| Deterministic     | Sorted keys, normalized URL, compact JSON formatting,
| Canonicalization  | SHA-256 32-byte cryptographic digest
+---------+---------+
          |
          v
+-------------------+
| Blockchain Client | web3.py calls EvidenceRegistry.sol
| (Sepolia / Local) | Records hash + URL; returns evidenceId & tx receipt
+---------+---------+
          |
          v
+-------------------+
| Verification      | Recomputes local hash from runs/<run_id>/evidence.json
| Engine            | Compares against on-chain record: VERIFIED or MISMATCH
+-------------------+
```

---

## 3. Technology Stack

* **Face Recognition**: OpenCV (YuNet detection + SFace recognition), Pillow
* **Reverse Search**: SerpApi Google Lens, `requests`
* **Evidence & Canonicalization**: Python standard library (`hashlib`, `json`, `urllib.parse`)
* **Smart Contract**: Solidity (`^0.8.20`), Hardhat, OpenZeppelin
* **Blockchain Network**: Ethereum Sepolia (or local Hardhat node) via Alchemy RPC
* **Python Web3 Client**: `web3.py` (v7+)
* **Testing**: `pytest` (offline test suite), Hardhat test runner

---

## 4. Prerequisites & Requirements

* **Python**: 3.10+ (tested on Python 3.11 / 3.13)
* **Node.js**: v18+ and `npm`
* **SerpApi API Key**: Free tier account at [serpapi.com](https://serpapi.com)
* **Alchemy RPC Key**: Free Sepolia endpoint at [alchemy.com](https://alchemy.com)
* **Ethereum Testnet Wallet**: MetaMask or disposable private key with Sepolia ETH

---

## 5. Installation

### 5.1 Python Virtual Environment

```bash
# Clone or navigate to the repository
cd hhgoa_task3

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 5.2 Node.js & Smart Contract Dependencies

```bash
npm install
npm run compile
```

---

## 6. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
SERPAPI_KEY=your_serpapi_key_here
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
WALLET_PRIVATE_KEY=your_testnet_wallet_private_key
CONTRACT_ADDRESS=deployed_contract_address
```

> **Security Note**: Never commit `.env` or private keys to git. `.env` is ignored in `.gitignore`.

---

## 7. Smart Contract Deployment

### Deploy to Ethereum Sepolia:

```bash
npm run deploy:sepolia
```

Example output:
```text
Deploying EvidenceRegistry...
Deployer: 0x71C...b45
Contract: 0x93F...12C
Transaction: 0x4a2...8ef
```

Copy the deployed `Contract` address into your `.env` as `CONTRACT_ADDRESS`.

### Deploy Locally (for testing without Sepolia ETH):

```bash
# In terminal 1:
npm run node

# In terminal 2:
npm run deploy:local
```

Set `SEPOLIA_RPC_URL=http://127.0.0.1:8545`, set `WALLET_PRIVATE_KEY` to Account #0 private key, and set `CONTRACT_ADDRESS`.

---

## 8. CLI Usage

### 8.1 Phase 1 Face Detection & Embedding

```bash
python -m app.cli face --image samples/test.jpg
```

### 8.2 Full End-to-End Pipeline

```bash
python -m app.cli run --image samples/test.jpg
```

Example output:
```text
========================================
HH Goa 2026 — Task 3
Face Identification & Blockchain Verification
========================================

[1/8] Face detection.............. PASS
[2/8] Face encoding............... PASS
[3/8] Reverse image search........ PASS
[4/8] Candidate validation....... PASS
[5/8] Evidence canonicalization.. PASS
[6/8] SHA-256 fingerprint......... PASS
[7/8] Blockchain anchoring........ PASS
[8/8] Verification................ PASS

Face detected: YES
Search provider: SerpApi Google Lens
Match type: exact_match
Selected URL: https://www.instagram.com/p/example_match

Evidence SHA-256:
7c84495e8bc8614cb831e5f8cfb54cbf8a892b1a8dcf8cbe44ef694b4e3c3b01

Network: Sepolia
Contract:
0x93F...12C

Transaction:
0x4a2...8ef

Evidence ID:
1

Verification:
VERIFIED

Run directory:
runs/20260907T120000Z_a1b2
```

### 8.3 Verify Tamper-Evidence

Verify an existing run against the blockchain:

```bash
python -m app.cli verify --evidence-id 1 --run ./runs/<RUN_ID>
```

Expected output:
```text
Evidence ID: 1
Local hash:  7c84495e8bc8614cb831e5f8cfb54cbf8a892b1a8dcf8cbe44ef694b4e3c3b01
On-chain:    7c84495e8bc8614cb831e5f8cfb54cbf8a892b1a8dcf8cbe44ef694b4e3c3b01

Result: VERIFIED
```

#### Tamper Test (Simulating Mismatch):

1. Modify any value in `runs/<RUN_ID>/evidence.json` (e.g. change `"title"` or `"source_url"`).
2. Run verify again:
```bash
python -m app.cli verify --evidence-id 1 --run ./runs/<RUN_ID>
```

Output:
```text
Evidence ID: 1
Local hash:  f31b81628d3e...
On-chain:    7c84495e8bc8...

Result: MISMATCH
```

---

## 9. Testing

### 9.1 Offline Python Unit Tests

No API keys or internet connection required. Mocks external HTTP and APIs:

```bash
pytest -v
```

Includes:
* `tests/test_face_engine.py`: Face detection, alignment, embeddings, artifacts (22 tests)
* `tests/test_canonicalization.py`: Tests A, B, C, D verifying deterministic ordering, formatting, and change detection (5 tests)
* `tests/test_fingerprint.py`: SHA-256 byte digest, 64-character lowercase hex format, determinism (4 tests)
* `tests/test_social_validation.py`: Platform allowlist, syntax checks, scoring determinism, mock selection (4 tests)
* `tests/test_search_adapter.py`: SerpApi upload, Google Lens parsing, error handling, secret scrubbing (6 tests)

Total: **41 unit tests passing**.

### 9.2 Smart Contract Tests

```bash
npm run test
```

Runs Hardhat Chai tests verifying:
* `recordEvidence()` event emission and ID incrementation
* Rejection of zero-hash evidence
* `getEvidence()` retrieval and field integrity
* `verifyEvidence()` returning true for matching hashes and false for mismatched hashes

---

## 10. Run Directory Artifacts

Every execution creates `runs/<run_id>/` containing:

```text
runs/<run_id>/
├── input_metadata.json       # Input file stats and timestamp
├── face_result.json          # Face count, bbox, embedding model, dim, crop SHA-256
├── crop_<run_id>.jpg         # Aligned face crop
├── search_response.json      # Raw SerpApi Google Lens response (secrets scrubbed)
├── selected_evidence.json    # Selected winner candidate with score & status
├── evidence.json             # Canonical deterministic JSON evidence record
├── evidence_hash.txt         # Lowercase 64-character SHA-256 hexadecimal string
└── blockchain_receipt.json   # Chain ID, tx hash, contract address, block number, status
```

---

## 11. Known Limitations

1. **Reverse-image search depends on API availability**: Upstream changes in SerpApi or Google Lens may affect response timing or formatting.
2. **Search results may change**: Search engines crawl and index pages continuously; results for an image can vary over time.
3. **Social-media pages may become private or disappear**: URLs discovered during a run may later return 404 or require authentication.
4. **Visual matching is not definitive identity proof**: A reverse-image match confirms that visually similar or identical media exists on the web, not that the face in the image legally belongs to a specific person.
5. **Face recognition performance**: Face detection and recognition depend on illumination, pose, resolution, and occlusion.
6. **Sepolia is a test network**: Sepolia testnet transactions depend on network congestion and faucet ETH availability.
7. **SerpApi rate limits**: Free accounts are limited to 250 requests per month.
