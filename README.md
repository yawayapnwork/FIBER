# F.I.B.E.R. (Facial Identification & Blockchain Enforcement Runtime)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Network: Arbitrum Sepolia](https://img.shields.io/badge/Network-Arbitrum%20Sepolia%20(421614)-blue)](https://sepolia.arbiscan.io)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Vision: Pure PIL + MTCNN](https://img.shields.io/badge/Vision-PIL%20%2B%20PyTorch%20(No%20OpenCV)-orange)](https://github.com/timesler/facenet-pytorch)

> **Decentralized Biometric Identity Protection & On-Chain Enforcement Attestation**

F.I.B.E.R. is an end-to-end Web3 & ML runtime designed to detect facial features, discover unauthorized visual web & social footprints, generate deterministic RFC 8785 canonical evidence digests, and anchor tamper-evident attestations on **Arbitrum Sepolia EVM L2**.

---

## 🏛️ System Architecture

```
┌─────────────────┐     ┌───────────────────────┐     ┌────────────────────────┐
│  Input Image    │ ──> │   src/vision.py       │ ──> │   src/search.py        │
│  (Target Face)  │     │   Pure PIL + MTCNN    │     │   Copyseeker Reverse   │
└─────────────────┘     │   (Zero OpenCV)       │     │   Visual Index         │
                        └───────────────────────┘     └────────────────────────┘
                                                                   │
                                                                   ▼
┌─────────────────┐     ┌───────────────────────┐     ┌────────────────────────┐
│ Arbiscan L2     │ <── │   src/blockchain.py   │ <── │   src/crypto.py        │
│ Explorer Receipt│     │   Web3.py Client      │     │   RFC 8785 Canonical   │
└─────────────────┘     │   Arbitrum Sepolia L2 │     │   SHA-256 Digest       │
                        └───────────────────────┘     └────────────────────────┘
                                   │
                                   ▼
                        ┌───────────────────────┐
                        │ FiberRegistry.sol     │
                        │ EVM Smart Contract    │
                        └───────────────────────┘
```

---

## ✅ Submission Checklist & Verification

| Requirement | Implementation Status | Component / Verification |
| :--- | :---: | :--- |
| **Face Identification** | **Passed** | PyTorch `facenet-pytorch` (MTCNN) + Pillow (`PIL`). Zero OpenCV (`cv2`) or `libGL` dependencies. |
| **Dynamic Reverse Search** | **Passed** | RapidAPI Copyseeker endpoint prioritizing X/Twitter, LinkedIn, Reddit, and Instagram footprints. Zero Google APIs. |
| **Canonical Fingerprinting** | **Passed** | RFC 8785 canonical JSON formatting and SHA-256 state hashing. |
| **Blockchain Settlement** | **Passed** | Arbitrum Sepolia EVM L2 settlement via `web3.py` with `FiberRegistry.sol`. |
| **Testing Suite** | **Passed** | 17/17 passing unit & integration tests (`pytest tests/ -v`). |
| **Demo Rehearsal** | **Passed** | Automated dry-run script (`scripts/demo_dryrun.py`) with browser link opening. |

---

## 🚀 Key Features & Constraints

1. **Pure Python Vision**: Zero OpenCV (`cv2`) or `libGL` dependencies. Powered by Pillow (`PIL`) and `facenet-pytorch` (`MTCNN`).
2. **Zero Google APIs**: Reverse visual footprint discovery via RapidAPI Copyseeker with social domain prioritization (X/Twitter, LinkedIn, Reddit, Instagram).
3. **Deterministic Hashing**: RFC 8785 canonical JSON formatting and SHA-256 state digest creation.
4. **Arbitrum Sepolia L2**: Low-cost, gas-optimized on-chain enforcement attestation (`FiberRegistry.sol`).

---

## ⚙️ Prerequisites & Installation

### 1. Requirements
- Python 3.10 or higher
- Git

### 2. Clone Repository & Install Dependencies
```bash
git clone https://github.com/yawayapnwork/FIBER.git
cd FIBER
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Copy `.env.example` to `.env` and fill in your RPC, private key, and RapidAPI credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Arbitrum Sepolia RPC URL
ARBITRUM_SEPOLIA_RPC=https://sepolia-rollup.arbitrum.io/rpc

# Deployer / Registrar Wallet Private Key
PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

# Deployed Contract Address
CONTRACT_ADDRESS=0xYOUR_CONTRACT_ADDRESS_HERE

# RapidAPI Key for Copyseeker Reverse Visual Search
RAPIDAPI_KEY=YOUR_RAPIDAPI_KEY_HERE
```

### 4. Arbitrum Sepolia Testnet Faucet
To execute on-chain transactions, obtain testnet ETH:
- [Alchemy Arbitrum Sepolia Faucet](https://www.alchemy.com/faucets/arbitrum-sepolia)
- [QuickNode Arbitrum Sepolia Faucet](https://faucet.quicknode.com/arbitrum/sepolia)

---

## 💻 CLI Usage Guide

### Mode 1: Full 5-Step Enforcement Scan Pipeline (`--scan`)
Runs face crop extraction -> reverse web search -> canonical hashing -> Arbitrum Sepolia anchoring -> immediate validation:
```bash
python main.py --scan path/to/target_image.jpg
```

### Mode 2: Direct On-Chain Verification (`--verify`)
Inspects the Arbitrum Sepolia contract to verify an existing evidence hash:
```bash
python main.py --verify 0x4f8a9c2e1b3d...
```

### Demo Dry-Run Rehearsal
Run the automated presentation runner script:
```bash
python scripts/demo_dryrun.py --mock-search
```

### Smart Contract Deployment
Deploy `FiberRegistry.sol` to Arbitrum Sepolia using `scripts/deploy.py`:
```bash
python scripts/deploy.py
```

---

## 🔗 Deployed Smart Contract

- **Target Network**: Arbitrum Sepolia Testnet (Chain ID `421614`)
- **Contract Source**: [`contracts/FiberRegistry.sol`](file:///c:/Dev/FIBER/contracts/FiberRegistry.sol)
- **Arbiscan Explorer**: [https://sepolia.arbiscan.io](https://sepolia.arbiscan.io)

---

## ⚠️ Known Limitations & Edge Cases

1. **Auth-Walled Social Accounts**: Private profiles or login-restricted media on Instagram/Facebook may not yield public match URLs via web indexers.
2. **Indexing Latency**: Images published within minutes may take time to index across reverse search endpoints.
3. **API Rate Limits**: RapidAPI Copyseeker endpoints enforce rate limits; handling is provided via fallback mechanisms.
4. **Extreme Occlusion**: Facial angles exceeding 60 degrees or heavy facial masks may fail MTCNN minimum probability threshold (`0.85`).
