"""
F.I.B.E.R. Smart Contract Source Code Verification Script
Automates verification of FiberRegistry.sol on Arbiscan Sepolia Explorer API.
"""

import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

# Rich UI Integration
from rich.console import Console
from rich.panel import Panel

# Load environment variables
load_dotenv()

console = Console()

CONTRACT_PATH = Path(__file__).parent.parent / "contracts" / "FiberRegistry.sol"
ARBISCAN_API_URL = "https://api-sepolia.arbiscan.io/api"
DEFAULT_EXPLORER_BASE = "https://sepolia.arbiscan.io"

COMPILER_VERSION = "v0.8.20+commit.a1b79de6"

def print_manual_verification_guide(contract_address: str):
    """Output manual verification steps in case the Arbiscan API is congested."""
    guide = (
        "[bold yellow]Manual Verification Fallback Steps (Arbiscan Web UI):[/bold yellow]\n\n"
        f"1. Open Arbiscan: [blue link={DEFAULT_EXPLORER_BASE}/address/{contract_address}#code]"
        f"{DEFAULT_EXPLORER_BASE}/address/{contract_address}#code[/blue link]\n"
        "2. Click [bold cyan]'Verify and Publish'[/bold cyan].\n"
        "3. Select Settings:\n"
        "   - Compiler Type:     [bold white]Solidity (Single file)[/bold white]\n"
        f"   - Compiler Version:  [bold white]{COMPILER_VERSION}[/bold white]\n"
        "   - License Type:      [bold white]MIT License (MIT)[/bold white]\n"
        "   - Optimization:      [bold white]Yes (Runs: 200)[/bold white]\n"
        f"4. Paste contents of [bold cyan]contracts/FiberRegistry.sol[/bold cyan] and click [bold green]'Verify and Publish'[/bold green]."
    )
    console.print(Panel(guide, border_style="yellow", title="Arbiscan Manual Verification Guide"))

def verify_contract_on_arbiscan(contract_address: str, api_key: str):
    """Submit contract source code and compiler parameters to Arbiscan API for verification."""
    if not CONTRACT_PATH.exists():
        console.print(f"[bold red][X] Error:[/bold red] Contract file not found at {CONTRACT_PATH}")
        sys.exit(1)

    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()

    console.print(Panel(
        f"[bold cyan]F.I.B.E.R. Contract Verification Runner[/bold cyan]\n"
        f"[dim]Contract Address: {contract_address}[/dim]\n"
        f"[dim]Compiler: {COMPILER_VERSION} | Optimization: Yes (200 runs)[/dim]",
        border_style="cyan"
    ))

    # Step 1: Submit source code for verification
    payload = {
        "apikey": api_key,
        "module": "contract",
        "action": "verifysourcecode",
        "contractaddress": contract_address,
        "sourceCode": source_code,
        "codeformat": "solidity-single-file",
        "contractname": "FiberRegistry",
        "compilerversion": COMPILER_VERSION,
        "optimizationUsed": 1,
        "runs": 200,
        "evmversion": "shanghai"
    }

    with console.status("Submitting source code payload to Arbiscan Sepolia API...", spinner="dots"):
        try:
            resp = requests.post(ARBISCAN_API_URL, data=payload, timeout=20)
            data = resp.json()
        except Exception as e:
            console.print(f"[bold red][X] Network Error:[/bold red] Failed to connect to Arbiscan API: {e}")
            print_manual_verification_guide(contract_address)
            sys.exit(1)

    if data.get("status") != "1":
        console.print(f"[bold red][X] Verification Submission Error:[/bold red] {data.get('result')}")
        print_manual_verification_guide(contract_address)
        sys.exit(1)

    guid = data.get("result")
    console.print(f"[bold green][+] Submission Accepted![/bold green] Verification Ticket GUID: [cyan]{guid}[/cyan]")
    console.print("[*] Polling Arbiscan API for compilation & verification status...")

    # Step 2: Poll status until verified
    poll_params = {
        "apikey": api_key,
        "module": "contract",
        "action": "checkverifystatus",
        "guid": guid
    }

    max_attempts = 15
    for attempt in range(1, max_attempts + 1):
        time.sleep(5)
        try:
            poll_resp = requests.get(ARBISCAN_API_URL, params=poll_params, timeout=15)
            poll_data = poll_resp.json()
            status_text = poll_data.get("result", "")
        except Exception:
            status_text = "Pending in queue"

        console.print(f"  [dim]Attempt {attempt}/{max_attempts}: Status -> {status_text}[/dim]")

        if "Pass - Verified" in status_text or poll_data.get("status") == "1":
            verified_url = f"{DEFAULT_EXPLORER_BASE}/address/{contract_address}#code"
            console.print(Panel(
                f"[bold green][+] CONTRACT VERIFIED SUCCESSFULLY ON ARBISCAN![/bold green]\n\n"
                f"Verified Explorer URL: [blue link={verified_url}]{verified_url}[/blue link]",
                border_style="green"
            ))
            return
        elif "Fail" in status_text:
            console.print(f"[bold red][X] Verification Failed:[/bold red] {status_text}")
            print_manual_verification_guide(contract_address)
            sys.exit(1)

    console.print("[bold yellow][!] Polling timed out. The verification may still be processing in queue.[/bold yellow]")
    print_manual_verification_guide(contract_address)

def main():
    parser = argparse.ArgumentParser(description="F.I.B.E.R. Smart Contract Source Code Verifier")
    parser.add_argument("--address", type=str, help="Deployed contract address on Arbitrum Sepolia")
    parser.add_argument("--api-key", type=str, help="Arbiscan API Key")

    args = parser.parse_args()

    contract_address = args.address or os.getenv("CONTRACT_ADDRESS")
    api_key = args.api_key or os.getenv("ARBISCAN_API_KEY") or os.getenv("ETHERSCAN_API_KEY") or "YourApiKeyToken"

    if not contract_address or contract_address == "0x0000000000000000000000000000000000000000":
        console.print("[bold red][X] Error:[/bold red] Contract address must be provided via --address or CONTRACT_ADDRESS in .env")
        sys.exit(1)

    verify_contract_on_arbiscan(contract_address, api_key)

if __name__ == "__main__":
    main()
