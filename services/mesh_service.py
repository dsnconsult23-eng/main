import os
import time
import logging
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)


class MeshServiceError(Exception):
    def __init__(self, public_message: str, status_code: int = 502):
        super().__init__(public_message)
        self.public_message = public_message
        self.status_code = status_code


class MeshService:
    def __init__(self):
        self.base_url = os.getenv("MESH_BASE_URL", "https://api.mesh.complyadvantage.com").rstrip("/")
        self.username = os.getenv("MESH_USERNAME", "")
        self.password = os.getenv("MESH_PASSWORD", "")
        self.realm = os.getenv("MESH_REALM", "")

        self._token: Optional[str] = None
        self._expires_at: float = 0

    def _validate_credentials(self):
        if not self.username or not self.password or not self.realm:
            raise MeshServiceError(
                "Mesh credentials are missing. Please set MESH_USERNAME, MESH_PASSWORD, and MESH_REALM."
                ,
                status_code=500
            )

    def get_token(self, force_refresh: bool = False) -> str:
        self._validate_credentials()

        now = time.time()
        if (
            not force_refresh
            and self._token
            and self._expires_at > now + 60
        ):
            return self._token

        payload = {
            "username": self.username,
            "password": self.password,
            "realm": self.realm
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        logger.info("Requesting Mesh token...")
        try:
            response = requests.post(
                f"{self.base_url}/v2/token",
                json=payload,
                headers=headers,
                timeout=60
            )
        except requests.RequestException as e:
            logger.exception("Mesh token request connection error")
            raise MeshServiceError("Mesh token request failed.") from e

        if not response.ok:
            logger.error("Mesh token request failed: %s", response.text)
            raise MeshServiceError("Mesh token request failed.")

        try:
            data = response.json()
        except ValueError as e:
            logger.exception("Mesh token response is not valid JSON")
            raise MeshServiceError("Mesh token response is invalid.") from e
        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 86400))

        if not access_token:
            raise MeshServiceError("Mesh token response does not contain access token.")

        self._token = access_token
        self._expires_at = now + expires_in

        logger.info("Mesh token acquired successfully.")
        return self._token

    def _headers(self) -> Dict[str, str]:
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "Content-Type": "application/json"
        }

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None
    ) -> Any:
        url = f"{self.base_url}{path}"
        logger.info("Calling Mesh API: %s %s", method.upper(), url)

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=120
            )
        except requests.RequestException as e:
            logger.exception("Mesh API connection error for %s", url)
            raise MeshServiceError("Mesh API request failed.") from e

        if response.status_code == 401:
            logger.warning("Mesh returned 401, refreshing token and retrying.")
            self.get_token(force_refresh=True)

            try:
                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                    timeout=120
                )
            except requests.RequestException as e:
                logger.exception("Mesh API retry connection error for %s", url)
                raise MeshServiceError("Mesh API request failed after token refresh.") from e

        if not response.ok:
            logger.error("Mesh API error [%s]: %s", response.status_code, response.text)
            if response.status_code in (400, 404, 422):
                raise MeshServiceError("Mesh request was rejected.", status_code=response.status_code)
            if response.status_code == 401:
                raise MeshServiceError("Mesh authentication failed.", status_code=502)
            if response.status_code == 403:
                raise MeshServiceError("Mesh access denied.", status_code=502)
            raise MeshServiceError("Mesh API error.", status_code=502)

        if response.text:
            try:
                return response.json()
            except ValueError as e:
                logger.exception("Mesh API response is not valid JSON for %s", url)
                raise MeshServiceError("Mesh API returned invalid JSON.") from e

        return {"status": "ok"}

    def get_client_info(self):
        return self.request("GET", "/v2/clients/me")

    def get_customers(self, search: Optional[str] = None):
        params = {}
        if search:
            params["search"] = search
        return self.request("GET", "/v2/customers", params=params)

    def get_customer(self, customer_id: str):
        return self.request("GET", f"/v2/customers/{customer_id}")

    def get_customer_scores(self, customer_id: str):
        return self.request("GET", f"/v2/customers/{customer_id}/scores")

    def get_customer_monitor(self, customer_id: str):
        return self.request("GET", f"/v2/customers/{customer_id}/monitor")

    def get_cases(self):
        return self.request("GET", "/v2/cases")

    def create_and_screen_sync(self, payload: Dict[str, Any]):
        return self.request(
            "POST",
            "/v2/workflows/sync/create-and-screen",
            json_body=payload
        )

    def create_and_screen_async(self, payload: Dict[str, Any]):
        return self.request(
            "POST",
            "/v2/workflows/create-and-screen",
            json_body=payload
        )

    def get_workflow_status(self, workflow_id: str):
        return self.request("GET", f"/v2/workflows/{workflow_id}")

    def create_webhook(self, payload: Dict[str, Any]):
        return self.request(
            "POST",
            "/v2/notifications/configurations/webhook",
            json_body=payload
        )

    def test_webhook(self, payload: Dict[str, Any]):
        return self.request(
            "POST",
            "/v2/notifications/configurations/webhook/test",
            json_body=payload
        )
