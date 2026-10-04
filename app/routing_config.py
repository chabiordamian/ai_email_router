from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

DepartmentId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z][a-z0-9-]*$"),
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Department(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: DepartmentId
    email: EmailStr
    description: NonEmptyText
    examples: tuple[NonEmptyText, ...] = Field(min_length=1)


class RoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    departments: tuple[Department, ...] = Field(min_length=1)
    fallback_department: DepartmentId

    @model_validator(mode="after")
    def validate_departments(self) -> Self:
        department_ids = [department.id for department in self.departments]
        if len(department_ids) != len(set(department_ids)):
            raise ValueError("department ids must be unique")

        emails = [str(department.email).casefold() for department in self.departments]
        if len(emails) != len(set(emails)):
            raise ValueError("department email addresses must be unique")

        if self.fallback_department not in department_ids:
            raise ValueError(
                "fallback_department must reference an existing department"
            )

        return self


def load_routing_config(path: Path) -> RoutingConfig:
    try:
        raw_config: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in routing config: {path}") from error

    return RoutingConfig.model_validate(raw_config)
