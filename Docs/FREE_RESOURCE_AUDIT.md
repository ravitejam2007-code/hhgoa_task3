# Free Resource Audit — HH Goa 2026 Task 3

**Goal:** Build the required Face -> genuine web/social search -> blockchain verification pipeline at **₹0 software/service spend** for the hackathon MVP.

> Cost definition: excludes the team's existing laptop, electricity, internet connection, and any optional paid upgrade. Paid tiers are not required for the recommended MVP.

## Final verdict

The project can be implemented with **₹0 direct spend** using free/open-source software plus free service tiers and Sepolia testnet ETH.

The highest-risk component is reverse-image/web search. The recommended primary service is **SerpApi's Google Lens API on its Free plan**. SerpApi currently lists a $0/month Free plan with 250 searches/month, and its Google Lens integration supports local image upload through a temporary image ID. The provider's current documentation shows the Lens API can return exact and visual matches.  

## Component audit

| Component | Candidate | Cost | Free status | Decision |
|---|---|---:|---|---|
| Face detection | OpenCV YuNet | ₹0 | Open source; model directory MIT | **Use** |
| Face embedding | OpenCV SFace | ₹0 | Apache 2.0 model directory | **Use** |
| Image processing | OpenCV | ₹0 | Apache 2.0; Python wheel repository MIT | **Use** |
| Reverse image search | SerpApi Google Lens | ₹0 for MVP | Free plan: 250 searches/month | **Use** |
| Local image upload for Lens | SerpApi Image API | Included in workflow | Temporary image_id; JPEG/PNG/WebP up to 500 KB | **Use** |
| Blockchain | Ethereum Sepolia | ₹0 | Testnet; test ETH from faucets | **Use** |
| RPC | Alchemy | ₹0 for MVP | Free plan: 30M compute units/month | **Use** |
| Test ETH | Alchemy Sepolia faucet | ₹0 | Free testnet ETH | **Use** |
| Smart contracts | Solidity + Hardhat | ₹0 | Hardhat is open source; local network included | **Use** |
| Contract helpers | OpenZeppelin Contracts | ₹0 | MIT | **Use** |
| Python blockchain client | web3.py | ₹0 | MIT | **Use** |
| Repository | GitHub Free | ₹0 | Unlimited public/private repositories | **Use** |
| Testing | pytest | ₹0 | MIT/open source | **Use** |
| Browser automation fallback | Playwright | ₹0 | Apache 2.0 | **Backup only** |

## Rejected or non-primary choices

### InsightFace
The InsightFace code is MIT, but its public pretrained models are explicitly licensed for non-commercial research use unless separately licensed. For a hackathon submission, use OpenCV YuNet + SFace instead to reduce licensing ambiguity.

### TinEye API
Not free for ongoing API use. Current API pricing starts at $200 for 5,000 searches. Do not make it a dependency.

### Google Custom Search JSON API
Do not use. Google currently says this API is closed to new customers and will be discontinued on January 1, 2027. Existing customers have 100 free queries/day until then, but this does not help a new project.

### Direct Google Lens browser automation
Google offers Lens image upload as a free user-facing feature, but Google's current Terms prohibit automated access where it violates machine-readable instructions. Do not make Playwright-based Google UI scraping the primary solution. Keep it as a manual/demo fallback only if needed.

### Google Cloud Vision
Face detection itself has a free monthly allowance of 1,000 units, but it is unnecessary because OpenCV can do the whole face stage locally at ₹0. Avoid introducing cloud billing/payment setup.

### IPFS
Not required by the task. Storing the evidence hash on-chain is enough for tamper-evident verification. Adding a hosted IPFS pinning provider can introduce another quota/account dependency.

## Recommended zero-cost architecture

```text
Local image
   |
   v
OpenCV YuNet face detection
   |
   v
OpenCV SFace face embedding
   |
   v
SerpApi Google Lens (Free: 250 searches/month)
   |
   v
Exact/visual matches -> social/web candidate filtering
   |
   v
Canonical evidence JSON
   |
   v
SHA-256 fingerprint
   |
   v
Ethereum Sepolia via free Alchemy RPC
   |
   v
EvidenceRegistry.sol
   |
   v
Read on-chain hash
   |
   v
Recompute SHA-256 -> VERIFIED / MISMATCH
```

## Cost ceiling

For the hackathon MVP:

- Software licenses: **₹0**
- API search: **₹0** within 250 SerpApi searches/month
- Blockchain gas: **₹0** using Sepolia test ETH
- RPC: **₹0** within Alchemy Free quota
- Smart-contract framework: **₹0**
- GitHub repository: **₹0**

Therefore expected direct spend is **₹0**.

## Important operational limits

1. SerpApi is a free tier, not an unlimited free service. Keep demo/search retries low.
2. SerpApi's image upload limit is 500 KB; compress/resize the input before upload.
3. Search results are not guaranteed to contain a social-media result for every image. The demo must use an image with a known public online appearance, while still discovering the URL dynamically at runtime.
4. Never hardcode the result URL.
5. Do not store raw face images on-chain.
6. Face matching should be described as evidence/candidate matching, not as legal proof of identity.

## Sources checked

- SerpApi pricing and Google Lens documentation
- Google Search/Lens help and Google Terms
- OpenCV Zoo YuNet/SFace repositories and licenses
- InsightFace repository licensing
- TinEye API pricing
- Google Custom Search API documentation
- Ethereum networks documentation
- Alchemy pricing and Sepolia faucet documentation
- OpenZeppelin Contracts licensing
- web3.py package metadata
- GitHub pricing
- Playwright licensing
