from pydantic import BaseModel, validator
from pydantic.class_validators import root_validator


class UserInfo(BaseModel):
    name: str
    email: str
    mobile_number: str

    @validator("email")
    def valid_email(cls, v):
        if "@" not in v:
            raise ValueError("email must be a valid email")
        return v

    @validator("mobile_number")
    def valid_mobile_number(cls, v):
        if len(v) < 10:
            raise ValueError("mobile_number should not be less than 10")
        return v

    @validator("name")
    def valid_name(cls, v):
        if v is None or v == "":
            raise ValueError("name should not be empty or null")
        return v


class CustomRequest(BaseModel):
    data: dict
