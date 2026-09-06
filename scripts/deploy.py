"""
F.I.B.E.R. Smart Contract Deployment Script
Deploys FiberRegistry.sol to Arbitrum Sepolia EVM L2 testnet using web3.py.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# Load environment variables from .env
load_dotenv()

# Solcx compiler integration
try:
    import solcx
    SOLCX_AVAILABLE = True
except ImportError:
    SOLCX_AVAILABLE = False

CONTRACT_PATH = Path(__file__).parent.parent / "contracts" / "FiberRegistry.sol"
DEFAULT_RPC = "https://sepolia-rollup.arbitrum.io/rpc"

def compile_contract():
    """Compile FiberRegistry.sol using py-solc-x or return compiled bytecode/abi."""
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found at {CONTRACT_PATH}")

    if SOLCX_AVAILABLE:
        print("[+] Compiling FiberRegistry.sol with py-solc-x...")
        try:
            installed_versions = solcx.get_installed_solc_versions()
            if not any(v.major == 0 and v.minor == 8 and v.patch >= 20 for v in installed_versions):
                print("[*] Installing solc 0.8.20...")
                solcx.install_solc("0.8.20")
            solcx.set_solc_version("0.8.20")
            
            compiled = solcx.compile_files(
                [str(CONTRACT_PATH)],
                output_values=["abi", "bin"],
                solc_version="0.8.20"
            )
            contract_id = f"{CONTRACT_PATH!s}:FiberRegistry"
            abi = compiled[contract_id]["abi"]
            bytecode = compiled[contract_id]["bin"]
            return abi, bytecode
        except Exception as e:
            print(f"[!] py-solc-x compilation warning: {e}. Falling back to standard artifact...")

    raise RuntimeError(
        "py-solc-x is required to compile contract dynamically. "
        "Please run `pip install py-solc-x` or provide pre-compiled ABI/Bytecode."
    )

def deploy():
    rpc_url = os.getenv("ARBITRUM_SEPOLIA_RPC", DEFAULT_RPC)
    private_key = os.getenv("PRIVATE_KEY")

    if not private_key or private_key == "0x0000000000000000000000000000000000000000000000000000000000000000":
        print("[!] ERROR: Valid PRIVATE_KEY must be set in .env before deployment.")
        sys.exit(1)

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"[!] ERROR: Failed to connect to Arbitrum Sepolia RPC at {rpc_url}")
        sys.exit(1)

    account = Account.from_key(private_key)
    chain_id = w3.eth.chain_id
    balance_wei = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance_wei, 'ether')

    print("==================================================")
    print("  F.I.B.E.R. Arbitrum Sepolia Deployment")
    print("==================================================")
    print(f"  RPC Endpoint:     {rpc_url}")
    print(f"  Chain ID:         {chain_id}")
    print(f"  Deployer Address: {account.address}")
    print(f"  Deployer Balance: {balance_eth:.6f} ETH")
    print("==================================================")

    if balance_wei == 0:
        print("[!] WARNING: Deployer balance is 0 ETH. Please request Arbitrum Sepolia testnet ETH from a faucet.")

    # Compile contract
    abi, bytecode = compile_contract()

    # Create contract instance
    FiberRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Build deployment transaction
    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    tx = FiberRegistry.constructor().build_transaction({
        "chainId": chain_id,
        "from": account.address,
        "nonce": nonce,
        "gasPrice": gas_price,
    })

    # Estimate gas if possible
    try:
        estimated_gas = w3.eth.estimate_gas(tx)
        tx["gas"] = int(estimated_gas * 1.2)
    except Exception:
        tx["gas"] = 1500000

    print("[*] Signing transaction with private key...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)

    print("[*] Broadcasting deployment transaction to Arbitrum Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"[+] Transaction submitted! Tx Hash: {tx_hash.hex()}")
    print("[*] Waiting for block confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    print("\n==================================================")
    print("  DEPLOYMENT SUCCESSFUL!")
    print("==================================================")
    print(f"  Contract Address: {receipt.contractAddress}")
    print(f"  Transaction Hash: {receipt.transactionHash.hex()}")
    print(f"  Block Number:     {receipt.blockNumber}")
    print(f"  Gas Used:         {receipt.gasUsed}")
    print("==================================================")
    print("\n[!] Update your .env file with:")
    print(f"CONTRACT_ADDRESS={receipt.contractAddress}")

if __name__ == "__main__":
    deploy()
