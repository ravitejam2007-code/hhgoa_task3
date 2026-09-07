import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying EvidenceRegistry...");
  console.log(`Deployer: ${deployer.address}`);

  const factory = await ethers.getContractFactory("EvidenceRegistry");
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  const tx = contract.deploymentTransaction();
  const txHash = tx ? tx.hash : "N/A";

  console.log(`Contract: ${contractAddress}`);
  console.log(`Transaction: ${txHash}`);
}

main().catch((error) => {
  console.error("Deployment failed:", error);
  process.exitCode = 1;
});
