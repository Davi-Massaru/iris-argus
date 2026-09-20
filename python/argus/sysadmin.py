"""Single HTTP boundary for the official SysAdmin v2 contract."""
import requests
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://127.0.0.1:52773/api/admin"


class SysAdminError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class SysAdminClient:
    def __init__(self, authorization, transport=None):
        self.authorization = authorization
        self.transport = transport or requests.Session()
        if hasattr(self.transport, "trust_env"):
            self.transport.trust_env = False

    def request(self, method, path, *, params=None, data=None):
        if not path.startswith(("/v2/", "/info", "/login", "/refresh")) or ".." in path:
            raise ValueError("Invalid SysAdmin path")
        try:
            response = self.transport.request(
                method, BASE_URL + path, params=params, json=data,
                headers={"Authorization": self.authorization, "Accept": "application/json"},
                timeout=(3, 15), allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise SysAdminError(503, "IRIS management API unavailable or timed out") from exc
        if response.status_code >= 300:
            messages = {400: "Invalid management request", 401: "Authentication required",
                        403: "Permission denied", 404: "Resource no longer exists",
                        409: "Operation conflicts with current IRIS state"}
            raise SysAdminError(response.status_code, messages.get(response.status_code, "IRIS management request failed"))
        try:
            body = response.json()
        except ValueError as exc:
            raise SysAdminError(502, "Invalid response from IRIS management API") from exc
        if isinstance(body, dict) and body.get("status", {}).get("errors"):
            raise SysAdminError(502, "IRIS reported an unsuccessful management operation")
        if response.status_code == 202:
            task_id = parse_qs(urlparse(response.headers.get("Location", "")).query).get("id", [None])[0]
            if not task_id:
                raise SysAdminError(502, "IRIS did not provide an asynchronous task identifier")
            return {"pending_id": task_id}
        return body.get("result", body) if isinstance(body, dict) else body

    def get(self, path, **params):
        return self.request("GET", path, params=params)

    def close(self):
        self.transport.close()
