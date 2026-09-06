// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FiberMerkleRegistry
 * @dev Registry for F.I.B.E.R. storing 3-leaf Merkle Tree evidence commitments on Arbitrum Sepolia
 */
contract FiberMerkleRegistry {
    // Custom errors for gas optimization
    error RootAlreadyAnchored(bytes32 _merkleRoot);
    error InvalidMerkleRoot();

    // Struct representing an anchored Merkle root commitment
    struct Record {
        bytes32 merkleRoot;     // 3-leaf Merkle Root digest
        string sourceUrl;       // Metadata URI or reverse search source match URL
        uint256 timestamp;      // Block timestamp when anchored
        address registrar;      // Address of the account registering the root
        bool indexingDelayBypass; // Flag for manual URL override due to search indexing lag
    }

    // Mapping from Merkle root to its anchoring Record
    mapping(bytes32 => Record) public records;

    // Event emitted when a new Merkle root is anchored on-chain
    event MerkleRootAnchored(
        bytes32 indexed merkleRoot,
        string sourceUrl,
        uint256 timestamp,
        address indexed registrar,
        bool indexingDelayBypass
    );

    /**
     * @notice Anchor a 3-leaf Merkle root evidence record on-chain
     * @dev Reverts with InvalidMerkleRoot if zero hash, or RootAlreadyAnchored if already exists
     * @param _merkleRoot SHA-256 digest of the 3-leaf Merkle Root
     * @param _sourceUrl URL / URI of reverse search match or evidence payload
     * @param _bypass Flag indicating if the indexing delay bypass was manually invoked
     */
    function anchorRoot(bytes32 _merkleRoot, string calldata _sourceUrl, bool _bypass) external {
        if (_merkleRoot == bytes32(0)) {
            revert InvalidMerkleRoot();
        }
        if (records[_merkleRoot].timestamp != 0) {
            revert RootAlreadyAnchored(_merkleRoot);
        }

        records[_merkleRoot] = Record({
            merkleRoot: _merkleRoot,
            sourceUrl: _sourceUrl,
            timestamp: block.timestamp,
            registrar: msg.sender,
            indexingDelayBypass: _bypass
        });

        emit MerkleRootAnchored(_merkleRoot, _sourceUrl, block.timestamp, msg.sender, _bypass);
    }

    /**
     * @notice Verify whether a Merkle root exists on-chain and retrieve its record
     * @param _merkleRoot Merkle root to query
     * @return exists Boolean indicating whether record exists
     * @return record The Record struct stored on-chain
     */
    function verifyRoot(bytes32 _merkleRoot) external view returns (bool exists, Record memory record) {
        Record memory rec = records[_merkleRoot];
        exists = (rec.timestamp != 0);
        record = rec;
    }
}
