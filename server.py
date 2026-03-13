from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import traceback

app = FastAPI()

VOLUME_PATH = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/data")
LICENSE_FILE = os.path.join(VOLUME_PATH, "licenses.json")
SEED_FILE = "licenses.json"


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: str


def read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_seed_licenses():
    if os.path.exists(SEED_FILE):
        return read_json_file(SEED_FILE)
    return {}


def ensure_license_file():
    os.makedirs(VOLUME_PATH, exist_ok=True)

    seed_data = load_seed_licenses()

    if not os.path.exists(LICENSE_FILE):
        write_json_file(LICENSE_FILE, seed_data)
        return

    try:
        volume_data = read_json_file(LICENSE_FILE)
    except Exception:
        write_json_file(LICENSE_FILE, seed_data)
        return

    merged_data = sync_licenses(seed_data, volume_data)
    write_json_file(LICENSE_FILE, merged_data)


def sync_licenses(seed_data, volume_data):
    merged = {}

    for username, seed_user in seed_data.items():
        if username in volume_data:
            volume_user = volume_data[username]

            merged[username] = {
                "password": seed_user.get("password", volume_user.get("password")),
                "device_id": volume_user.get("device_id"),
                "active": seed_user.get("active", volume_user.get("active", True)),
            }
        else:
            merged[username] = {
                "password": seed_user.get("password", ""),
                "device_id": seed_user.get("device_id", None),
                "active": seed_user.get("active", True),
            }

    return merged


def load_licenses():
    ensure_license_file()
    return read_json_file(LICENSE_FILE)


def save_licenses(data):
    write_json_file(LICENSE_FILE, data)


@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Servidor de licencias Neon Race activo"
    }


@app.get("/health")
def health():
    try:
        ensure_license_file()
        data = load_licenses()
        return {
            "ok": True,
            "volume_path": VOLUME_PATH,
            "license_file": LICENSE_FILE,
            "license_file_exists": os.path.exists(LICENSE_FILE),
            "users": list(data.keys())
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }


@app.post("/login")
def login(data: LoginRequest):
    try:
        licenses = load_licenses()
        user = licenses.get(data.username)

        if not user:
            return {"ok": False, "message": "Usuario no encontrado"}

        if not user.get("active", False):
            return {"ok": False, "message": "Licencia desactivada"}

        if user["password"] != data.password:
            return {"ok": False, "message": "Contraseña incorrecta"}

        saved_device = user.get("device_id")

        if saved_device is None:
            user["device_id"] = data.device_id
            licenses[data.username] = user
            save_licenses(licenses)
            return {"ok": True, "message": "Licencia activada correctamente"}

        if saved_device == data.device_id:
            return {"ok": True, "message": "Acceso correcto"}

        return {"ok": False, "message": "Esta licencia ya está activada en otro ordenador"}

    except Exception as e:
        return {
            "ok": False,
            "message": "Error interno del servidor",
            "error": str(e),
            "trace": traceback.format_exc()
        }
