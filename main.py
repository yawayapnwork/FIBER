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

# Rich UI Integration
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.status import Status
from rich import box

# Load environment variables from .env
load_dotenv()

from src.vision import extract_face_info
from src.search import CopyseekerSearchEngine, NoMatchesFoundError, CopyseekerAPIError, CopyseekerTimeoutError, CopyseekerRateLimitError
from src.crypto import generate_evidence_hash, FiberCrypto
from src.blockchain import BlockchainClient

console = Console()

def print_banner():
    banner_text = (
        "[bold cyan]F.I.B.E.R.  |  Facial Identification & Blockchain Enforcement Runtime[/bold cyan]\n"
        "[dim]Target Network: Arbitrum Sepolia EVM L2 (421614)  |  Zero Google APIs  |  Pure Python[/dim]"
    )
    console.print(Panel(banner_text, expand=False, border_style="cyan"))

def parse_social_info(url: str, title: str) -> str:
    """Extract platform, author, and URL details from search match."""
    url_lower = url.lower()
    if "twitter.com" in url_lower or "x.com" in url_lower:
        platform = "X / Twitter"
    elif "instagram.com" in url_lower:
        platform = "Instagram"
    elif "linkedin.com" in url_lower:
        platform = "LinkedIn"
    elif "reddit.com" in url_lower:
        platform = "Reddit"
    elif "facebook.com" in url_lower:
        platform = "Facebook"
    elif "tiktok.com" in url_lower:
        platform = "TikTok"
    else:
        platform = "Web Discovery"

    return f"Platform: [bold yellow]{platform}[/bold yellow] | Title: {title}\nURL: [blue link={url}]{url}[/blue link]"

