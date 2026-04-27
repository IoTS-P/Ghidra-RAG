from typing import Optional
from ..database.api_repository import api_repository
from ..database.models import ClassInfo, Method, FieldInfo, MethodExample


class APIService:
    def get_class_methods(self, class_name: str, version: str) -> list[Method]:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return []
        return api_repository.get_methods_by_class_id(class_info.id)

    def get_class_fields(self, class_name: str, version: str) -> list[FieldInfo]:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return []
        return api_repository.get_fields_by_class_id(class_info.id)

    def get_class_hierarchy(self, class_name: str, version: str) -> dict:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return {"ancestors": [], "descendants": []}
        return api_repository.get_class_hierarchy(class_info.id)

    def get_classes_in_package(self, package_name: str, version: str) -> list[ClassInfo]:
        package = api_repository.get_package_by_name(package_name, version)
        if not package:
            return []
        return api_repository.get_classes_in_package(package.id)

    def get_method_detail(self, class_name: str, method_name: str, version: str) -> Optional[Method]:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return None
        return api_repository.get_method_by_name(class_info.id, method_name)

    def get_method_examples(self, class_name: str, method_name: str, version: str) -> list[MethodExample]:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return []
        method = api_repository.get_method_by_name(class_info.id, method_name)
        if not method:
            return []
        return api_repository.get_examples_by_method_id(method.id)

    def add_method_example(
        self,
        class_name: str,
        method_name: str,
        version: str,
        example_code: str,
        description: Optional[str] = None,
        scenario: Optional[str] = None,
        expected_output: Optional[str] = None,
        author: str = "llm",
        model_id: Optional[str] = None,
        confidence: float = 0.5
    ) -> Optional[MethodExample]:
        class_info = api_repository.get_class_by_full_name(class_name, version)
        if not class_info:
            return None
        method = api_repository.get_method_by_name(class_info.id, method_name)
        if not method:
            return None
        example = MethodExample(
            method_id=method.id,
            example_code=example_code,
            description=description,
            scenario=scenario,
            expected_output=expected_output,
            author=author,
            model_id=model_id,
            confidence=confidence,
            status="pending"
        )
        example_id = api_repository.add_example(example)
        example.id = example_id
        return example

    def vote_example(self, example_id: int, vote: str) -> bool:
        return api_repository.vote_example(example_id, vote)

    def update_example_status(self, example_id: int, status: str) -> bool:
        return api_repository.update_example_status(example_id, status)


api_service = APIService()
