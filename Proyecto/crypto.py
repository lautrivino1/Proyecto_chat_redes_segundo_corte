import os

from dotenv import load_dotenv
from cryptography.fernet import Fernet


# Cargar las variables del archivo .env
load_dotenv()


# Obtener la clave de encriptación
clave = os.getenv("FERNET_KEY")

if clave is None:
    raise ValueError("No se encontró FERNET_KEY en el archivo .env")


# Crear el objeto Fernet
fernet = Fernet(clave.encode())


def encriptar(mensaje):
    mensaje_bytes = mensaje.encode("utf-8")

    mensaje_encriptado = fernet.encrypt(mensaje_bytes)

    return mensaje_encriptado.decode("utf-8")


def desencriptar(mensaje_encriptado):
    mensaje_encriptado_bytes = mensaje_encriptado.encode("utf-8")

    mensaje_bytes = fernet.decrypt(mensaje_encriptado_bytes)

    return mensaje_bytes.decode("utf-8")


if __name__ == "__main__":
    mensaje = "Hola Natalia"

    mensaje_encriptado = encriptar(mensaje)
    mensaje_desencriptado = desencriptar(mensaje_encriptado)

    print("Mensaje original:")
    print(mensaje)

    print("\nMensaje encriptado:")
    print(mensaje_encriptado)

    print("\nMensaje desencriptado:")
    print(mensaje_desencriptado)