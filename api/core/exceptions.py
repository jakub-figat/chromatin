class ServiceException(Exception):
    """Base exception for domain/business logic errors"""

    pass


class NotFoundError(ServiceException):
    """Resource not found"""

    def __init__(self, resource: str, identifier: int | str):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with id {identifier} not found")


class PermissionDeniedError(ServiceException):
    """User doesn't have permission to perform action"""

    def __init__(self, action: str, resource: str):
        self.action = action
        self.resource = resource
        super().__init__(f"Permission denied: cannot {action} {resource}")


class AlreadyExistsError(ServiceException):
    """Resource already exists"""

    def __init__(self, resource: str, field: str, value: str):
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field}='{value}' already exists")


class ValidationError(ServiceException):
    """Business logic validation error"""

    pass
