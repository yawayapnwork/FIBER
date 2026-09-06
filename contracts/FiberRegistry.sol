// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FiberRegistry
 * @dev Gas-optimized registry for Facial Identification & Blockchain Enforcement Runtime (F.I.B.E.R.) on Arbitrum Sepolia
 */
contract FiberRegistry {
    // Custom errors for gas optimization
    error EvidenceAlreadyAnchored(bytes32 evidenceHash);
    error InvalidEvidenceHash();

    // Struct representing anchored facial evidence
    struct Evidence {
        bytes32 evidenceHash;   // SHA-256 or Keccak-256 hash of facial feature / crop
        string sourceUrl;       // Reverse visual search source match URL or metadata link
        uint256 timestamp;      // Block timestamp when evidence was anchored
        address registeredBy;   // Address of the account registering the evidence
    }

    // Mapping from evidence hash to Evidence record
    mapping(bytes32 => Evidence) public records;

    // Event emitted when new evidence is anchored on-chain
    event EvidenceAnchored(
        bytes32 indexed evidenceHash,
        string sourceUrl,
        uint256 timestamp,
        address indexed registrar
    );

    /**
     * @notice Anchor a facial identification evidence record on-chain
     * @dev Reverts with InvalidEvidenceHash if zero hash, or EvidenceAlreadyAnchored if already exists
     * @param _evidenceHash Keccak-256 or SHA-256 digest of facial identification
     * @param _sourceUrl URL / URI of reverse search match or evidence payload
     */
    function anchorEvidence(bytes32 _evidenceHash, string calldata _sourceUrl) external {
        if (_evidenceHash == bytes32(0)) {
            revert InvalidEvidenceHash();
        }
        if (records[_evidenceHash].timestamp != 0) {
            revert EvidenceAlreadyAnchored(_evidenceHash);
        }

        records[_evidenceHash] = Evidence({
            evidenceHash: _evidenceHash,
            sourceUrl: _sourceUrl,
            timestamp: block.timestamp,
            registeredBy: msg.sender
        });

        emit EvidenceAnchored(_evidenceHash, _sourceUrl, block.timestamp, msg.sender);
    }

    /**
     * @notice Verify whether an evidence hash exists on-chain and retrieve its record
     * @param _evidenceHash Evidence hash to query
     * @return exists Boolean indicating whether record exists
     * @return record The Evidence struct stored on-chain
     */
    function verifyEvidence(bytes32 _evidenceHash) external view returns (bool exists, Evidence memory record) {
        Evidence memory rec = records[_evidenceHash];
        exists = (rec.timestamp != 0);
        record = rec;
    }
}
