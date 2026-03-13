from fastapi import FastAPI
from pydantic import BaseModel
import json
import os

app = FastAPI()

LICENSE_FILE = "licenses.json"


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: str


def load_licenses():
    if not os.path.exists(LICENSE_FILE):
        return {}
    with open(LICENSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_licenses(data):
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.post("/login")
def login(data: LoginRequest):
    licenses = load_licenses()

    user = licenses.get(data.username)
    if not user:
        return {
            "ok": False,
            "message": "Usuario no encontrado"
        }

    if not user.get("active", False):
        return {
            "ok": False,
            "message": "Licencia desactivada"
        }

    if user["password"] != data.password:
        return {
            "ok": False,
            "message": "Contraseña incorrecta"
        }

    saved_device = user.get("device_id")

    # Primera activación
    if saved_device is None:
        user["device_id"] = data.device_id
        licenses[data.username] = user
        save_licenses(licenses)
        return {
            "ok": True,
            "message": "Licencia activada correctamente"
        }

    # Mismo ordenador
    if saved_device == data.device_id:
        return {
            "ok": True,
            "message": "Acceso correcto"
        }

    # Otro ordenador
    return {
        "ok": False,
        "message": "Esta licencia ya está activada en otro ordenador"
    }