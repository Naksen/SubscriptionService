from django.utils.encoding import force_str
from rest_framework import pagination
from rest_framework.response import Response


class ExtPagination(pagination.PageNumberPagination):
    page_query_param = "current_page"

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_paginated_response(self, data):
        current_page_from_request = self.request.query_params.get(self.page_query_param)
        return Response(
            {
                "items": data,
                "page_size": self.get_page_size(self.request),
                "current_page": (
                    int(current_page_from_request) if current_page_from_request else 1
                ),
                "total_pages": self.page.paginator.count,
            },
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["items"],
            "properties": {
                "items": schema,
                "page_size": {
                    "type": "integer",
                    "example": 50,
                },
                "current_page": {
                    "type": "integer",
                    "example": 1,
                },
                "total_pages": {
                    "type": "integer",
                    "example": 123,
                },
            },
        }

    def get_schema_operation_parameters(self, view):
        parameters = [
            {
                "name": self.page_query_param,
                "required": False,
                "in": "query",
                "description": force_str(self.page_query_description),
                "schema": {"type": "integer", "example": 1},
            },
        ]
        if self.page_size_query_param is not None:
            parameters.append(
                {
                    "name": self.page_size_query_param,
                    "required": False,
                    "in": "query",
                    "description": force_str(self.page_size_query_description),
                    "schema": {"type": "integer", "example": self.page_size},
                },
            )
        return parameters
