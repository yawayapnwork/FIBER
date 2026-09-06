"""
F.I.B.E.R. Main CLI & Enforcement Pipeline Runner
Facial Identification & Blockchain Enforcement Runtime
Target Network: Arbitrum Sepolia EVM L2
"""

import sys
import os
import argparse
import datetime
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from src.vision import extract_face
from src.search import CopyseekerSearchEngine, NoMatchesFoundError, CopyseekerAPIError
from src.crypto import generate_evidence_hash, FiberCrypto
from src.blockchain import BlockchainClient

# Terminal Colors & ANSI Styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def print_banner():
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}  F.I.B.E.R.  |  Facial Identification & Blockchain Enforcement Runtime{RESET}")
    print(f"{DIM}  Target Network: Arbitrum Sepolia EVM L2  |  Zero Google APIs  |  Pure Python{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}\n")

def run_scan_pipeline(image_path: str):
    """
    Run full 5-step enforcement pipeline:
    Step 1: Face Extraction
    Step 2: Reverse Visual Search
    Step 3: Canonical Evidence Hashing
    Step 4: Blockchain Anchoring
    Step 5: Immediate Validation
    """
    print_banner()

    # STEP 1: Face Extraction
    print(f"{BOLD}[STEP 1/5] Extracting Primary Facial Crop...{RESET}")
    crop_output_path = "cropped_face.jpg"
    try:
        crop_path = extract_face(image_path, output_path=crop_output_path, padding=15)
        print(f"  {GREEN}[✓] Face extracted successfully:{RESET} {crop_path}")
    except ValueError as e:
        print(f"  {RED}[✗] Face Extraction Failed:{RESET} {e}")
        sys.exit(1)

    # STEP 2: Reverse Visual Search
    print(f"\n{BOLD}[STEP 2/5] Performing Reverse Visual Search (Copyseeker API)...{RESET}")
    try:
        search_engine = CopyseekerSearchEngine()
        search_res = search_engine.search(crop_output_path)
        print(f"  {GREEN}[✓] Match Discovered:{RESET} {search_res['source_url']}")
        print(f"  {DIM}    Page Title: {search_res['page_title']}{RESET}")
        print(f"  {DIM}    Matched Image: {search_res['matched_image_url']}{RESET}")
    except NoMatchesFoundError:
        print(f"  {YELLOW}[!] No web/social matches found. Using default verification URI.{RESET}")
        search_res = {
            "source_url": f"https://fiber.enforcement/records/{os.path.basename(image_path)}",
            "page_title": "F.I.B.E.R. Unmatched Direct Image Record",
            "matched_image_url": f"file://{os.path.abspath(crop_output_path)}",
            "discovered_at": int(datetime.datetime.now().timestamp())
        }
    except CopyseekerAPIError as e:
        print(f"  {YELLOW}[!] Search API Warning ({e}). Falling back to local evidence URI.{RESET}")
        search_res = {
            "source_url": f"https://fiber.enforcement/records/{os.path.basename(image_path)}",
            "page_title": "F.I.B.E.R. Local Evidence Record",
            "matched_image_url": f"file://{os.path.abspath(crop_output_path)}",
            "discovered_at": int(datetime.datetime.now().timestamp())
        }

    # STEP 3: Canonical Evidence Hashing
    print(f"\n{BOLD}[STEP 3/5] Generating RFC 8785 Canonical Evidence Hash...{RESET}")
    # Compute image crop Keccak-256
    crop_img = Image.open(crop_output_path)
    crop_keccak = FiberCrypto.hash_pil_image(crop_img)

    evidence_manifest = {
        "facial_crop_keccak256": "0x" + crop_keccak.hex(),
        "source_url": search_res["source_url"],
        "page_title": search_res["page_title"],
        "discovered_at": search_res["discovered_at"]
    }

    hex_evidence_hash, bytes32_hash = generate_evidence_hash(evidence_manifest)
    print(f"  {GREEN}[✓] Canonical SHA-256 Digest:{RESET} {hex_evidence_hash}")

    # STEP 4: Blockchain Anchoring
    print(f"\n{BOLD}[STEP 4/5] Anchoring Evidence to Arbitrum Sepolia L2...{RESET}")
    client = BlockchainClient()
    if not client.is_connected():
        print(f"  {RED}[✗] Failed to connect to Arbitrum Sepolia RPC at {client.rpc_url}{RESET}")
        sys.exit(1)

    try:
        anchor_res = client.anchor(hex_evidence_hash, search_res["source_url"])
        print(f"  {GREEN}[✓] Transaction Confirmed!{RESET}")
        print(f"      Tx Hash:       {anchor_res['tx_hash']}")
        print(f"      Block Number:  {anchor_res['block_number']}")
        print(f"      Arbiscan Link: {CYAN}{anchor_res['explorer_url']}{RESET}")
    except ValueError as e:
        print(f"  {RED}[✗] On-Chain Transaction Error:{RESET} {e}")
        print(f"  {DIM}Please verify PRIVATE_KEY and CONTRACT_ADDRESS in your .env configuration.{RESET}")
        sys.exit(1)

    # STEP 5: Immediate Validation
    print(f"\n{BOLD}[STEP 5/5] Verifying On-Chain Evidence Record...{RESET}")
    verify_res = client.verify(hex_evidence_hash)
    if verify_res["exists"]:
        print(f"  {GREEN}[✓] ON-CHAIN VERIFICATION CONFIRMED{RESET}")
        print(f"      Evidence Hash: {verify_res['evidence_hash']}")
        print(f"      Registered By: {verify_res['registered_by']}")
        print(f"      Source URL:    {verify_res['source_url']}")
        ts_str = datetime.datetime.fromtimestamp(verify_res['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"      Timestamp:     {ts_str}")
    else:
        print(f"  {RED}[✗] Verification Failed: Record not found on-chain.{RESET}")

    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{GREEN}{BOLD}  PIPELINE EXECUTION COMPLETE  |  EVIDENCE ANCHORED ON ARBITRUM SEPOLIA{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}\n")

def run_verify_command(evidence_hash: str):
    """
    Directly query Arbitrum Sepolia contract to verify an existing evidence hash.
    """
    print_banner()
    print(f"{BOLD}[F.I.B.E.R. Verification] Inspecting Arbitrum Sepolia Contract...{RESET}")
    client = BlockchainClient()
    if not client.is_connected():
        print(f"  {RED}[✗] Failed to connect to Arbitrum Sepolia RPC at {client.rpc_url}{RESET}")
        sys.exit(1)

    try:
        res = client.verify(evidence_hash)
        if res["exists"]:
            print(f"\n  {GREEN}{BOLD}[✓] VALID EVIDENCE RECORD FOUND ON-CHAIN{RESET}")
            print(f"      Evidence Hash:    {res['evidence_hash']}")
            print(f"      Registered By:    {res['registered_by']}")
            print(f"      Source URL:       {res['source_url']}")
            ts_str = datetime.datetime.fromtimestamp(res['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"      Timestamp:        {ts_str}")
            print(f"      Contract Address: {res['contract_address']}")
            print(f"      Arbiscan Link:    {CYAN}{res['explorer_url']}{RESET}\n")
        else:
            print(f"\n  {RED}{BOLD}[✗] RECORD NOT FOUND{RESET}")
            print(f"      No evidence record exists for hash: {evidence_hash}\n")
    except ValueError as e:
        print(f"  {RED}[✗] Verification Query Error:{RESET} {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="F.I.B.E.R. - Facial Identification & Blockchain Enforcement Runtime"
    )
    # Support both --scan / --verify flags AND positional subcommands
    parser.add_argument("--scan", type=str, help="Run 5-step enforcement pipeline on target image")
    parser.add_argument("--verify", type=str, help="Verify existing evidence hash on Arbitrum Sepolia")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    scan_sub = subparsers.add_parser("scan", help="Run 5-step enforcement pipeline on target image")
    scan_sub.add_argument("image_path", type=str, help="Path to input image file")

    verify_sub = subparsers.add_parser("verify", help="Verify existing evidence hash on Arbitrum Sepolia")
    verify_sub.add_argument("evidence_hash", type=str, help="Bytes32 hex evidence hash")

    args = parser.parse_args()

    # Route based on flags or subcommands
    if args.scan:
        run_scan_pipeline(args.scan)
    elif args.verify:
        run_verify_command(args.verify)
    elif args.command == "scan":
        run_scan_pipeline(args.image_path)
    elif args.command == "verify":
        run_verify_command(args.evidence_hash)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
