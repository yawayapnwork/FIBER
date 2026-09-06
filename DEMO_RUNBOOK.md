# F.I.B.E.R. Demo Video Runbook & Screen Recording Script

> **Target Duration:** < 2 Minutes (120 Seconds)  
> **Target Audience:** Hackathon Judges, Web3 Engineers & Security Researchers  

---

## 📋 Pre-Demo Checklist

1. Open terminal window zoomed to **125% font size** for clear visibility.
2. Confirm `.env` file contains a funded `PRIVATE_KEY` and valid `CONTRACT_ADDRESS` on Arbitrum Sepolia.
3. Have a sample target face image ready: `sample_target.jpg`.
4. Open Chrome browser to [Arbiscan Sepolia Explorer](https://sepolia.arbiscan.io).

---

## 🎬 Screen Recording Script (120 Seconds)

### Act I: Project Pitch & Architecture (0:00 - 0:25)
- **Visual:** Display terminal showing directory layout or README architecture diagram.
- **Voiceover Script:**
  > *"Welcome! This is Project F.I.B.E.R. — Facial Identification & Blockchain Enforcement Runtime. F.I.B.E.R. solves biometric identity theft by detecting facial crops using pure PyTorch MTCNN without OpenCV, finding unauthorized social footprints, generating RFC 8785 canonical evidence hashes, and anchoring tamper-evident attestations on Arbitrum Sepolia EVM L2."*

---

### Act II: Executing 5-Step Enforcement Scan (0:25 - 1:00)
- **Visual:** Type and execute the CLI scan command in terminal.
- **Terminal Command:**
  ```bash
  python main.py --scan sample_target.jpg
  ```
- **Voiceover Script:**
  > *"Let's execute the pipeline on our sample image `sample_target.jpg`.*  
  > *In Step 1, MTCNN detects and crops the primary face with Pillow padding.*  
  > *In Step 2, Copyseeker searches reverse visual indexers, prioritizing social domains like Twitter, LinkedIn, and Reddit.*  
  > *In Step 3, we serialize the manifest into an RFC 8785 canonical SHA-256 state digest.*  
  > *In Step 4, web3.py signs and broadcasts the transaction directly to our `FiberRegistry` smart contract on Arbitrum Sepolia.*  
  > *And in Step 5, we verify persistence on-chain!"*

---

### Act III: On-Chain Hash Verification (1:00 - 1:25)
- **Visual:** Copy the generated evidence hash from terminal output and execute the `--verify` command.
- **Terminal Command:**
  ```bash
  python main.py --verify 0x4f8a9c2e1b3d...
  ```
- **Voiceover Script:**
  > *"To prove tamper-evident verification, we can run `main.py --verify` with any anchored hash. The CLI queries the contract's `verifyEvidence` view function on Arbitrum Sepolia and returns the exact registrar address, source match URL, and block timestamp."*

---

### Act IV: Arbiscan Sepolia Explorer Verification (1:25 - 2:00)
- **Visual:** Switch to browser window showing Arbiscan Sepolia.
- **Action Steps for Judges:**
  1. Click on the transaction hash link output in the terminal (`https://sepolia.arbiscan.io/tx/0x...`).
  2. In Arbiscan, highlight **Status: Success** and **Block Number**.
  3. Scroll down to the **Logs** tab.
  4. Expand event **`EvidenceAnchored(bytes32 evidenceHash, string sourceUrl, uint256 timestamp, address registrar)`**.
  5. Show judges the `evidenceHash` parameter stored permanently on-chain.
- **Voiceover Script:**
  > *"Finally, let's open Arbiscan Sepolia. We see our transaction confirmed in block 14920381. Inspecting the event logs shows `EvidenceAnchored` with our exact evidence hash, source URL, and registrar address. F.I.B.E.R. brings decentralized biometric enforcement to EVM Layer 2. Thank you!"*

---

## 🛠️ Summary of Demo Commands

```bash
# 1. Environment Verification
python scripts/deploy.py --help

# 2. Run 5-Step Pipeline
python main.py --scan sample_target.jpg

# 3. Verify Anchored Hash
python main.py --verify <HASH_FROM_STEP_2>
```
