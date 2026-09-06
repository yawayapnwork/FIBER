"""
F.I.B.E.R. Edge Case & Pipeline Boundary Test Suite
Validates edge cases before final demonstration:
1. Low Resolution / Occluded Face -> MTCNN raises ValueError("No valid human face detected")
2. Search Disconnect & Zero Matches -> Exit code 1 with remediation guidance
3. Duplicate Blockchain Anchoring -> Graceful catch of EVM revert error ("Evidence already registered")
4. Gas Spike / Insufficient Balance -> Directs user to Arbitrum Sepolia faucet
"""

import sys
import os

# Add root directory to sys.path for src imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile
import unittest.mock as mock
from PIL import Image, ImageFilter
import pytest

from src.vision import extract_face_info
from src.search import CopyseekerSearchEngine, NoMatchesFoundError
from src.blockchain import BlockchainClient
import main


def test_scenario_1_occluded_or_low_res_face():
    """Scenario 1: Low Resolution / Heavy Blur / Featureless image face detection failure."""
    print("\n[Running Scenario 1: Low Resolution / Occluded Face]")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        # Create heavily blurred / featureless solid image
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img = img.filter(ImageFilter.GaussianBlur(radius=10))
        img.save(tmp_path)

    try:
        with pytest.raises(ValueError) as exc_info:
            extract_face_info(tmp_path)
        assert "No valid human face detected" in str(exc_info.value)
        print("[+] Scenario 1 PASSED: MTCNN correctly rejected occluded/blurry image with ValueError('No valid human face detected')")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_scenario_2_search_disconnect_zero_matches():
    """Scenario 2: Empty search response / disconnect in strict mode outputs remediation guidance and exits code 1."""
    print("\n[Running Scenario 2: Search Disconnect & Zero Matches]")
    engine = CopyseekerSearchEngine(api_key="mock_key")
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"visual_matches": []}

    # Validate engine.search raises NoMatchesFoundError on empty response
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        face_img = Image.new("RGB", (200, 200), color=(200, 200, 200))
        face_img.save(tmp.name)
        tmp_path = tmp.name

    try:
        with mock.patch("requests.post", return_value=mock_resp):
            with pytest.raises(NoMatchesFoundError) as exc_info:
                engine.search(tmp_path)
            assert "No matching visual results discovered" in str(exc_info.value)

        # Validate main CLI exit code 1 and remediation message output under --strict-search
        dummy_crop = "cropped_face.jpg"
        with open(dummy_crop, "wb") as f:
            f.write(b"dummy_crop_bytes")

        try:
            with mock.patch.dict(os.environ, {"RAPIDAPI_KEY": "mock_key_for_testing"}):
                with mock.patch("main.extract_face_info", return_value={"output_path": dummy_crop, "width": 100, "height": 100, "aspect_ratio": 1.0, "confidence": 0.95, "box": [0, 0, 100, 100]}):
                    with mock.patch("requests.post", return_value=mock_resp):
                        with pytest.raises(SystemExit) as sys_exit:
                            main.run_scan_pipeline(tmp_path, strict_search=True)
                        assert sys_exit.value.code == 1
                        print("[+] Scenario 2 PASSED: Zero match search disconnect terminated with Exit Code 1 and remediation guidance.")
        finally:
            if os.path.exists(dummy_crop):
                os.remove(dummy_crop)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_scenario_3_duplicate_blockchain_anchoring():
    """Scenario 3: Duplicate evidence hash anchoring catches EVM revert ('Evidence already registered')."""
    print("\n[Running Scenario 3: Duplicate Blockchain Anchoring]")
    client = BlockchainClient(
        rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
        private_key="0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        contract_address="0x1234567890123456789012345678901234567890"
    )

    dummy_hash = "0x" + "aa" * 32
    dummy_url = "https://x.com/user/status/123"

    with mock.patch.object(client.w3.eth, "get_balance", return_value=10**18):
        mock_contract = mock.MagicMock()
        mock_contract.functions.anchorEvidence.side_effect = Exception("execution reverted: Evidence already registered")
        client.contract = mock_contract

        with pytest.raises(RuntimeError) as exc_info:
            client.anchor(dummy_hash, dummy_url)

        assert "Evidence already registered" in str(exc_info.value)
        print("[+] Scenario 3 PASSED: Duplicate anchoring caught EVM revert error ('Evidence already registered') gracefully.")


def test_scenario_4_insufficient_gas_balance():
    """Scenario 4: 0 testnet ETH balance directs user to Arbitrum Sepolia faucet."""
    print("\n[Running Scenario 4: Gas Spike / Insufficient Balance]")
    client = BlockchainClient(
        rpc_url="https://sepolia-rollup.arbitrum.io/rpc",
        private_key="0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        contract_address="0x1234567890123456789012345678901234567890"
    )

    dummy_hash = "0x" + "bb" * 32
    dummy_url = "https://x.com/user/status/456"

    # Simulate 0 testnet ETH balance
    with mock.patch.object(client.w3.eth, "get_balance", return_value=0):
        with pytest.raises(ValueError) as exc_info:
            client.anchor(dummy_hash, dummy_url)

        err_msg = str(exc_info.value)
        assert "Insufficient testnet ETH balance" in err_msg
        assert "https://faucet.quicknode.com/arbitrum/sepolia" in err_msg
        print("[+] Scenario 4 PASSED: 0 testnet ETH caught with human-readable prompt linking to Arbitrum Sepolia faucet.")


def main_runner():
    print("=" * 70)
    print("F.I.B.E.R. Edge Case Test Suite")
    print("Validating boundary conditions across Vision, Search, Contracts & Gas")
    print("=" * 70)

    test_scenario_1_occluded_or_low_res_face()
    test_scenario_2_search_disconnect_zero_matches()
    test_scenario_3_duplicate_blockchain_anchoring()
    test_scenario_4_insufficient_gas_balance()

    print("\n" + "=" * 70)
    print("ALL 4 EDGE CASE SCENARIOS VERIFIED SUCCESSFULLY (Exit Code 0)")
    print("=" * 70)


if __name__ == "__main__":
    main_runner()
