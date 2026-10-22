import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-]{7,15}$")


def _email(v):
    if v is None:
        return v
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("invalid email address")
    return v


def _phone(v):
    if v is None:
        return v
    v = v.strip()
    if not PHONE_RE.match(v):
        raise ValueError("invalid phone number")
    return v


def _dob(v):
    if v is not None and v >= date.today():
        raise ValueError("date_of_birth must be in the past")
    return v



class StudentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    enrollment_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("name must have at least 2 characters")
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        if v is None:
            return v
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("invalid phone number")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v: date):
        if v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v


class StudentCreate(StudentBase):
    @model_validator(mode="after")
    def need_contact(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one of email or phone")
        return self


class StudentUpdate(BaseModel):
    """All fields optional (PATCH semantics)."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    enrollment_date: Optional[date] = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        return _email(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _phone(v)

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v):
        return _dob(v)


class StudentOut(StudentBase):
    id: int


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=300)


class AskResponse(BaseModel):
    question: str
    answer: str
    records_used: int
