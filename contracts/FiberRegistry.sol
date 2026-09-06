// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FiberRegistry
 * @dev Facial Identification & Blockchain Enforcement Runtime Registry on Arbitrum Sepolia
 */
contract FiberRegistry {
    enum EnforcementStatus { Registered, UnderReview, ViolationConfirmed, Enforced }

    struct FacialRecord {
        bytes32 faceHash;         // Cryptographic SHA-256 / Keccak-256 hash of facial features
        string metadataUri;       // Pointer to match metadata / reverse search report
        uint256 timestamp;        // Block timestamp of registration
        address owner;            // Address registering the record
        EnforcementStatus status; // Current enforcement status
        bool exists;              // Flag checking record existence
    }

    // Mapping from faceHash to FacialRecord
    mapping(bytes32 => FacialRecord) public records;

    // Array of all registered face hashes
    bytes32[] public allFaceHashes;

    // Events
    event RecordRegistered(
        bytes32 indexed faceHash,
        address indexed owner,
        string metadataUri,
        uint256 timestamp
    );
    
    event StatusUpdated(
        bytes32 indexed faceHash,
        EnforcementStatus newStatus,
        uint256 timestamp
    );

    event EnforcementTriggered(
        bytes32 indexed faceHash,
        address indexed enforcer,
        uint256 timestamp
    );

    modifier onlyRecordOwner(bytes32 faceHash) {
        require(records[faceHash].exists, "FiberRegistry: Record does not exist");
        require(records[faceHash].owner == msg.sender, "FiberRegistry: Not record owner");
        _;
    }

    /**
     * @notice Register a new facial hash record on-chain
     * @param faceHash Keccak-256 / SHA-256 digest of facial features
     * @param metadataUri URI pointing to reverse visual search findings or metadata
     */
    function registerRecord(bytes32 faceHash, string memory metadataUri) external {
        require(faceHash != bytes32(0), "FiberRegistry: Invalid face hash");
        require(!records[faceHash].exists, "FiberRegistry: Face record already exists");

        records[faceHash] = FacialRecord({
            faceHash: faceHash,
            metadataUri: metadataUri,
            timestamp: block.timestamp,
            owner: msg.sender,
            status: EnforcementStatus.Registered,
            exists: true
        });

        allFaceHashes.push(faceHash);

        emit RecordRegistered(faceHash, msg.sender, metadataUri, block.timestamp);
    }

    /**
     * @notice Update enforcement status of a face record
     * @param faceHash Hash of the facial record
     * @param newStatus New enforcement status enum
     */
    function updateStatus(bytes32 faceHash, EnforcementStatus newStatus) external onlyRecordOwner(faceHash) {
        records[faceHash].status = newStatus;
        emit StatusUpdated(faceHash, newStatus, block.timestamp);
        
        if (newStatus == EnforcementStatus.Enforced) {
            emit EnforcementTriggered(faceHash, msg.sender, block.timestamp);
        }
    }

    /**
     * @notice Retrieve details of a facial record
     * @param faceHash Hash of the facial record
     */
    function getRecord(bytes32 faceHash) external view returns (
        bytes32 hashVal,
        string memory metadataUri,
        uint256 timestamp,
        address owner,
        EnforcementStatus status,
        bool exists
    ) {
        require(records[faceHash].exists, "FiberRegistry: Record does not exist");
        FacialRecord memory rec = records[faceHash];
        return (rec.faceHash, rec.metadataUri, rec.timestamp, rec.owner, rec.status, rec.exists);
    }

    /**
     * @notice Total number of registered face records
     */
    function totalRecords() external view returns (uint256) {
        return allFaceHashes.length;
    }
}
