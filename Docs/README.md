# HH Goa 2026 — Task 3: Face Identification & Blockchain Verification

This repository implements the required pipeline:

```text
Face scan
  → face detection/encoding
  → live reverse-image search
  → matching social-media result
  → evidence fingerprint
  → blockchain record
  → re-verification
```

## Documents

- [PRD](PRD.md)
- [TRD](TRD.md)
- [Architecture](ARCHITECTURE.md)
- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Phases](PHASES.md)
- [Test Plan](TEST_PLAN.md)
- [Research](RESEARCH.md)

## Recommended stack

- Python 3.11
- InsightFace + ONNX Runtime
- SerpApi Google Lens
- Solidity
- Hardhat
- Ethereum Sepolia
- web3.py

## Run

```bash
python -m app.cli run --image ./samples/known_good.jpg
```

The final run should show the live search, discovered social result, evidence hash, blockchain transaction, and `VERIFIED` status.

## Blockchain

Network: Ethereum Sepolia  
Contract: `<fill after deployment>`

## Limitations

- Search results depend on the external provider's current index and availability.
- A visual match is not independent proof of a person's identity.
- Public social pages can disappear or change.
- Sepolia is a testnet, not a production evidentiary system.
- Any real deployment involving biometric/personal data requires appropriate privacy, legal, security, and platform-policy review.

## Submission

The source brief requires the GitHub repository, a plain end-to-end screen recording, and the submission form; it says no resubmissions will be allowed. fileciteturn0file0L25-L36

Submission form from brief:

`https://forms.gle/oZbQGuwiNeHVcHWo8`
