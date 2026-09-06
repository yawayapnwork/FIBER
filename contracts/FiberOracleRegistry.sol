// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FiberOracleRegistry
 * @dev Gas-optimized oracle registry for F.I.B.E.R. supporting EIP-712/EIP-191 signatures.
 */
contract FiberOracleRegistry {
    error AlreadyAttested(bytes32 structHash);
    error InvalidSignature();
    error InvalidRegistrar();

    address public immutable registrar;

    // Guard against signature replay attacks
    mapping(bytes32 => bool) public attested;

    event AttestationRecorded(bytes32 indexed structHash, address indexed submitter);

    constructor(address _registrar) {
        registrar = _registrar;
    }

    /**
     * @notice Submit an off-chain attestation securely.
     * @param structHash The message digest to verify.
     * @param v ECDSA recovery id.
     * @param r ECDSA signature output.
     * @param s ECDSA signature output.
     */
    function attest(bytes32 structHash, uint8 v, bytes32 r, bytes32 s) external {
        // EVM Guardrail: Signature Replay Protection
        if (attested[structHash]) {
            revert AlreadyAttested(structHash);
        }

        address recovered = ecrecover(structHash, v, r, s);
        
        // EVM Guardrail: Validate non-zero ecrecover returns
        if (recovered == address(0)) {
            revert InvalidSignature();
        }

        // EVM Guardrail: Validate recovered address against trusted registrar
        if (recovered != registrar) {
            revert InvalidRegistrar();
        }

        // Mark as attested to prevent replays
        attested[structHash] = true;

        emit AttestationRecorded(structHash, msg.sender);
    }
}
