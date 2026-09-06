# FiberRegistry.sol Contract Verification Guide

This guide details automated and manual steps to verify `contracts/FiberRegistry.sol` on [Arbiscan Sepolia Explorer](https://sepolia.arbiscan.io).

---

## 1. Automated Verification via CLI

Run the automated verification script:
```bash
python scripts/verify_contract.py --address <DEPLOYED_CONTRACT_ADDRESS>
```

Optional: Pass your Arbiscan API key via `--api-key` or set `ARBISCAN_API_KEY` in `.env`.

---

## 2. Manual Verification via Arbiscan Web UI

If the Arbiscan API is congested or rate-limited:

1. Open your contract's code tab on Arbiscan:
   `https://sepolia.arbiscan.io/address/<YOUR_CONTRACT_ADDRESS>#code`
2. Click **Verify and Publish**.
3. Select Compiler Settings:
   - **Compiler Type**: `Solidity (Single file)`
   - **Compiler Version**: `v0.8.20+commit.a1b79de6`
   - **Open Source License Type**: `MIT License (MIT)`
   - **Optimization**: `Yes` (Optimization Runs: `200`)
   - **EVM Version**: `shanghai`
4. Copy the entire contents of [`contracts/FiberRegistry.sol`](file:///c:/Dev/FIBER/contracts/FiberRegistry.sol) and paste it into the **Enter the Solidity Contract Code** box.
5. Click **Verify and Publish**.
