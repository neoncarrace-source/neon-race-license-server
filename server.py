from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import traceback

app = FastAPI()

# Si Railway tiene volumen montado, usa esa ruta.
# Si no, usa /data por defecto.
VOLUME_PATH = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/data")
LICENSE_FILE = os.path.join(VOLUME_PATH, "licenses.json")

# Archivo plantilla del repositorio
SEED_FILE = "licenses.json"


class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: str


def ensure_license_file():
    # Crear carpeta del volumen si no existe
    os.makedirs(VOLUME_PATH, exist_ok=True)

    # Si no existe aún el archivo persistente, lo creamos
    if not os.path.exists(LICENSE_FILE):
        if os.path.exists(SEED_FILE):
            with open(SEED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def load_licenses():
    ensure_license_file()

    with open(LICENSE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_licenses(data):
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Servidor de licencias Neon Race activo",
        "volume_path": VOLUME_PATH,
        "license_file": LICENSE_FILE
    }


@app.get("/health")
def health():
    try:
        ensure_license_file()
        return {
            "ok": True,
            "volume_path": VOLUME_PATH,
            "license_file": LICENSE_FILE,
            "license_file_exists": os.path.exists(LICENSE_FILE)
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
            print(f"LOGIN FALLIDO | usuario no encontrado | user={data.username} | device={data.device_id}")
            return {
                "ok": False,
                "message": "Usuario no encontrado"
            }

        if not user.get("active", False):
            print(f"LOGIN BLOQUEADO | licencia desactivada | user={data.username}")
            return {
                "ok": False,
                "message": "Licencia desactivada"
            }

        if user["password"] != data.password:
            print(f"LOGIN FALLIDO | contraseña incorrecta | user={data.username}")
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

            print(f"LOGIN OK | primera activación | user={data.username} | device={data.device_id}")

            return {
                "ok": True,
                "message": "Licencia activada correctamente"
            }

        # Mismo ordenador
        if saved_device == data.device_id:
            print(f"LOGIN OK | mismo dispositivo | user={data.username}")
            return {
                "ok": True,
                "message": "Acceso correcto"
            }

        # Otro ordenador
        print(f"LOGIN BLOQUEADO | otro dispositivo | user={data.username} | intento={data.device_id}")

        return {
            "ok": False,
            "message": "Esta licencia ya está activada en otro ordenador"
        }

    except Exception as e:
        print("ERROR EN /login")
        print(str(e))
        print(traceback.format_exc())

        return {
            "ok": False,
            "message": "Error interno del servidor",
            "error": str(e),
            "trace": traceback.format_exc()
        }
