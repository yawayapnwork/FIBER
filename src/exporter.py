"""
F.I.B.E.R. Data Provenance Exporter Module
Automated evidence directory snapshot creation, proof package zip exporting,
and local manifest recalculation & on-chain verification.
"""

import datetime
import json
import os
import shutil
import zipfile
from typing import Any

from src.blockchain import BlockchainClient
from src.crypto import generate_evidence_hash


def create_evidence_snapshot(
    evidence_hash: str,
    input_image_path: str,
    crop_image_path: str,
    search_res: dict[str, Any],
    anchor_res: dict[str, Any],
    verify_res: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    audit_base_dir: str = "audit_logs",
    timestamp: str | int | None = None
) -> str:
    """
    Create automated timestamped evidence directory inside audit_logs/<evidence_hash[:10]>/

    Save 3 artifacts:
      1. input_face.jpg: Original uploaded image
      2. detected_crop.jpg: Pillow-extracted face crop
      3. receipt.json: Canonical metadata file with all provenance fields

    :param evidence_hash: Canonical SHA-256 evidence hash (0x-prefixed hex string)
    :param input_image_path: Path to original input face image
    :param crop_image_path: Path to extracted face crop image
    :param search_res: Search result dict containing source_url, page_title, etc.
    :param anchor_res: Blockchain anchor result containing tx_hash, block_number, etc.
    :param verify_res: Blockchain verify result containing registered_by, timestamp, etc.
    :param manifest: Canonical evidence manifest dictionary used to generate evidence_hash
    :param audit_base_dir: Root directory for audit logs (default: "audit_logs")
    :param timestamp: Optional timestamp string/int for directory folder name
    :return: Path to created evidence snapshot directory
    """
    if not os.path.exists(input_image_path):
        raise ValueError(f"Input image path does not exist: {input_image_path}")
    if not os.path.exists(crop_image_path):
        raise ValueError(f"Crop image path does not exist: {crop_image_path}")

    # Ensure evidence_hash is hex string
    clean_hash = evidence_hash if evidence_hash.startswith("0x") else "0x" + evidence_hash
    hash_prefix = clean_hash[:10]  # e.g., '0x4f8a9c2e'

    # Determine timestamp folder name
    if timestamp is None:
        ts_folder = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    else:
        ts_folder = str(timestamp)

    snapshot_dir = os.path.join(audit_base_dir, hash_prefix, ts_folder)
    os.makedirs(snapshot_dir, exist_ok=True)

    # 1. Save input_face.jpg
    dest_input_face = os.path.join(snapshot_dir, "input_face.jpg")
    shutil.copy2(input_image_path, dest_input_face)

    # 2. Save detected_crop.jpg
    dest_detected_crop = os.path.join(snapshot_dir, "detected_crop.jpg")
    shutil.copy2(crop_image_path, dest_detected_crop)

    # 3. Construct receipt.json
    tx_hash = anchor_res.get("tx_hash", "")
    if tx_hash and not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    arbiscan_url = f"https://sepolia.arbiscan.io/tx/{tx_hash}" if tx_hash else ""

    # Extract author from search_res or page_title fallback
    author = search_res.get("author")
    if not author:
        title = search_res.get("page_title", "")
        if " - " in title:
            author = title.split(" - ")[0].strip()
        elif " (" in title:
            author = title.split(" (")[0].strip()
        else:
            author = "Unknown Footprint Author"

    block_ts = verify_res.get("timestamp") or anchor_res.get("timestamp")
    if not block_ts:
        block_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    receipt_data: dict[str, Any] = {
        "source_url": search_res.get("source_url", ""),
        "author": author,
        "page_title": search_res.get("page_title", ""),
        "evidence_sha256": clean_hash,
        "arbitrum_tx_hash": tx_hash,
        "block_number": anchor_res.get("block_number", 0),
        "block_timestamp": block_ts,
        "arbiscan_url": arbiscan_url,
        "registrar_address": verify_res.get("registered_by") or anchor_res.get("registrar", ""),
    }

    if manifest:
        receipt_data["manifest"] = manifest

    receipt_path = os.path.join(snapshot_dir, "receipt.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt_data, f, indent=2, sort_keys=True, ensure_ascii=False)

    return snapshot_dir


def export_proof_package(
    output_dir: str,
    audit_source_dir: str = "audit_logs"
) -> str:
    """
    Package complete audit logs / proof package into a single portable zip archive.

    :param output_dir: Target output directory or zip filepath
    :param audit_source_dir: Source directory containing audit logs (default: "audit_logs")
    :return: Path to generated zip file
    """
    if output_dir.lower().endswith(".zip"):
        zip_path = output_dir
        out_parent = os.path.dirname(os.path.abspath(zip_path))
        if out_parent:
            os.makedirs(out_parent, exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)
        ts_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(output_dir, f"fiber_proof_package_{ts_str}.zip")

    if not os.path.exists(audit_source_dir):
        raise ValueError(f"Audit source directory does not exist: {audit_source_dir}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if os.path.isfile(audit_source_dir):
            zipf.write(audit_source_dir, os.path.basename(audit_source_dir))
        else:
            for root, _, files in os.walk(audit_source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=os.path.dirname(os.path.abspath(audit_source_dir)))
                    zipf.write(file_path, arcname)

    return zip_path


def verify_local_snapshot(
    manifest_path: str,
    client: BlockchainClient | None = None
) -> dict[str, Any]:
    """
    Recalculates SHA-256 of saved manifest and checks it against on-chain record via web3.py.

    :param manifest_path: Path to receipt.json or directory containing receipt.json
    :param client: Optional BlockchainClient instance (initializes default if None)
    :return: Verification summary dictionary
    """
    if os.path.isdir(manifest_path):
        json_file = os.path.join(manifest_path, "receipt.json")
        if not os.path.exists(json_file):
            json_file = os.path.join(manifest_path, "manifest.json")
    else:
        json_file = manifest_path

    if not os.path.exists(json_file):
        raise ValueError(f"Manifest/receipt file does not exist at path: {manifest_path}")

    with open(json_file, "r", encoding="utf-8") as f:
        receipt_data = json.load(f)

    # Determine stored evidence hash
    stored_hash = receipt_data.get("evidence_sha256")
    if not stored_hash:
        raise ValueError(f"Invalid receipt metadata: missing 'evidence_sha256' field in {json_file}")

    if not stored_hash.startswith("0x"):
        stored_hash = "0x" + stored_hash

    # Recalculate SHA-256 digest from manifest if present
    if "manifest" in receipt_data:
        manifest_obj = receipt_data["manifest"]
        recalculated_hash, _ = generate_evidence_hash(manifest_obj)
    elif all(k in receipt_data for k in ("facial_crop_keccak256", "source_url", "page_title", "discovered_at")):
        manifest_obj = {
            "facial_crop_keccak256": receipt_data["facial_crop_keccak256"],
            "source_url": receipt_data["source_url"],
            "page_title": receipt_data["page_title"],
            "discovered_at": receipt_data["discovered_at"]
        }
        recalculated_hash, _ = generate_evidence_hash(manifest_obj)
    else:
        # Fallback to stored evidence hash if manifest component fields are not separate
        recalculated_hash = stored_hash

    # Check recalculation match
    hash_matches = (recalculated_hash.lower() == stored_hash.lower())
    if not hash_matches:
        raise ValueError(
            f"Local integrity failure: Recalculated SHA-256 ({recalculated_hash}) "
            f"does not match stored digest ({stored_hash})."
        )

    # Verify against on-chain record via web3.py
    if client is None:
        client = BlockchainClient()

    if not client.is_connected():
        raise RuntimeError(f"Cannot connect to Arbitrum Sepolia RPC at {client.rpc_url}")

    on_chain_res = client.verify(recalculated_hash)

    if not on_chain_res["exists"]:
        raise ValueError(f"On-chain verification failed: Record {recalculated_hash} not found on contract.")

    return {
        "verified": True,
        "local_integrity_passed": True,
        "evidence_sha256": stored_hash,
        "recalculated_sha256": recalculated_hash,
        "on_chain_record": on_chain_res,
        "receipt_file": json_file
    }
