"""Typed OpenAI settings results: FastMCP must emit schemas and structured content."""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class SettingsSchema(TypedDict):
    type: Literal["object"]
    properties: dict[str, Any]


class SettingsAction(TypedDict):
    kind: Literal["tool"]
    tool: str


class SettingsGroup(TypedDict):
    kind: Literal["group"]
    title: str
    items: list[SettingsAction]


class SettingsReadResult(BaseModel):
    schema_: SettingsSchema = Field(alias="schema")
    values: dict[str, Any]
    layout: list[SettingsGroup]


class SettingsUpdateResult(TypedDict):
    status: str
    values: dict[str, Any]
