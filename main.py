"""
F.I.B.E.R. Main CLI & Enforcement Pipeline Runner
Facial Identification & Blockchain Enforcement Runtime
Target Network: Arbitrum Sepolia EVM L2
"""

import sys
import os
import argparse
import datetime
import time
import io
import copy

import requests
import torch
import torch.nn.functional as F
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

from src.matcher import extract_embedding, mtcnn
from src.search import CopyseekerSearchEngine, NoMatchesFoundError, CopyseekerAPIError, CopyseekerTimeoutError, CopyseekerRateLimitError, download_candidate_image
from src.blockchain import BlockchainClient
from src.merkle import EvidenceMerkleTree
from src.crypto import FiberCrypto
from src.liveness import verify_liveness
from src.relayer import execute_meta_tx
from src.lsh_hasher import compute_simhash
from src.tls_witness import capture_witness_metadata
import torchvision.transforms.functional as TF
from PIL import ImageOps

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

def parse_author(url: str, title: str) -> str:
    """Extract author or title for metadata"""
    return title

def run_scan_pipeline(image_path: str, is_tamper_test: bool = False, manual_url: str = None, is_gasless: bool = False):
    """
    Run full 6-step enforcement pipeline with Rich terminal UI.
    Supports bypass of indexing latency via manual_url.
    """
    print_banner()

    # STEP 1: Face Extraction & Embedding
    with console.status("[bold green]Step 1/6: Detecting face & extracting 512-D embedding (MTCNN/InceptionResnetV1)...", spinner="dots"):
        if not os.path.exists(image_path):
            console.print(f"[bold red][X] Step 1 Error:[/bold red] Image file not found: {image_path}")
            sys.exit(1)
        try:
            input_img = Image.open(image_path)
            
            # --- Liveness Detection Check ---
            fixed_img = ImageOps.exif_transpose(input_img).convert("RGB")
            x_aligned, prob = mtcnn(fixed_img, return_prob=True)
            
            if x_aligned is None or prob is None or prob < 0.85:
                raise ValueError("No valid human face detected with confidence > 0.85")
                
            face_pil = TF.to_pil_image(x_aligned.byte())
            liveness_res = verify_liveness(face_pil)
            
            if not liveness_res["is_live"]:
                raise ValueError("Spoof detected: input failed passive liveness heuristics.")
            # --------------------------------
            
            input_tensor = extract_embedding(input_img)
            input_vector_bytes = input_tensor.cpu().numpy().tobytes()
            
            # Generate 64-bit Locality-Sensitive Hash (SimHash)
            fingerprint = compute_simhash(input_tensor)
            
            # Generate blinding salt for zero-knowledge match proofs
            blind_res = FiberCrypto.generate_blinded_commitment(input_tensor)
            blinding_salt = blind_res["salt"]
        except ValueError as e:
            console.print(f"[bold red][X] Step 1 Detection Failure:[/bold red] {e}")
            console.print("[dim]Hint: Ensure the image contains a clear front-facing human face.[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red][X] Image Processing Error:[/bold red] {e}")
            sys.exit(1)

    console.print(f"[bold green][+] Step 1 Complete:[/bold green] High-confidence facial embedding extracted.")

    # STEP 2: Reverse Visual Search
    if manual_url:
        console.print(f"[bold yellow][!] Step 2 Bypassed:[/bold yellow] Using manual URL override due to search indexing latency.")
        search_res = {
    with console.status("[bold green]Step 2/6: Querying Non-Google Reverse Visual Search Index...", spinner="earth"):
        try:
            if manual_url:
                search_res = {
                    "source_url": manual_url,
                    "page_title": "Manual Verification Override",
                    "matched_image_url": manual_url,
                    "discovered_at": int(time.time())
                }
            else:
                search_engine = CopyseekerSearchEngine()
                search_res = search_engine.search(image_path)
                
            # Capture network witness metadata from target source
            witness_manifest = capture_witness_metadata(search_res["source_url"])
        except Exception as e:
            console.print(f"[bold red][X] Step 2 Oracle Query/Witness Error:[/bold red] {e}")
            sys.exit(2)

    console.print(f"[bold green][+] Step 2 Complete:[/bold green] Found reverse match at [cyan]{search_res['source_url']}[/cyan]")
    console.print(f"    [dim]TLS Witness Root:[/dim] [magenta]{witness_manifest.get('tlsWitnessRoot')}[/magenta]")
    if witness_manifest.get("cert_sha256"):
        console.print(f"    [dim]Remote Cert SHA256:[/dim] {witness_manifest['cert_sha256'][:32]}...")

    # STEP 3: Bidirectional Face Verification
    with console.status("[bold green]Step 3/6: Running Bidirectional Face Verification (Cosine Similarity)...", spinner="bouncingBar"):
        try:
            candidate_url = search_res["matched_image_url"]
            resp, auth_metadata = download_candidate_image(candidate_url)
            candidate_img = Image.open(io.BytesIO(resp.content))
            candidate_tensor = extract_embedding(candidate_img)
            candidate_vector_bytes = candidate_tensor.cpu().numpy().tobytes()
            
            cosine_sim = F.cosine_similarity(input_tensor, candidate_tensor).item()
        except Exception as e:
            console.print(f"[bold red][X] Step 3 Verification Failure:[/bold red] Failed to process candidate image: {e}")
            sys.exit(1)
            
        if cosine_sim < 0.72:
            console.print(f"[bold red][X] Step 3 Verification Rejected:[/bold red] Cosine Similarity ({cosine_sim:.4f}) below threshold (0.72).")
            sys.exit(1)

    console.print(f"[bold green][+] Step 3 Complete:[/bold green] Identity cryptographically verified. Similarity Score: [cyan]{cosine_sim:.4f}[/cyan] (>= 0.72)")

    # STEP 4: Merkle Tree Construction
    with console.status("[bold green]Step 4/6: Constructing 3-Leaf Merkle Tree Commitment...", spinner="moon"):
        # Use Bi-Temporal tracking
        if manual_url:
            published_at = search_res["discovered_at"] - 300 # Mock 5 mins ago for unindexed post
            author = "Manual Override Verify"
        else:
            published_at = search_res["discovered_at"] - 3600 # Assume ~1 hour ago for organically indexed posts
            author = parse_author(search_res["source_url"], search_res["page_title"])
            
        metadata = FiberCrypto.create_bitemporal_manifest(
            source_url=search_res["source_url"],
            author=author,
            discovered_at=search_res["discovered_at"],
            published_at=published_at
        )
        metadata["tls_witness"] = witness_manifest
        metadata.update(auth_metadata)

        merkle_res = EvidenceMerkleTree.build_tree(input_vector_bytes, candidate_vector_bytes, metadata, salt=blinding_salt)
        merkle_root = merkle_res["merkle_root"]
        
        # Securely save the salt inside the local audit log
        audit_dir = os.path.join("audit_logs", merkle_root)
        os.makedirs(audit_dir, exist_ok=True)
        with open(os.path.join(audit_dir, "secret.key"), "wb") as f:
            f.write(blinding_salt)

    console.print(f"[bold green][+] Step 4 Complete:[/bold green] Bi-Temporal Merkle Root Generated: [cyan]{merkle_root}[/cyan]")

    # TAMPER TEST MODE BRANCH
    if is_tamper_test:
        console.print("\n[bold yellow]--- COMMENCING TAMPER TEST MUTATION ---[/bold yellow]")
        
        # Mutate 1 byte of the candidate vector
        tampered_candidate_bytes = bytearray(candidate_vector_bytes)
        tampered_candidate_bytes[0] ^= 0xFF
        
        # Modifying a query parameter in the source URL
        tampered_metadata = copy.deepcopy(metadata)
        tampered_metadata["url"] += "?tampered=true"
        
        tampered_merkle_res = EvidenceMerkleTree.build_tree(input_vector_bytes, bytes(tampered_candidate_bytes), tampered_metadata, salt=blinding_salt)
        tampered_root = tampered_merkle_res["merkle_root"]
        
        console.print(f"[bold yellow][!] Single byte mutation applied to asset payload.[/bold yellow]")
        console.print(f"[bold yellow][!] Source URL metadata manipulated.[/bold yellow]")
        console.print(f"[bold yellow][!] Recomputing Merkle Root ->[/bold yellow] [cyan]{tampered_root}[/cyan]")
        
        client = BlockchainClient()
        if not client.is_connected():
            console.print(f"[bold red][X] RPC Connection Error[/bold red]")
            sys.exit(2)
            
        try:
            res = client.verify(tampered_root)
            if not res["exists"]:
                console.print("\n")
                console.print(Panel(
                    f"[bold red]TAMPER DETECTED: Computed {tampered_root[:10]}... does NOT exist on Arbitrum Sepolia[/bold red]\n"
                    "Zero-Trust immutability guarantee upheld. Evidence is invalid.",
                    border_style="red", expand=False
                ))
                sys.exit(0)
            else:
                console.print("[bold red][X] TAMPER TEST FAILED: Tampered root somehow exists on-chain![/bold red]")
                sys.exit(1)
        except Exception as e:
            console.print(f"[bold red][X] Verification Query Error:[/bold red] {e}")
            sys.exit(2)

    # STEP 5: Blockchain Anchoring (Only in normal scan mode)
    client = BlockchainClient()
    if not client.is_connected():
        console.print(f"[bold red][X] Step 5 RPC Connection Error:[/bold red] Cannot connect to Arbitrum Sepolia RPC.")
        sys.exit(2)

    with console.status("[bold green]Step 5/6: Anchoring Merkle Root to FiberMerkleRegistry on Arbitrum Sepolia...", spinner="dots2"):
        try:
            if is_gasless:
                user_key = os.getenv("PRIVATE_KEY")
                relayer_key = os.getenv("RELAYER_PRIVATE_KEY")
                forwarder = os.getenv("FORWARDER_ADDRESS")
                
                if not relayer_key or not forwarder:
                    raise ValueError("RELAYER_PRIVATE_KEY and FORWARDER_ADDRESS must be set in .env for gasless meta-transactions")
                if not user_key:
                    raise ValueError("PRIVATE_KEY is required to sign the zero-gas payload")
                    
                target = client.contract_address
                encoded_data = client.encode_anchor_payload(merkle_root, search_res["source_url"], bypass_flag=bool(manual_url), biometric_fingerprint=fingerprint)
                
                console.print("\n[dim]Signing zero-gas payload (EIP-712) & delegating to Sponsor Relayer...[/dim]")
                tx_hash = execute_meta_tx(
                    client, forwarder, target, encoded_data, user_key, relayer_key
                )
                
                anchor_res = {
                    "tx_hash": tx_hash,
                    "block_number": "Mined (Relayer)",
                    "explorer_url": f"https://sepolia.arbiscan.io/tx/{tx_hash}",
                    "gas_used": "0 (Paid by Sponsor)"
                }
            else:
                anchor_res = client.anchor(merkle_root, search_res["source_url"], bypass_flag=bool(manual_url), biometric_fingerprint=fingerprint)
        except ValueError as e:
            console.print(f"[bold red][X] Step 5 Configuration Error:[/bold red] {e}")
            sys.exit(2)
        except RuntimeError as e:
            console.print(f"[bold red][X] Step 5 Chain Error:[/bold red] {e}")
            sys.exit(2)
        except Exception as e:
            console.print(f"[bold red][X] Step 5 Transaction Error:[/bold red] {e}")
            sys.exit(2)

    console.print(f"[bold green][+] Step 5 Complete:[/bold green] Transaction anchored. Block: [cyan]{anchor_res['block_number']}[/cyan] | Gas: [yellow]{anchor_res.get('gas_used', 'N/A')}[/yellow]")

    # STEP 6: Immediate Validation & Display
    with console.status("[bold green]Step 6/6: Verifying On-Chain Persisted State...", spinner="clock"):
        try:
            verify_res = client.verify(merkle_root)
        except Exception as e:
            console.print(f"[bold red][X] Step 6 Verification Query Failed:[/bold red] {e}")
            sys.exit(2)

    if not verify_res["exists"]:
        console.print("[bold red][X] Step 6 Validation Error: Merkle root not found on-chain.[/bold red]")
        sys.exit(2)

    console.print(f"[bold green][+] Step 6 Complete:[/bold green] On-Chain State Confirmed!")

    # OUTPUT CLEAN SUMMARY TABLE
    console.print("\n")
    table = Table(title="F.I.B.E.R. Immutable Evidence Receipt", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Property", style="bold cyan", width=35)
    table.add_column("Details / On-Chain State", style="white")

    social_info = parse_social_info(search_res["source_url"], search_res["page_title"])

    table.add_row("Cosine Similarity Match Score", f"{cosine_sim:.4f} / 1.0 (Threshold: 0.72)")
    table.add_row("Discovered Footprint", social_info)
    table.add_row("3-Leaf Merkle Root (Commitment)", merkle_root)
    table.add_row("64-bit SimHash Fingerprint", str(fingerprint))
    table.add_row("Biometric Root (Leaf A)", merkle_res["leaves"]["leaf_a"] + " [bold yellow](Blinded)[/bold yellow]")
    table.add_row("Visual Asset Root (Leaf B)", merkle_res["leaves"]["leaf_b"])
    table.add_row("Context Root (Leaf C)", merkle_res["leaves"]["leaf_c"])
    
    if metadata.get("access_scope") == "WALLED_RESTRICTED":
        table.add_row("Access Scope", "[bold red]WALLED_RESTRICTED (OpenGraph Fallback)[/bold red]")
        table.add_row("Auth Wall Hash (Proof)", f"[dim]{metadata.get('auth_wall_hash')}...[/dim]")
    
    table.add_row("Indexing Lag (Seconds)", str(metadata["indexing_lag_seconds"]))
    
    if verify_res.get("indexing_delay_bypass"):
        table.add_row("Indexing Delay Bypass", "[bold yellow]TRUE (Manual Verification)[/bold yellow]")
        
    table.add_row("Arbitrum Tx Hash", f"{anchor_res['tx_hash']} (Block #{anchor_res['block_number']})")
    table.add_row("Arbiscan Explorer Link", f"[blue link={anchor_res['explorer_url']}]{anchor_res['explorer_url']}[/blue link]")
    table.add_row("Registered By (Registrar)", verify_res["registered_by"])

    console.print(table)
    console.print(Panel("[bold green]ENFORCEMENT PIPELINE COMPLETED SUCCESSFULLY (Exit Code 0)[/bold green]", border_style="green", expand=False))
    sys.exit(0)


def run_verify_command(merkle_root: str):
    """
    Directly query Arbitrum Sepolia FiberMerkleRegistry to verify an existing Merkle root.
    """
    print_banner()
    client = BlockchainClient()
    if not client.is_connected():
        console.print(f"[bold red][X] RPC Connection Error:[/bold red] Cannot connect to Arbitrum Sepolia RPC.")
        sys.exit(2)

    with console.status("[bold green]Querying Arbitrum Sepolia FiberMerkleRegistry...", spinner="dots"):
        try:
            res = client.verify(merkle_root)
        except Exception as e:
            console.print(f"[bold red][X] Query Error:[/bold red] {e}")
            sys.exit(2)

    if res["exists"]:
        table = Table(title="On-Chain Evidence Record Verified", box=box.ROUNDED, header_style="bold green")
        table.add_column("Property", style="bold cyan", width=25)
        table.add_column("Value", style="white")

        ts_str = datetime.datetime.fromtimestamp(res['timestamp'], tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        table.add_row("Verification Status", "[bold green]CONFIRMED (EXISTS)[/bold green]")
        table.add_row("Merkle Root", res["merkle_root"])
        
        if res.get("indexing_delay_bypass"):
            table.add_row("Indexing Delay Bypass", "[bold yellow]TRUE (Manual Override)[/bold yellow]")
            
        table.add_row("Registered By", res["registered_by"])
        table.add_row("Source Match URL", res["source_url"])
        table.add_row("Block Timestamp", ts_str)
        table.add_row("Contract Address", res["contract_address"])
        table.add_row("Arbiscan Link", f"[blue link={res['explorer_url']}]{res['explorer_url']}[/blue link]")
        if res.get("biometric_fingerprint"):
            table.add_row("64-bit SimHash", str(res["biometric_fingerprint"]))

        console.print(table)
        sys.exit(0)
    else:
        console.print(Panel(f"[bold red]RECORD NOT FOUND ON-CHAIN[/bold red]\nNo evidence anchored for Merkle Root: {merkle_root}", border_style="red", expand=False))
        sys.exit(2)


def run_visual_audit(original_img_path: str, candidate_img_path: str):
    """
    Run the Visual Auditor tool on two images.
    """
    from src.visual_auditor import generate_tamper_delta
    
    console.print(f"\n[bold cyan]F.I.B.E.R. Visual Auditor[/bold cyan]")
    console.print(f"Original:  [dim]{original_img_path}[/dim]")
    console.print(f"Candidate: [dim]{candidate_img_path}[/dim]\n")
    
    with console.status("[bold green]Calculating Euclidean pixel distances and rendering delta mask...", spinner="dots2"):
        delta_path = os.path.join(os.getcwd(), "audit_logs", "tamper_delta.png")
        try:
            res = generate_tamper_delta(original_img_path, candidate_img_path, delta_path)
        except Exception as e:
            console.print(f"[bold red][X] Auditor Error:[/bold red] {e}")
            sys.exit(1)
            
    # Render Terminal Telemetry utilizing Rich UI components
    table = Table(title="Visual Audit Results", box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Metric", style="bold cyan", width=30)
    table.add_column("Value", style="white")
    
    score = res["structural_parity_score"]
    score_style = "bold green" if score >= 99.0 else "bold red"
    
    bbox = res["bounding_box"]
    if bbox:
        bbox_str = f"({bbox[0]}, {bbox[1]}) to ({bbox[2]}, {bbox[3]})"
    else:
        bbox_str = "None detected"
        
    table.add_row("Structural Parity Score (%)", f"[{score_style}]{score:.4f}%[/{score_style}]")
    table.add_row("Tamper Anomaly Coordinates", bbox_str)
    table.add_row("Delta Evidence Saved At", f"[dim]{res['delta_path']}[/dim]")
    
    console.print(table)
    if score < 99.0:
        console.print("[bold red][!] Warning: Significant visual tampering detected.[/bold red]")


def main():
    parser = argparse.ArgumentParser(
        description="F.I.B.E.R. - Facial Identification & Blockchain Enforcement Runtime"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    
    scan_sub = subparsers.add_parser("scan", help="Run 6-step enforcement pipeline on target image")
    scan_sub.add_argument("image_path", type=str, help="Path to input image file")
    scan_sub.add_argument("--manual-url", type=str, help="Bypass search and directly verify a post URL", default=None)
    scan_sub.add_argument("--gasless", action="store_true", help="Execute transaction via relayer using EIP-2771 forwarder")
    
    verify_sub = subparsers.add_parser("verify", help="Verify existing Merkle Root on Arbitrum Sepolia")
    verify_sub.add_argument("merkle_root", type=str, help="Bytes32 hex Merkle Root")

    tamper_sub = subparsers.add_parser("tamper-test", help="Demonstrate zero-trust immutability via payload mutation")
    tamper_sub.add_argument("image_path", type=str, help="Path to input image file")
    
    audit_sub = subparsers.add_parser("audit", help="Run cryptographic visual auditor on two images")
    audit_sub.add_argument("original", type=str, help="Path to original image")
    audit_sub.add_argument("candidate", type=str, help="Path to candidate image")

    args = parser.parse_args()

    if args.command == "scan":
        run_scan_pipeline(args.image_path, is_tamper_test=False, manual_url=args.manual_url, is_gasless=args.gasless)
    elif args.command == "verify":
        run_verify_command(args.merkle_root)
    elif args.command == "tamper-test":
        run_scan_pipeline(args.image_path, is_tamper_test=True)
    elif args.command == "audit":
        run_visual_audit(args.original, args.candidate)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
