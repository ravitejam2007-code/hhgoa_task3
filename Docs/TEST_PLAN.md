# Test Plan — Face Identification & Blockchain Verification

## 1. Objective

Validate that the implementation satisfies each explicit task requirement and that the evidence verification logic fails safely.

## 2. Test Levels

### Unit tests

- URL normalization
- social-domain detection
- JSON canonicalization
- SHA-256 fingerprinting
- candidate ranking
- error mapping

### Integration tests

- face engine → normalized search image
- search provider → candidate model
- candidate → social validator
- evidence → hash
- hash → contract

### End-to-end test

Input face scan → live search → social result → blockchain write → blockchain read → verification.

## 3. Functional Test Cases

| ID | Test | Expected |
|---|---|---|
| FT-01 | Valid single-face image | Face detected |
| FT-02 | No-face image | `NO_FACE_FOUND` |
| FT-03 | Corrupt image | Validation error |
| FT-04 | Live reverse search | Provider request appears in logs |
| FT-05 | Dynamic result | Result URL not sourced from code constant |
| FT-06 | Social result | URL passes domain validation |
| FT-07 | No social result | `NO_SOCIAL_MATCH` |
| FT-08 | Evidence hash | Deterministic 32-byte digest |
| FT-09 | Blockchain write | Transaction mined |
| FT-10 | Blockchain read | Stored hash equals submitted hash |
| FT-11 | Reverification | `VERIFIED` |
| FT-12 | Tampered evidence | `MISMATCH` |
| FT-13 | Wrong contract ID | Clear chain error |
| FT-14 | Insufficient wallet balance | Clear funding error |
| FT-15 | Search timeout | Retry then explicit `SEARCH_ERROR` |

## 4. Security Tests

- Verify `.env` is in `.gitignore`.
- Search Git history for secrets before publishing.
- Confirm private key is not printed in logs.
- Confirm raw face embeddings are not sent to blockchain.
- Confirm on-chain string fields do not contain unnecessary personal data.

## 5. Re-verification Tamper Test

1. Record evidence.
2. Store hash on Sepolia.
3. Read record.
4. Change exactly one character in `title`.
5. Recompute hash.
6. Confirm mismatch.
7. Restore original evidence.
8. Confirm match again.

Expected:

```text
Original -> VERIFIED
Tampered -> MISMATCH
Original restored -> VERIFIED
```

## 6. Provider Research Tests

### SerpApi Google Lens

Test both:

- upload image → `exact_matches`
- upload image → `visual_matches`

The current API documentation explicitly supports image upload and those search types. citeturn127503search0

### TinEye fallback

If used, run a real API account search, not the sandbox, because TinEye states the sandbox does not return real image matches. citeturn150875search6

## 7. Performance Recording

Capture measured values for:

- face inference duration
- search latency
- social fetch latency
- blockchain transaction wait
- end-to-end duration

Do not publish unmeasured accuracy/latency percentages.

## 8. Demo Readiness Test

A run is demo-ready when the evaluator can visually see:

```text
[FACE SCAN]
    ↓
[SEARCH EXECUTED]
    ↓
[SOCIAL POST FOUND]
    ↓
[EVIDENCE HASH]
    ↓
[TX HASH]
    ↓
[ON-CHAIN RECORD]
    ↓
[VERIFIED]
```

This directly mirrors the required recording path in the source brief. fileciteturn0file0L30-L32
