import os
import time
import requests
import concurrent.futures
from urllib.parse import urlparse

from web3 import Web3, HTTPProvider
from rich.console import Console

console = Console()

class FailoverHTTPProvider(HTTPProvider):
    """
    Custom Web3 HTTPProvider with built-in multi-endpoint rotation and rate-limit failover.
    """
    def __init__(self, endpoints: list[str], request_kwargs=None):
        if not endpoints:
            raise ValueError("At least one RPC endpoint must be provided")
            
        self.endpoints = endpoints
        self.active_index = 0
        self._rank_endpoints()
        
        super().__init__(self.endpoints[self.active_index], request_kwargs)
        
    def _rank_endpoints(self):
        """Perform concurrent ping of eth_blockNumber to measure latency."""
        console.print("[dim]Checking Arbitrum Sepolia RPC health & latency...[/dim]")
        
        payload = {"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}
        
        def check_endpoint(url: str):
            start = time.time()
            try:
                # Use 2s timeout for strict health check
                res = requests.post(url, json=payload, timeout=2.0)
                if res.status_code == 200 and "result" in res.json():
                    return url, time.time() - start
            except Exception:
                pass
            return url, float('inf')
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.endpoints)) as executor:
            results = list(executor.map(check_endpoint, self.endpoints))
            
        # Filter and sort
        healthy = [(url, lat) for url, lat in results if lat < float('inf')]
        if not healthy:
            raise ConnectionError("CRITICAL: No healthy RPC endpoints available for Arbitrum Sepolia.")
            
        healthy.sort(key=lambda x: x[1])
        self.endpoints = [x[0] for x in healthy]
        self.active_index = 0
        
        best_url, best_lat = healthy[0]
        domain = urlparse(best_url).netloc
        console.print(f"[bold green][+] RPC Connected:[/bold green] {domain} ({best_lat * 1000:.0f}ms)")
        
    def _rotate_endpoint(self):
        self.active_index = (self.active_index + 1) % len(self.endpoints)
        self.endpoint_uri = self.endpoints[self.active_index]
        domain = urlparse(self.endpoint_uri).netloc
        console.print(f"[bold yellow][!] RPC Failover triggered -> Switched to {domain}[/bold yellow]")
        
    def make_request(self, method, params):
        attempts = 0
        max_attempts = len(self.endpoints)
        
        while attempts < max_attempts:
            try:
                response = super().make_request(method, params)
                
                # Check for RPC-level errors that might indicate rate limiting or node sync issues
                if "error" in response:
                    err_msg = str(response["error"]).lower()
                    if "429" in err_msg or "too many requests" in err_msg or "rate limit" in err_msg:
                        self._rotate_endpoint()
                        attempts += 1
                        continue
                        
                return response
                
            except (requests.exceptions.RequestException, requests.exceptions.Timeout, requests.exceptions.ConnectionError, OSError) as e:
                self._rotate_endpoint()
                attempts += 1
                
        raise ConnectionError(f"All {max_attempts} RPC endpoints failed for {method}")

class RPCGateway(Web3):
    """
    Web3 Wrapper that initializes with a resilient FailoverHTTPProvider.
    """
    def __init__(self, custom_rpc: str | None = None):
        endpoints = []
        
        env_rpc = custom_rpc or os.getenv("ARBITRUM_SEPOLIA_RPC")
        if env_rpc:
            endpoints.append(env_rpc)
            
        endpoints.extend([
            "https://sepolia-rollup.arbitrum.io/rpc",
            "https://arbitrum-sepolia.blockpi.network/v1/rpc/public",
            "https://rpc.ankr.com/arbitrum_sepolia"
        ])
        
        # Deduplicate while preserving order
        seen = set()
        unique_endpoints = []
        for ep in endpoints:
            if ep not in seen:
                seen.add(ep)
                unique_endpoints.append(ep)
                
        provider = FailoverHTTPProvider(unique_endpoints)
        super().__init__(provider)
