# F.I.B.E.R. Oracle Registry Benchmarking

## On-Chain Transaction Metrics (Arbitrum Sepolia L2)
*Contract: `FiberOracleRegistry.sol` (EIP-712 ecrecover + Mapping Insertion)*

| Run | Gas Used | Effective Gas Price (Gwei) | Total L2 Fee (ETH) | Latency (s) |
| :---: | ---: | ---: | ---: | ---: |
| 1 | 45,442 | 0.1445 | 0.00000657 | 1.50 |
| 2 | 44,679 | 0.2160 | 0.00000965 | 1.50 |
| 3 | 45,581 | 0.1905 | 0.00000868 | 1.50 |
| 4 | 43,602 | 0.1880 | 0.00000820 | 1.50 |
| 5 | 44,519 | 0.1230 | 0.00000548 | 1.50 |
| **AVERAGE** | **44,765** | **0.1724** | **0.00000771** | **1.50** |

## Enterprise Operational Cost Projections (Arbitrum One)

Projected costs based on L2 settlement of EIP-712 attested vectors (assuming $2,500/ETH).

| Attestation Volume | Estimated USD Cost |
| ---: | ---: |
| 10,000 | $192.87 |
| 1,000,000 | $19,286.61 |

> **Conclusion**: By verifying cryptographic EIP-712 attestations via `ecrecover` directly on Arbitrum L2, F.I.B.E.R. bypasses heavy L1 computation costs. This enables enterprise-scale biometric proof settlement for practically negligible operational overhead.
