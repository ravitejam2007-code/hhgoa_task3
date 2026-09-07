# Research & Technology Decisions

**Research date:** 2026-09-07

## 1. Source Brief

The task requires:

- face detection/encoding
- genuine web/social reverse search
- a real matching social-media post
- blockchain upload/verification
- no website requirement
- GitHub repo + README
- screen recording

The pipeline and submission requirements are explicitly stated in the supplied task PDF. fileciteturn0file0L3-L24

## 2. Face Recognition Research

NIST maintains distinct FRTE tracks for 1:1 verification and 1:N identification. The 1:N track is directly relevant to identification-style systems. citeturn819969search1turn819969search7

InsightFace is a local face-analysis project supporting detection, recognition, and alignment and has an actively maintained ecosystem. Its published repository also notes licensing distinctions between the software and some model packages, so the exact model package/license must be recorded in the repository before any non-hackathon deployment. citeturn486093search1

DeepFace is a practical alternative because it wraps multiple face-recognition models and exposes verification, representation, and database/search functions. citeturn486093search0

**Decision:** use InsightFace/ONNX for the primary implementation; keep DeepFace as fallback.

## 3. Reverse Image Search Research

### Google Lens via SerpApi

SerpApi's current Google Lens documentation supports image upload, `exact_matches`, `visual_matches`, structured JSON, and image IDs for uploaded images. citeturn127503search0turn127503search9

Its current public pricing page lists a free tier of 250 searches/month and paid plans above that. citeturn127503search1

**Decision:** primary search provider for the MVP because it provides an actual programmatic reverse-image search path with current upload support.

### TinEye

TinEye provides a REST API for programmatic reverse-image search, supports direct image upload, and currently advertises an index in the tens of billions of images. Real API use is paid; its sandbox does not return real matches. citeturn150875search0turn150875search6

**Decision:** backup provider when account access/budget is available.

### Google Custom Search JSON API

The current Google documentation says the Custom Search JSON API is closed to new customers, with transition guidance for existing customers. citeturn142345search0

**Decision:** do not build the new MVP around it.

## 4. Blockchain Research

OpenZeppelin documents deployment workflows for Ethereum smart contracts and explicitly discusses local chains and testnets such as Sepolia. citeturn819969search6

OpenZeppelin Contracts provides reusable Solidity components and role/access control patterns. citeturn819969search4turn819969search5

**Decision:** Ethereum Sepolia + Solidity + Hardhat + minimal custom evidence registry.

## 5. Content Addressing / IPFS

IPFS uses content identifiers derived from cryptographic hashes, so changed content results in a different content identifier. However, a CID contains codec/multiformat information and is not necessarily identical to a raw file hash. citeturn819969search0

**Decision:** IPFS optional. The MVP only needs an on-chain fingerprint, so adding IPFS is not required.

## 6. Privacy / India

India's Digital Personal Data Protection Act, 2023 establishes a framework for lawful processing of digital personal data, while MeitY published the Digital Personal Data Protection Rules, 2025 and an enforcement timeline. citeturn467868search0turn467868search2

**Engineering implication:** use consented test images, minimize retention, avoid public biometric databases, and do not put face embeddings/raw images on-chain.

## 7. Important Technical Limitation

A reverse-image match is not equivalent to face identity proof. A system may identify that the same or similar image exists online without proving that the person in the image is the claimed individual. The demo should therefore say:

> **Visual match discovered; identity not independently proven.**

NIST's evaluation work also demonstrates that face-recognition algorithms vary materially in performance, including across demographic groups. citeturn819969search9

## 8. Research Conclusion

The MVP should optimize for evaluator-verifiable evidence rather than feature count:

```text
Local face processing
        +
Real reverse-image search
        +
Social URL validation
        +
Deterministic evidence hash
        +
Public testnet anchor
        +
Independent re-verification
```

That is the clearest implementation of the supplied brief with the fewest moving parts.
