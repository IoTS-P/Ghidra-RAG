from typing import Optional
from httpx import Client
from .api_query import APIQuery
from .doc_search import DocSearch


class GhidraRAGClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30
    ):
        self.client = Client(base_url=base_url, timeout=timeout)
        self.api = APIQuery(self.client)
        self.search = DocSearch(self.client)

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ghidra RAG CLI")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("command", nargs="*", help="Command to execute")
    args = parser.parse_args()

    with GhidraRAGClient(base_url=args.url) as client:
        if args.command and args.command[0] == "versions":
            result = client.api.list_versions()
            print(result)
        elif args.command and args.command[0] == "search":
            query = " ".join(args.command[1:]) if len(args.command) > 1 else ""
            result = client.search(query)
            print(result)
        else:
            print("Available commands: versions, search <query>")


if __name__ == "__main__":
    main()
