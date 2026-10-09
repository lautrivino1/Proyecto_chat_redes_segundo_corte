import socket
import threading
import json

from config import SERVER_HOST, SERVER_PORT
from crypto import encriptar, desencriptar


cliente_nombre = ""
puerto_escucha = 0

conexion_servidor = None
lock_servidor = threading.Lock()


def enviar_json_socket(sock, datos):

    mensaje = json.dumps(datos) + "\n"

    sock.sendall(
        mensaje.encode("utf-8")
    )


def recibir_json_socket():

    file = conexion_servidor.makefile(
        "r",
        encoding="utf-8"
    )

    linea = file.readline()

    if not linea:
        return None

    return json.loads(linea)


def conectar_servidor():

    global conexion_servidor

    conexion_servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    conexion_servidor.connect(
        (SERVER_HOST, SERVER_PORT)
    )


def registrar():

    with lock_servidor:

        enviar_json_socket(
            conexion_servidor,
            {
                "type": "register",
                "cliente": cliente_nombre,
                "port": puerto_escucha
            }
        )

        respuesta = recibir_json_socket()

    if respuesta is None:

        print(
            "El servidor cerró la conexión."
        )

        return

    if respuesta["type"] == "register_ok":

        print("\nRegistro exitoso.")

        print(
            f"{respuesta['cliente']} -> "
            f"{respuesta['ip']}:{respuesta['port']}\n"
        )

    else:

        print(
            "No fue posible registrarse."
        )


def listar_clientes():

    with lock_servidor:

        enviar_json_socket(
            conexion_servidor,
            {
                "type": "list"
            }
        )

        respuesta = recibir_json_socket()

    if respuesta is None:

        print(
            "El servidor cerró la conexión."
        )

        return

    if respuesta["type"] == "list_ok":

        print("\nCLIENTES REGISTRADOS")

        for cliente in respuesta["clients"]:

            print(
                f"- {cliente['cliente']} "
                f"({cliente['ip']}:{cliente['port']})"
            )

        print()


def buscar_cliente(nombre):

    with lock_servidor:

        enviar_json_socket(
            conexion_servidor,
            {
                "type": "lookup",
                "cliente": nombre
            }
        )

        respuesta = recibir_json_socket()

    if respuesta is None:

        print(
            "El servidor cerró la conexión."
        )

        return None

    if respuesta["type"] == "lookup_ok":

        return (
            respuesta["ip"],
            respuesta["port"]
        )

    print(
        "\nCliente no encontrado.\n"
    )

    return None


def desregistrar():

    try:

        with lock_servidor:

            enviar_json_socket(
                conexion_servidor,
                {
                    "type": "unregister",
                    "cliente": cliente_nombre
                }
            )

            recibir_json_socket()

    except Exception:

        pass


def manejar_chat(conn, addr):

    file = conn.makefile(
        "r",
        encoding="utf-8"
    )

    try:

        while True:

            linea = file.readline()

            if not linea:
                break

            datos = json.loads(linea)

            if datos["type"] == "chat":

                remitente = datos["cliente"]

                mensaje_encriptado = datos["message"]

                print("\n" + "=" * 50)
                print("           MENSAJE RECIBIDO")
                print("=" * 50)

                print(
                    "\nMensaje encriptado recibido:"
                )

                print(
                    mensaje_encriptado
                )

                print(
                    "\nDesencriptando..."
                )

                try:

                    mensaje = desencriptar(
                        mensaje_encriptado
                    )

                except Exception:

                    print(
                        "\nNo fue posible "
                        "desencriptar el mensaje."
                    )

                    continue

                print(
                    "\nMensaje desencriptado:"
                )

                print(
                    f"{remitente}: {mensaje}"
                )

                print("=" * 50)

                print(
                    "\n>> ",
                    end="",
                    flush=True
                )

    except Exception as e:

        print(
            f"\nError recibiendo mensaje: {e}"
        )

    finally:

        conn.close()


def escuchar_mensajes():

    servidor_cliente = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor_cliente.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor_cliente.bind(
        ("0.0.0.0", puerto_escucha)
    )

    servidor_cliente.listen()

    print(
        f"Escuchando mensajes en "
        f"puerto {puerto_escucha}..."
    )

    while True:

        conn, addr = servidor_cliente.accept()

        hilo = threading.Thread(
            target=manejar_chat,
            args=(conn, addr),
            daemon=True
        )

        hilo.start()


def enviar_mensaje(destinatario, mensaje):

    destino = buscar_cliente(
        destinatario
    )

    if destino is None:
        return

    ip, puerto = destino

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.connect(
            (ip, puerto)
        )

        print("\n" + "=" * 50)
        print("        PROCESO DE ENCRIPTACIÓN")
        print("=" * 50)

        print(
            "\nMensaje original:"
        )

        print(
            mensaje
        )

        print(
            "\nEncriptando..."
        )

        mensaje_encriptado = encriptar(
            mensaje
        )

        print(
            "\nMensaje encriptado:"
        )

        print(
            mensaje_encriptado
        )

        print(
            "\nEnviando mensaje..."
        )

        print("=" * 50)

        enviar_json_socket(
            sock,
            {
                "type": "chat",
                "cliente": cliente_nombre,
                "message": mensaje_encriptado
            }
        )

        sock.close()

        print(
            "\nMensaje enviado correctamente.\n"
        )

    except Exception as e:

        print(
            f"\nNo fue posible enviar "
            f"el mensaje: {e}\n"
        )


def mostrar_menu():

    print("=" * 45)
    print("CHAT CON SOCKETS")
    print("=" * 45)

    print(
        "1. Listar clientes"
    )

    print(
        "2. Enviar mensaje"
    )

    print(
        "3. Salir"
    )

    print("=" * 45)


def iniciar_cliente():

    global cliente_nombre
    global puerto_escucha

    print(
        "\nBienvenido al chat\n"
    )

    cliente_nombre = input(
        "Ingrese su identificador: "
    ).strip()

    puerto_escucha = int(
        input(
            "Ingrese su puerto de escucha: "
        )
    )

    hilo_escucha = threading.Thread(
        target=escuchar_mensajes,
        daemon=True
    )

    hilo_escucha.start()

    conectar_servidor()

    registrar()

    while True:

        mostrar_menu()

        opcion = input(
            "Seleccione una opción: "
        )

        if opcion == "1":

            listar_clientes()

        elif opcion == "2":

            destinatario = input(
                "Cliente destinatario: "
            ).strip()

            mensaje = input(
                "Mensaje: "
            )

            enviar_mensaje(
                destinatario,
                mensaje
            )

        elif opcion == "3":

            desregistrar()

            conexion_servidor.close()

            print(
                "\nCliente cerrado correctamente."
            )

            break

        else:

            print(
                "\nOpción inválida.\n"
            )


if __name__ == "__main__":

    iniciar_cliente()