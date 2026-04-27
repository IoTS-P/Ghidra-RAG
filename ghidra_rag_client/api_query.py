from typing import Optional
from httpx import Client


class APIQuery:
    def __init__(self, client: Client):
        self.client = client

    def get_methods(self, class_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/class/{class_name}/methods", params=params)
        response.raise_for_status()
        return response.json()

    def get_fields(self, class_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/class/{class_name}/fields", params=params)
        response.raise_for_status()
        return response.json()

    def get_hierarchy(self, class_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/class/{class_name}/hierarchy", params=params)
        response.raise_for_status()
        return response.json()

    def get_package_classes(self, package_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/package/{package_name}/classes", params=params)
        response.raise_for_status()
        return response.json()

    def get_method_detail(self, class_name: str, method_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/method/{class_name}/{method_name}", params=params)
        response.raise_for_status()
        return response.json()

    def get_method_examples(self, class_name: str, method_name: str, version: Optional[str] = None) -> dict:
        params = {"version": version} if version else {}
        response = self.client.get(f"/api/method/{class_name}/{method_name}/examples", params=params)
        response.raise_for_status()
        return response.json()

    def add_method_example(
        self,
        class_name: str,
        method_name: str,
        example_code: str,
        description: Optional[str] = None,
        scenario: Optional[str] = None,
        expected_output: Optional[str] = None,
        author: str = "llm",
        model_id: Optional[str] = None,
        confidence: float = 0.5,
        version: Optional[str] = None
    ) -> dict:
        params = {"version": version} if version else {}
        data = {
            "example_code": example_code,
            "description": description,
            "scenario": scenario,
            "expected_output": expected_output,
            "author": author,
            "model_id": model_id,
            "confidence": confidence
        }
        response = self.client.post(
            f"/api/method/{class_name}/{method_name}/examples",
            params=params,
            json=data
        )
        response.raise_for_status()
        return response.json()

    def vote_example(self, example_id: int, vote: str) -> dict:
        response = self.client.post(f"/api/examples/{example_id}/vote", json={"vote": vote})
        response.raise_for_status()
        return response.json()

    def update_example_status(self, example_id: int, status: str) -> dict:
        response = self.client.patch(f"/api/examples/{example_id}/status", json={"status": status})
        response.raise_for_status()
        return response.json()

    def list_versions(self) -> dict:
        response = self.client.get("/api/v1/versions")
        response.raise_for_status()
        return response.json()
