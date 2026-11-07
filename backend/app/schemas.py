"""Request bodies. Pydantic validates them; a failure becomes a 400 VALIDATION_ERROR with a plain-language message."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(v: str | None, max_len: int) -> str | None:
    if v is None:
        return None
    v = _CTRL.sub(" ", v).strip()
    return v[:max_len] or None


def normalize_phone(raw: str) -> str:
    """Pakistani mobile numbers in any common form -> +923001234567."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0092"):
        digits = digits[2:]
    if digits.startswith("92") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+92" + digits[1:]
    if len(digits) == 10 and digits.startswith("3"):
        return "+92" + digits
    raise ValueError("Enter a valid Pakistani mobile number, for example 0300 1234567.")


def check_email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v


def check_password(v: str) -> str:
    if not (re.search(r"[A-Z]", v) and re.search(r"\d", v) and re.search(r"[^A-Za-z0-9]", v)):
        raise ValueError("Password needs at least 8 characters, one uppercase letter, one number and one special character.")
    return v


class Body(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ---------------------------------------------------------------------------------------------- auth
class RegisterIn(Body):
    fullName: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    acceptedTerms: bool
    phone: str | None = None
    cnic: str | None = None
    preferredLanguage: Literal["en", "ur", "both"] = "en"

    @field_validator("fullName")
    @classmethod
    def _name(cls, v: str) -> str:
        return clean_text(v, 80) or ""

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return check_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_password(v)

    @field_validator("acceptedTerms")
    @classmethod
    def _terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Please accept the Terms of Service and Privacy Policy.")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v and v.strip() else None

    @field_validator("cnic")
    @classmethod
    def _cnic(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        if not re.fullmatch(r"\d{5}-\d{7}-\d", v.strip()):
            raise ValueError("CNIC must look like 35202-1234567-1.")
        return v.strip()


class LoginIn(Body):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    remember: bool = True
    role: Literal["client", "lawyer", "admin"] = "client"


class RefreshIn(Body):
    refreshToken: str = Field(min_length=10, max_length=200)


class LogoutIn(Body):
    refreshToken: str | None = Field(default=None, max_length=200)


class ChangePasswordIn(Body):
    currentPassword: str = Field(min_length=1, max_length=128)
    newPassword: str = Field(min_length=8, max_length=128)

    @field_validator("newPassword")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_password(v)


# ---------------------------------------------------------------------------------------------- users
class UserPatch(Body):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = None
    city: str | None = Field(default=None, max_length=60)
    address: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return None if v is None else check_email(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalize_phone(v) if v and v.strip() else None


PROVINCES = ("Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan", "Islamabad Capital Territory", "Gilgit-Baltistan", "Azad Jammu & Kashmir")
USER_TYPES = ("Citizen", "Young adult", "Business owner (SME)", "Student")
EMPLOYMENT = ("Employed", "Self-employed", "Unemployed", "Student", "Retired")
ROLES = ("Tenant", "Landlord", "Employee", "Employer", "Business owner", "Property buyer or seller", "Parent or guardian")
AGE_BANDS = ("18-24", "25-34", "35-44", "45-59", "60+")
MARITAL = ("Single", "Married", "Divorced", "Widowed", "Prefer not to say")
INTERESTS = ("Property and tenancy", "Family", "Criminal", "Employment", "Business and contracts", "Consumer", "Cyber and online", "Constitutional rights")


class ProfileIn(Body):
    """Onboarding answers. Every field is optional; values are limited to fixed choices (city is the only free text), because
    these values are placed in the model's prompt. No name, CNIC, phone, email or address is ever part of the profile."""
    province: Literal[PROVINCES] | None = None            # type: ignore[valid-type]
    city: str | None = Field(default=None, max_length=60)
    userType: Literal[USER_TYPES] | None = None           # type: ignore[valid-type]
    employmentStatus: Literal[EMPLOYMENT] | None = None   # type: ignore[valid-type]
    roles: list[Literal[ROLES]] = Field(default_factory=list, max_length=7)   # type: ignore[valid-type]
    ageBand: Literal[AGE_BANDS] | None = None             # type: ignore[valid-type]
    maritalStatus: Literal[MARITAL] | None = None         # type: ignore[valid-type]
    language: Literal["en", "ur", "both"] | None = None
    interests: list[Literal[INTERESTS]] = Field(default_factory=list, max_length=8)   # type: ignore[valid-type]

    @field_validator("city")
    @classmethod
    def _city(cls, v: str | None) -> str | None:
        v = clean_text(v, 60)
        if v and not re.fullmatch(r"[A-Za-z0-9 .,'\-]{1,60}", v):
            raise ValueError("City can only contain letters, numbers and spaces.")
        return v


# ---------------------------------------------------------------------------------------------- chat
class ConversationCreate(Body):
    firstMessage: str = Field(min_length=1, max_length=4000)
    topic: str | None = Field(default=None, max_length=40)


class ConversationPatch(Body):
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = clean_text(v, 80)
        if not v:
            raise ValueError("Title cannot be empty.")
        return v


class PinIn(Body):
    pinned: bool = True


class MessageIn(Body):
    content: str = Field(min_length=1, max_length=4000)
    attachmentIds: list[str] = Field(default_factory=list, max_length=5)
    language: Literal["en", "ur"] | None = None


class AnalysisIn(Body):
    documentIds: list[str] = Field(min_length=1, max_length=10)
    language: Literal["auto", "en", "ur"] = "auto"
    depth: Literal["quick", "detailed"] = "quick"
    saveToVault: bool = False


class FeedbackIn(Body):
    vote: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=500)


class SourceReportIn(Body):
    messageId: str
    sourceId: int = Field(ge=1, le=50)
    reason: str = Field(default="user_report", max_length=60)
