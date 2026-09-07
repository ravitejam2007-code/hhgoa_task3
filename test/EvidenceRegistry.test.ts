import { expect } from "chai";
import { ethers } from "hardhat";

describe("EvidenceRegistry Contract", function () {
  let contract: any;
  let owner: any;
  let otherAccount: any;

  const sampleHash = ethers.keccak256(ethers.toUtf8Bytes("test-evidence-canonical-json"));
  const differentHash = ethers.keccak256(ethers.toUtf8Bytes("different-evidence-data"));
  const sampleUrl = "https://instagram.com/p/test123";
  const sampleProvider = "serpapi_google_lens";

  beforeEach(async function () {
    [owner, otherAccount] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("EvidenceRegistry");
    contract = await Factory.deploy();
    await contract.waitForDeployment();
  });

  it("should record evidence and emit EvidenceRecorded event", async function () {
    await expect(contract.recordEvidence(sampleHash, sampleUrl, sampleProvider))
      .to.emit(contract, "EvidenceRecorded")
      .withArgs(1, sampleHash, sampleUrl, sampleProvider, owner.address);

    const total = await contract.totalEvidence();
    expect(total).to.equal(1n);
  });

  it("should reject zero evidence hash", async function () {
    await expect(
      contract.recordEvidence(ethers.ZeroHash, sampleUrl, sampleProvider)
    ).to.be.revertedWith("Evidence hash cannot be zero");
  });

  it("should retrieve recorded evidence by ID", async function () {
    await contract.recordEvidence(sampleHash, sampleUrl, sampleProvider);

    const record = await contract.getEvidence(1);
    expect(record.evidenceHash).to.equal(sampleHash);
    expect(record.sourceUrl).to.equal(sampleUrl);
    expect(record.searchProvider).to.equal(sampleProvider);
    expect(record.submitter).to.equal(owner.address);
    expect(record.createdAt).to.be.gt(0n);
  });

  it("should revert getEvidence for non-existent ID", async function () {
    await expect(contract.getEvidence(999)).to.be.revertedWith(
      "Evidence record not found"
    );
  });

  it("should return true for matching evidence hash and false for mismatched hash", async function () {
    await contract.recordEvidence(sampleHash, sampleUrl, sampleProvider);

    const isMatch = await contract.verifyEvidence(1, sampleHash);
    expect(isMatch).to.be.true;

    const isDifferent = await contract.verifyEvidence(1, differentHash);
    expect(isDifferent).to.be.false;

    const nonExistent = await contract.verifyEvidence(999, sampleHash);
    expect(nonExistent).to.be.false;
  });
});
