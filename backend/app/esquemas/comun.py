"""Esquemas compartidos."""
from pydantic import BaseModel, EmailStr, Field


class CredencialesIn(BaseModel):
    email: EmailStr
    password: str


class UsuarioSesion(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    rol: str


class EstadoIn(BaseModel):
    activo: bool


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class AreaOut(BaseModel):
    id: int
    nombre: str
