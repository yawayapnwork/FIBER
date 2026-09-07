import ssl
import socket
import json
import hashlib
from urllib.parse import urlparse
from typing import Any
import requests

def build_witness_manifest(url: str, response_headers: dict[str, str], cert_sha256: str) -> dict[str, Any]:
    """
    Canonicalizes the network witness tuple into a deterministic JSON string
    and hashes it into bytes32 tlsWitnessRoot.
    """
    manifest = {
        "url": url,
        "response_headers": response_headers,
        "cert_sha256": cert_sha256
    }
    
    canonical_json = json.dumps(
        manifest,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode('utf-8')
    
    tls_witness_root = "0x" + hashlib.sha256(canonical_json).hexdigest()
    manifest["tlsWitnessRoot"] = tls_witness_root
    
    return manifest


def capture_witness_metadata(url: str) -> dict[str, Any]:
    """
    Captures immutable server response headers and TLS certificate fingerprint.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    
    cert_sha256 = ""
    if parsed.scheme == 'https' and hostname:
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_bin = ssock.getpeercert(binary_form=True)
                    if cert_bin:
                        cert_sha256 = hashlib.sha256(cert_bin).hexdigest()
        except Exception:
            # Gracefully fallback if the raw socket handshake fails
            pass
            
    # Stream the headers
    captured_headers = {}
    try:
        resp = requests.get(url, stream=True, timeout=10)
        target_headers = ['ETag', 'Last-Modified', 'Date', 'CF-Ray', 'Content-Length', 'Server']
        
        for h in target_headers:
            if h in resp.headers:
                captured_headers[h] = resp.headers[h]
    except Exception:
        pass
        
    return build_witness_manifest(url, captured_headers, cert_sha256)
