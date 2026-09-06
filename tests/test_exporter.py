"""
Unit & Integration Test Suite for F.I.B.E.R. Data Provenance Exporter Module
Tests automated evidence directory creation, zip proof-package exporting,
and local manifest recalculation & on-chain state verification.
"""

import json
import os
import zipfile
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.crypto import generate_evidence_hash
from src.exporter import (
    create_evidence_snapshot,
    export_proof_package,
    verify_local_snapshot
)


class TestExporterModule:
    @pytest.fixture(autouse=True)
    def setup_files(self, tmp_path):
        self.tmp_dir = tmp_path
        self.input_image = str(self.tmp_dir / "input_test.jpg")
        self.crop_image = str(self.tmp_dir / "crop_test.jpg")
        self.audit_base = str(self.tmp_dir / "audit_logs")
        self.export_dir = str(self.tmp_dir / "reports")

        # Create dummy JPEG files
        img = Image.new("RGB", (200, 200), color=(100, 100, 200))
        img.save(self.input_image)

        crop = Image.new("RGB", (100, 100), color=(200, 100, 100))
        crop.save(self.crop_image)

        self.manifest = {
            "facial_crop_keccak256": "0x11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            "source_url": "https://twitter.com/target_user/status/9876543210",
            "page_title": "Target User - Unauthorized Footprint (Twitter / X)",
            "discovered_at": 1757149500
        }
        self.evidence_hash, _ = generate_evidence_hash(self.manifest)

        self.search_res = {
            "source_url": "https://twitter.com/target_user/status/9876543210",
            "page_title": "Target User - Unauthorized Footprint (Twitter / X)",
            "matched_image_url": "https://twitter.com/target_user/img.jpg",
            "discovered_at": 1757149500
        }
        self.anchor_res = {
            "tx_hash": "0xa1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
            "block_number": 14920381,
            "explorer_url": "https://sepolia.arbiscan.io/tx/0xa1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef",
            "gas_used": 125000,
            "status": 1
        }
        self.verify_res = {
            "exists": True,
            "evidence_hash": self.evidence_hash,
            "source_url": "https://twitter.com/target_user/status/9876543210",
            "timestamp": 1757149500,
            "registered_by": "0x1234567890123456789012345678901234567890",
            "contract_address": "0x9876543210987654321098765432109876543210",
            "explorer_url": "https://sepolia.arbiscan.io/address/0x9876543210987654321098765432109876543210"
        }

    def test_create_evidence_snapshot_structure_and_artifacts(self):
        snapshot_dir = create_evidence_snapshot(
            evidence_hash=self.evidence_hash,
            input_image_path=self.input_image,
            crop_image_path=self.crop_image,
            search_res=self.search_res,
            anchor_res=self.anchor_res,
            verify_res=self.verify_res,
            manifest=self.manifest,
            audit_base_dir=self.audit_base,
            timestamp="20260906_190800"
        )

        assert os.path.exists(snapshot_dir)
        hash_prefix = self.evidence_hash[:10]
        assert snapshot_dir.replace("\\", "/").endswith(f"{hash_prefix}/20260906_190800")

        # Verify three artifacts
        input_face_path = os.path.join(snapshot_dir, "input_face.jpg")
        detected_crop_path = os.path.join(snapshot_dir, "detected_crop.jpg")
        receipt_path = os.path.join(snapshot_dir, "receipt.json")

        assert os.path.exists(input_face_path)
        assert os.path.exists(detected_crop_path)
        assert os.path.exists(receipt_path)

        # Inspect receipt JSON contents
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt_data = json.load(f)

        assert receipt_data["source_url"] == self.search_res["source_url"]
        assert receipt_data["author"] == "Target User"
        assert receipt_data["page_title"] == self.search_res["page_title"]
        assert receipt_data["evidence_sha256"] == self.evidence_hash
        assert receipt_data["arbitrum_tx_hash"] == self.anchor_res["tx_hash"]
        assert receipt_data["block_number"] == 14920381
        assert receipt_data["block_timestamp"] == 1757149500
        assert receipt_data["arbiscan_url"] == f"https://sepolia.arbiscan.io/tx/{self.anchor_res['tx_hash']}"
        assert receipt_data["registrar_address"] == self.verify_res["registered_by"]
        assert receipt_data["manifest"] == self.manifest

    def test_export_proof_package_zip_archive(self):
        snapshot_dir = create_evidence_snapshot(
            evidence_hash=self.evidence_hash,
            input_image_path=self.input_image,
            crop_image_path=self.crop_image,
            search_res=self.search_res,
            anchor_res=self.anchor_res,
            verify_res=self.verify_res,
            manifest=self.manifest,
            audit_base_dir=self.audit_base,
            timestamp="20260906_190800"
        )

        zip_file = export_proof_package(self.export_dir, audit_source_dir=self.audit_base)
        assert os.path.exists(zip_file)
        assert zip_file.endswith(".zip")

        # Check zip archive entries
        with zipfile.ZipFile(zip_file, "r") as zf:
            namelist = zf.namelist()
            assert any("input_face.jpg" in name for name in namelist)
            assert any("detected_crop.jpg" in name for name in namelist)
            assert any("receipt.json" in name for name in namelist)

    def test_verify_local_snapshot_success(self):
        snapshot_dir = create_evidence_snapshot(
            evidence_hash=self.evidence_hash,
            input_image_path=self.input_image,
            crop_image_path=self.crop_image,
            search_res=self.search_res,
            anchor_res=self.anchor_res,
            verify_res=self.verify_res,
            manifest=self.manifest,
            audit_base_dir=self.audit_base,
            timestamp="20260906_190800"
        )

        # Mock BlockchainClient
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.verify.return_value = {
            "exists": True,
            "evidence_hash": self.evidence_hash,
            "source_url": self.search_res["source_url"],
            "timestamp": 1757149500,
            "registered_by": self.verify_res["registered_by"],
            "contract_address": "0x9876543210987654321098765432109876543210",
            "explorer_url": "https://sepolia.arbiscan.io/address/0x9876543210987654321098765432109876543210"
        }

        res = verify_local_snapshot(snapshot_dir, client=mock_client)
        assert res["verified"] is True
        assert res["local_integrity_passed"] is True
        assert res["on_chain_record"]["exists"] is True

    def test_verify_local_snapshot_tampered_manifest_fails(self):
        snapshot_dir = create_evidence_snapshot(
            evidence_hash=self.evidence_hash,
            input_image_path=self.input_image,
            crop_image_path=self.crop_image,
            search_res=self.search_res,
            anchor_res=self.anchor_res,
            verify_res=self.verify_res,
            manifest=self.manifest,
            audit_base_dir=self.audit_base,
            timestamp="20260906_190800"
        )

        receipt_path = os.path.join(snapshot_dir, "receipt.json")
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt_data = json.load(f)

        # Tamper manifest URL
        receipt_data["manifest"]["source_url"] = "https://tampered.url/hacked"

        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt_data, f, indent=2)

        mock_client = MagicMock()
        mock_client.is_connected.return_value = True

        with pytest.raises(ValueError, match="Local integrity failure"):
            verify_local_snapshot(snapshot_dir, client=mock_client)
