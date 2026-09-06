"""
F.I.B.E.R. Main CLI Entrypoint
Facial Identification & Blockchain Enforcement Runtime
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.vision import FaceDetector
from src.search import CopyseekerSearchEngine
from src.crypto import FiberCrypto
from src.blockchain import ArbitrumFiberClient

def main():
    parser = argparse.ArgumentParser(
        description="F.I.B.E.R. - Facial Identification & Blockchain Enforcement Runtime"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan image for face detection & cryptographic hashing")
    scan_parser.add_argument("image_path", type=str, help="Path to input image file")

    # Command: search
    search_parser = subparsers.add_parser("search", help="Perform reverse visual search using RapidAPI Copyseeker")
    search_parser.add_argument("image_path", type=str, help="Path to input image file")

    # Command: anchor / register
    anchor_parser = subparsers.add_parser("anchor", help="Scan face, search matches, and anchor evidence on Arbitrum Sepolia")
    anchor_parser.add_argument("image_path", type=str, help="Path to input image file")
    anchor_parser.add_argument("--url", type=str, default="https://fiber.enforcement/match", help="Evidence source URL or metadata link")

    # Command: verify / status
    verify_parser = subparsers.add_parser("verify", help="Query evidence record status from Arbitrum Sepolia")
    verify_parser.add_argument("evidence_hash", type=str, help="Bytes32 hex evidence hash")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scan":
        print(f"[F.I.B.E.R. Vision] Scanning image: {args.image_path}")
        detector = FaceDetector()
        faces = detector.detect_and_crop(args.image_path)
        print(f"[+] Detected {len(faces)} face(s).")
        for idx, f in enumerate(faces):
            face_hash = FiberCrypto.hash_pil_image(f["crop_pil"])
            print(f"  Face #{idx+1}: Box={f['box']}, Confidence={f['prob']:.4f}")
            print(f"  Keccak-256 Hash: 0x{face_hash.hex()}")

    elif args.command == "search":
        print(f"[F.I.B.E.R. Search] Executing reverse visual search for: {args.image_path}")
        search_engine = CopyseekerSearchEngine()
        results = search_engine.search_by_image(args.image_path)
        print(f"[+] Search Results: {results}")

    elif args.command == "anchor":
        print(f"[F.I.B.E.R. Pipeline] Anchoring evidence for: {args.image_path}")
        detector = FaceDetector()
        faces = detector.detect_and_crop(args.image_path)
        if not faces:
            print("[-] No valid faces detected.")
            sys.exit(1)

        evidence_hash = FiberCrypto.hash_pil_image(faces[0]["crop_pil"])
        print(f"[+] Evidence Keccak-256 Hash: 0x{evidence_hash.hex()}")

        client = ArbitrumFiberClient()
        if not client.is_connected():
            print("[-] Error connecting to Arbitrum Sepolia RPC.")
            sys.exit(1)

        res = client.anchor_evidence(evidence_hash, args.url)
        print(f"[+] Evidence transaction submitted to Arbitrum Sepolia: {res['tx_hash']}")

    elif args.command == "verify":
        client = ArbitrumFiberClient()
        hash_bytes = bytes.fromhex(args.evidence_hash.replace("0x", ""))
        rec = client.verify_evidence(hash_bytes)
        print(f"[+] Evidence Record: Exists={rec['exists']}")
        print(f"    Source URL: {rec['source_url']}")
        print(f"    Timestamp:  {rec['timestamp']}")
        print(f"    Registrar:  {rec['registered_by']}")

if __name__ == "__main__":
    main()
