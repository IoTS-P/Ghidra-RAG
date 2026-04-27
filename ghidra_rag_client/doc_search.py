from typing import Optional
from httpx import Client


class DocSearch:
    def __init__(self, client: Client):
        self.client = client

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        version: Optional[str] = None
    ) -> dict:
        params = {"q": query, "top_k": top_k}
        if doc_type:
            params["doc_type"] = doc_type
        if version:
            params["version"] = version
        response = self.client.get("/api/v1/search", params=params)
        response.raise_for_status()
        return response.json()

    def search_post(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
        version: Optional[str] = None
    ) -> dict:
        params = {"version": version} if version else {}
        data = {
            "query": query,
            "top_k": top_k,
            "doc_type": doc_type
        }
        response = self.client.post("/api/v1/search", params=params, json=data)
        response.raise_for_status()
        return response.json()
