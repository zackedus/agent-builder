"""Pydantic models for DevOps build output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BuildStatus = Literal["success", "partial", "failed"]


class BuildReport(BaseModel):
    """Persisted build summary (``dist/BUILD_REPORT.json``)."""

    project_name: str
    version: str = "1.0.0"
    platform: str
    requirements_path: str = "requirements.txt"
    spec_path: str | None = None
    artifact_path: str | None = None
    package_path: str | None = None
    checksum_sha256: str | None = None
    smoke_ok: bool = False
    status: BuildStatus = "partial"
    notes: list[str] = Field(default_factory=list)

    def is_acceptable(self) -> bool:
        return self.status in ("success", "partial") and self.package_path is not None
