"""
QA & Automation Integration Suite for Project F.I.B.E.R.
End-to-End Mocked Pipeline Test covering all 5 steps offline.
"""

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from src.blockchain import BlockchainClient
from src.crypto import FiberCrypto, generate_evidence_hash
from src.search import CopyseekerSearchEngine
from src.vision import extract_face


class TestEndToEndPipeline:
    @pytest.fixture(autouse=True)
    def setup_files(self, tmp_path):
        self.tmp_dir = tmp_path
        self.input_file = str(self.tmp_dir / "target_person.jpg")
        self.crop_file = str(self.tmp_dir / "cropped_face.jpg")

        img = Image.new("RGB", (250, 250), color=(150, 150, 150))
        img.save(self.input_file)
        yield
        for f in [self.input_file, self.crop_file, "cropped_face.jpg", "temp_crop.jpg"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    @patch("src.vision.MTCNN")
    @patch("src.search.requests.post")
    @patch("src.blockchain.Web3")
    def test_full_5_step_pipeline_offline(
        self,
        mock_web3_cls,
        mock_http_post,
        mock_mtcnn_cls
    ):
        mock_mtcnn_inst = MagicMock()
        mock_mtcnn_inst.detect.return_value = (
            np.array([[40.0, 40.0, 180.0, 180.0]]),
            np.array([0.96])
        )
        mock_mtcnn_cls.return_value = mock_mtcnn_inst

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = {
            "visual_matches": [
                {
                    "url": "https://twitter.com/target/status/12345",
                    "title": "Target Social Media Post",
                    "matched_image_url": "https://twitter.com/target/img.jpg"
                }
            ]
        }
        mock_http_post.return_value = mock_search_resp

        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 421614
        mock_w3.eth.get_transaction_count.return_value = 10
        mock_w3.eth.gas_price = 100000000

        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "chainId": 421614,
            "gas": 300000,
            "gasPrice": 100000000,
            "nonce": 10,
            "from": "0x1234567890123456789012345678901234567890"
        }
        mock_contract.functions.anchorEvidence.return_value = mock_func

        evidence_hash_bytes = b"\x55" * 32
        mock_record_tuple = (
            evidence_hash_bytes,
            "https://twitter.com/target/status/12345",
            1757149500,
            "0x1234567890123456789012345678901234567890"
        )
        mock_contract.functions.verifyEvidence.return_value.call.return_value = (True, mock_record_tuple)
        mock_w3.eth.contract.return_value = mock_contract

        mock_signed_tx = MagicMock()
        mock_signed_tx.rawTransaction = b"signed_raw_tx_bytes"
        mock_w3.eth.account.sign_transaction.return_value = mock_signed_tx
        mock_w3.eth.send_raw_transaction.return_value = b"\x55" * 32

        mock_receipt = MagicMock()
        mock_receipt.transactionHash = b"\x55" * 32
        mock_receipt.blockNumber = 14920381
        mock_receipt.status = 1
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_web3_cls.return_value = mock_w3

        crop_path = extract_face(self.input_file, output_path=self.crop_file)
        assert os.path.exists(crop_path)

        search_engine = CopyseekerSearchEngine(api_key="mock_key")
        search_res = search_engine.search(crop_path)
        assert search_res["source_url"] == "https://twitter.com/target/status/12345"

        crop_img = Image.open(crop_path)
        crop_keccak = FiberCrypto.hash_pil_image(crop_img)
        manifest = {
            "facial_crop_keccak256": "0x" + crop_keccak.hex(),
            "source_url": search_res["source_url"],
            "page_title": search_res["page_title"],
            "discovered_at": search_res["discovered_at"]
        }
        hex_hash, bytes_hash = generate_evidence_hash(manifest)
        assert hex_hash.startswith("0x")
        assert len(bytes_hash) == 32

        client = BlockchainClient(
            rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
            private_key="0x" + "11" * 32,
            contract_address="0x" + "22" * 20
        )
        client.w3 = mock_w3
        client.contract = mock_contract
        client.account = MagicMock(address="0x1234567890123456789012345678901234567890")

        anchor_res = client.anchor(hex_hash, search_res["source_url"])
        assert anchor_res["block_number"] == 14920381

        verify_res = client.verify(hex_hash)
        assert verify_res["exists"] is True
        assert verify_res["source_url"] == "https://twitter.com/target/status/12345"
