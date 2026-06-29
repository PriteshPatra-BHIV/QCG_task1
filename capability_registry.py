"""
capability_registry.py - Dynamic Capability Registry and Discovery Client.
Allows runtime services to register their capabilities and discover downstream endpoints.
"""

import json
import logging
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from typing import Dict, Any, List, Optional

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qcg.capability_registry")

# In-memory database of registered capabilities
_registry_db: Dict[str, Dict[str, Any]] = {}
_registry_lock = threading.Lock()

def validate_capability_payload(payload: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate capability payload against the core fields of capability_registry_schema.json.
    Ensures structural correctness without requiring external jsonschema package.
    """
    required_keys = [
        "capability_id", "capability_name", "owner", "version", "status", 
        "scope", "dependencies", "attachment_rules", "authority_limits", 
        "inputs", "outputs", "consumers", "documentation_reference"
    ]
    for key in required_keys:
        if key not in payload:
            return False, f"Missing required key: {key}"
            
    # Validate nested structures
    owner = payload["owner"]
    if not isinstance(owner, dict) or "team" not in owner or "contact" not in owner:
        return False, "Invalid 'owner' structure: must contain 'team' and 'contact'."
        
    attachment = payload["attachment_rules"]
    if not isinstance(attachment, dict) or "attachment_type" not in attachment or "protocol" not in attachment:
        return False, "Invalid 'attachment_rules' structure: must contain 'attachment_type' and 'protocol'."
        
    auth = payload["authority_limits"]
    if not isinstance(auth, dict) or "owns" not in auth or "does_not_own" not in auth:
        return False, "Invalid 'authority_limits' structure: must contain 'owns' and 'does_not_own'."
        
    return True, ""

class CapabilityRegistryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress logging to stdout

    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        if self.path == "/capabilities":
            with _registry_lock:
                self._set_headers(200)
                self.wfile.write(json.dumps(list(_registry_db.values())).encode("utf-8"))
        elif self.path.startswith("/capabilities/"):
            cap_id = self.path.split("/")[-1]
            with _registry_lock:
                if cap_id in _registry_db:
                    self._set_headers(200)
                    self.wfile.write(json.dumps(_registry_db[cap_id]).encode("utf-8"))
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"error": f"Capability {cap_id} not found"}).encode("utf-8"))
        elif self.path.startswith("/discover/"):
            cap_name = self.path.split("/")[-1]
            found = None
            with _registry_lock:
                for cap in _registry_db.values():
                    if cap["capability_name"].upper() == cap_name.upper():
                        found = cap
                        break
            if found:
                self._set_headers(200)
                self.wfile.write(json.dumps(found).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Capability with name {cap_name} not found"}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self):
        if self.path == "/register":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Empty body"}).encode("utf-8"))
                return
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode("utf-8"))
                return

            valid, err_msg = validate_capability_payload(payload)
            if not valid:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": f"Schema Validation Failure: {err_msg}"}).encode("utf-8"))
                return

            cap_id = payload["capability_id"]
            with _registry_lock:
                _registry_db[cap_id] = payload
            logger.info(f"Registered capability '{payload['capability_name']}' version {payload['version']} (ID: {cap_id})")
            
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "REGISTERED", "capability_id": cap_id}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

# -- Registry Server Control --------------------------------------------------

class CapabilityRegistryServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        self.server = HTTPServer((self.host, self.port), CapabilityRegistryHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Capability Registry Server started on http://{self.host}:{self.port}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        logger.info("Capability Registry Server stopped")

# -- Registry Client Helper ----------------------------------------------------

class CapabilityRegistryClient:
    def __init__(self, registry_url: str = "http://127.0.0.1:9000"):
        self.registry_url = registry_url

    def register(self, capability_data: Dict[str, Any]) -> bool:
        """Register a service capability with the centralized registry."""
        url = f"{self.registry_url}/register"
        data = json.dumps(capability_data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body.get("status") == "REGISTERED"
        except Exception as e:
            logger.error(f"Failed to register capability: {e}")
            return False

    def discover(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Query the registry to resolve a capability's metadata and endpoint."""
        url = f"{self.registry_url}/discover/{capability_name}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to discover capability '{capability_name}': {e}")
            return None