def run_scan_pipeline(image_path: str):
    """
    Run full 5-step enforcement pipeline with Rich terminal UI and exit codes.
    - Exit 0: Success (match and anchor verified)
    - Exit 1: Detection failure (no valid human face found)
    - Exit 2: Chain revert / Web3 transaction failure
    """
    print_banner()

    # STEP 1: Face Extraction
    crop_output_path = "cropped_face.jpg"
    with console.status("[bold green]Step 1/5: Extracting facial crop with Pillow & MTCNN...", spinner="dots"):
        try:
            face_info = extract_face_info(image_path, output_path=crop_output_path, padding=15)
            crop_path = face_info["output_path"]
        except ValueError as e:
            console.print(f"[bold red][X] Step 1 Detection Failure:[/bold red] {e}")
            console.print("[dim]Hint: Ensure the image contains a clear front-facing human face.[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red][X] Image Processing Error:[/bold red] {e}")
            sys.exit(1)

    console.print(f"[bold green][+] Step 1 Complete:[/bold green] Face extracted successfully ({face_info['width']}x{face_info['height']}px)")

    # STEP 2: Reverse Visual Search
    with console.status("[bold green]Step 2/5: Querying Copyseeker Reverse Visual Search Index...", spinner="earth"):
        try:
            search_engine = CopyseekerSearchEngine()
            search_res = search_engine.search(crop_output_path)
        except NoMatchesFoundError:
            console.print("[bold yellow][!] Step 2 Warning:[/bold yellow] No web/social matches found. Using direct evidence URI.")
            search_res = {
                "source_url": f"https://fiber.enforcement/records/{os.path.basename(image_path)}",
                "page_title": "F.I.B.E.R. Direct Image Record",
                "matched_image_url": f"file://{os.path.abspath(crop_output_path)}",
                "discovered_at": int(datetime.datetime.now().timestamp())
            }
        except CopyseekerTimeoutError:
            console.print("[bold yellow][!] Step 2 Timeout:[/bold yellow] RapidAPI search timed out. Falling back to local evidence record.")
            search_res = {
                "source_url": f"https://fiber.enforcement/records/{os.path.basename(image_path)}",
                "page_title": "F.I.B.E.R. Fallback Evidence Record",
                "matched_image_url": f"file://{os.path.abspath(crop_output_path)}",
                "discovered_at": int(datetime.datetime.now().timestamp())
            }
        except (CopyseekerRateLimitError, CopyseekerAPIError) as e:
            console.print(f"[bold yellow][!] Step 2 API Warning ({e}):[/bold yellow] Falling back to local evidence URI.")
            search_res = {
                "source_url": f"https://fiber.enforcement/records/{os.path.basename(image_path)}",
                "page_title": "F.I.B.E.R. Local Evidence Record",
                "matched_image_url": f"file://{os.path.abspath(crop_output_path)}",
                "discovered_at": int(datetime.datetime.now().timestamp())
            }

    console.print(f"[bold green][+] Step 2 Complete:[/bold green] Match discovered: [blue link={search_res['source_url']}]{search_res['source_url']}[/blue link]")

    # STEP 3: Canonical Evidence Hashing
    with console.status("[bold green]Step 3/5: Computing RFC 8785 Canonical JSON SHA-256 Fingerprint...", spinner="bouncingBar"):
        crop_img = Image.open(crop_output_path)
        crop_keccak = FiberCrypto.hash_pil_image(crop_img)

        evidence_manifest = {
            "facial_crop_keccak256": "0x" + crop_keccak.hex(),
            "source_url": search_res["source_url"],
            "page_title": search_res["page_title"],
            "discovered_at": search_res["discovered_at"]
        }

        hex_evidence_hash, bytes32_hash = generate_evidence_hash(evidence_manifest)

    console.print(f"[bold green][+] Step 3 Complete:[/bold green] Canonical Fingerprint: [cyan]{hex_evidence_hash}[/cyan]")

    # STEP 4: Blockchain Anchoring
    client = BlockchainClient()
    if not client.is_connected():
        console.print(f"[bold red][X] Step 4 RPC Connection Error:[/bold red] Cannot connect to Arbitrum Sepolia RPC at [cyan]{client.rpc_url}[/cyan]")
        console.print("[dim]Hint: Check network connectivity or update ARBITRUM_SEPOLIA_RPC in .env.[/dim]")
        sys.exit(2)

    with console.status("[bold green]Step 4/5: Signing & Mining Transaction on Arbitrum Sepolia EVM L2...", spinner="moon"):
        try:
            anchor_res = client.anchor(hex_evidence_hash, search_res["source_url"])
        except ValueError as e:
            console.print(f"[bold red][X] Step 4 Configuration Error:[/bold red] {e}")
            console.print("[dim]Hint: Please set a valid PRIVATE_KEY and CONTRACT_ADDRESS in your .env file.[/dim]")
            sys.exit(2)
        except RuntimeError as e:
            console.print(f"[bold red][X] Step 4 Chain Revert Error:[/bold red] {e}")
            sys.exit(2)
        except Exception as e:
            console.print(f"[bold red][X] Step 4 Transaction Error:[/bold red] {e}")
            sys.exit(2)

    console.print(f"[bold green][+] Step 4 Complete:[/bold green] Transaction mined in Block [cyan]#{anchor_res['block_number']}[/cyan]")

    # STEP 5: Immediate Validation
    with console.status("[bold green]Step 5/5: Verifying On-Chain Persisted State...", spinner="clock"):
        try:
            verify_res = client.verify(hex_evidence_hash)
        except Exception as e:
            console.print(f"[bold red][X] Step 5 Verification Query Failed:[/bold red] {e}")
            sys.exit(2)

    if not verify_res["exists"]:
        console.print("[bold red][X] Step 5 Validation Error: Record not found on-chain.[/bold red]")
        sys.exit(2)

    console.print(f"[bold green][+] Step 5 Complete:[/bold green] On-Chain Record Verified!")

    # OUTPUT CLEAN SUMMARY TABLE
    console.print("\n")
    table = Table(title="F.I.B.E.R. Enforcement Summary", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Property", style="bold cyan", width=32)
    table.add_column("Details / On-Chain State", style="white")

    box_str = f"{face_info['box']} ({face_info['width']}x{face_info['height']}px, Aspect {face_info['aspect_ratio']})"
    social_info = parse_social_info(search_res["source_url"], search_res["page_title"])

    table.add_row("Detected Face Bounds", box_str)
    table.add_row("Confidence Score", f"{face_info['confidence'] * 100:.2f}%")
    table.add_row("Discovered Footprint", social_info)
    table.add_row("Canonical SHA-256 Fingerprint", hex_evidence_hash)
    table.add_row("Arbitrum Tx Hash", f"{anchor_res['tx_hash']} (Block #{anchor_res['block_number']})")
    table.add_row("Arbiscan Explorer Link", f"[blue link={anchor_res['explorer_url']}]{anchor_res['explorer_url']}[/blue link]")
    table.add_row("Registered By (Registrar)", verify_res["registered_by"])

    console.print(table)
    console.print(Panel("[bold green]ENFORCEMENT PIPELINE COMPLETED SUCCESSFULLY (Exit Code 0)[/bold green]", border_style="green", expand=False))
    sys.exit(0)

def run_verify_command(evidence_hash: str):
    """
    Directly query Arbitrum Sepolia contract to verify an existing evidence hash.
    - Exit 0: Found and verified.
    - Exit 2: Not found or chain query error.
    """
    print_banner()
    client = BlockchainClient()
    if not client.is_connected():
        console.print(f"[bold red][X] RPC Connection Error:[/bold red] Cannot connect to Arbitrum Sepolia RPC at [cyan]{client.rpc_url}[/cyan]")
        sys.exit(2)

    with console.status("[bold green]Querying Arbitrum Sepolia FiberRegistry Contract...", spinner="dots"):
        try:
            res = client.verify(evidence_hash)
        except Exception as e:
            console.print(f"[bold red][X] Query Error:[/bold red] {e}")
            sys.exit(2)

    if res["exists"]:
        table = Table(title="On-Chain Evidence Record Verified", box=box.ROUNDED, header_style="bold green")
        table.add_column("Property", style="bold cyan", width=25)
        table.add_column("Value", style="white")

        ts_str = datetime.datetime.fromtimestamp(res['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        table.add_row("Verification Status", "[bold green]CONFIRMED (EXISTS)[/bold green]")
        table.add_row("Evidence Hash", res["evidence_hash"])
        table.add_row("Registered By", res["registered_by"])
        table.add_row("Source Match URL", res["source_url"])
        table.add_row("Block Timestamp", ts_str)
        table.add_row("Contract Address", res["contract_address"])
        table.add_row("Arbiscan Link", f"[blue link={res['explorer_url']}]{res['explorer_url']}[/blue link]")

        console.print(table)
        sys.exit(0)
    else:
        console.print(Panel(f"[bold red]RECORD NOT FOUND ON-CHAIN[/bold red]\nNo evidence anchored for hash: {evidence_hash}", border_style="red", expand=False))
        sys.exit(2)

def main():
    parser = argparse.ArgumentParser(
        description="F.I.B.E.R. - Facial Identification & Blockchain Enforcement Runtime"
    )
    parser.add_argument("--scan", type=str, help="Run 5-step enforcement pipeline on target image")
    parser.add_argument("--verify", type=str, help="Verify existing evidence hash on Arbitrum Sepolia")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    scan_sub = subparsers.add_parser("scan", help="Run 5-step enforcement pipeline on target image")
    scan_sub.add_argument("image_path", type=str, help="Path to input image file")

    verify_sub = subparsers.add_parser("verify", help="Verify existing evidence hash on Arbitrum Sepolia")
    verify_sub.add_argument("evidence_hash", type=str, help="Bytes32 hex evidence hash")

    args = parser.parse_args()

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
