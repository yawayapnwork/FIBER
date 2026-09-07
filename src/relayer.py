import os
import json
from eth_account import Account
from eth_account.messages import encode_typed_data
from src.blockchain import BlockchainClient

# EIP-712 Domain for OpenZeppelin MinimalForwarder
DOMAIN_NAME = "MinimalForwarder"
DOMAIN_VERSION = "0.0.1"

MINIMAL_FORWARDER_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "from", "type": "address"}],
        "name": "getNonce",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "address", "name": "from", "type": "address"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "uint256", "name": "gas", "type": "uint256"},
                    {"internalType": "uint256", "name": "nonce", "type": "uint256"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"}
                ],
                "internalType": "struct MinimalForwarder.ForwardRequest",
                "name": "req",
                "type": "tuple"
            },
            {"internalType": "bytes", "name": "signature", "type": "bytes"}
        ],
        "name": "execute",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"},
            {"internalType": "bytes", "name": "", "type": "bytes"}
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

def execute_meta_tx(
    blockchain_client: BlockchainClient,
    forwarder_address: str,
    target_address: str,
    encoded_data: bytes,
    user_private_key: str,
    relayer_private_key: str
) -> str:
    """
    Constructs a meta-transaction, signs it with the user_private_key (gasless),
    and executes it via the forwarder using the relayer_private_key.
    
    Returns the transaction hash.
    """
    w3 = blockchain_client.w3
    user_account = Account.from_key(user_private_key)
    relayer_account = Account.from_key(relayer_private_key)
    
    forwarder_contract = w3.eth.contract(
        address=w3.to_checksum_address(forwarder_address),
        abi=MINIMAL_FORWARDER_ABI
    )
    
    # 1. Get user's nonce on the forwarder
    nonce = forwarder_contract.functions.getNonce(user_account.address).call()
    
    # 2. Prepare ForwardRequest
    req = {
        "from": user_account.address,
        "to": target_address,
        "value": 0,
        "gas": 1500000,  # Ensure there is enough gas for the destination call
        "nonce": nonce,
        "data": encoded_data
    }
    
    # 3. Create EIP-712 structured data
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"}
            ],
            "ForwardRequest": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "gas", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "data", "type": "bytes"}
            ]
        },
        "primaryType": "ForwardRequest",
        "domain": {
            "name": DOMAIN_NAME,
            "version": DOMAIN_VERSION,
            "chainId": w3.eth.chain_id,
            "verifyingContract": forwarder_address
        },
        "message": req
    }
    
    # 4. Sign typed data with user key
    structured_msg = encode_typed_data(full_message=typed_data)
    signed_message = Account.sign_message(structured_msg, private_key=user_private_key)
    signature = signed_message.signature
    
    # 5. Broadcast execute() transaction via relayer
    req_tuple = (req["from"], req["to"], req["value"], req["gas"], req["nonce"], req["data"])
    
    try:
        relayer_gas = forwarder_contract.functions.execute(req_tuple, signature).estimate_gas({'from': relayer_account.address})
        gas_limit = int(relayer_gas * 1.3)
    except Exception as e:
        gas_limit = 3000000
        
    relayer_nonce = w3.eth.get_transaction_count(relayer_account.address)
    
    try:
        gas_price = int(w3.eth.gas_price * 1.1)
    except Exception:
        gas_price = w3.to_wei(0.1, 'gwei')
    
    tx = forwarder_contract.functions.execute(req_tuple, signature).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': relayer_nonce,
        'from': relayer_account.address
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=relayer_private_key)
    
    try:
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    except Exception as e:
        raise RuntimeError(f"Relayer transaction failed: {e}") from e
    
    # Wait for block confirmation receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)
    receipt_tx_hash = receipt.transactionHash.hex()
    
    if not receipt_tx_hash.startswith("0x"):
        receipt_tx_hash = "0x" + receipt_tx_hash
        
    if receipt.status == 0:
        raise RuntimeError(f"Meta-transaction reverted on-chain! Tx Hash: {receipt_tx_hash}")
        
    return receipt_tx_hash
