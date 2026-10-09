import socket
import json
import threading

from config import SERVER_HOST, SERVER_PORT


clientes = {}


def enviar_json(sock, datos):
    mensaje = json.dumps(datos) + "\n"
    sock.sendall(mensaje.encode("utf-8"))


def recibir_json(sock):
    file = sock.makefile("r", encoding="utf-8")
    linea = file.readline()

    if not linea:
        return None

    return json.loads(linea)


def registrar_cliente(datos, addr):
    cliente = datos["cliente"]
    puerto = datos["port"]

    clientes[cliente] = {
        "cliente": cliente,
        "ip": addr[0],
        "port": puerto
    }

    return {
        "type": "register_ok",
        "cliente": cliente,
        "ip": addr[0],
        "port": puerto
    }


def atender_cliente(conn, addr):
    try:
        while True:

            datos = recibir_json(conn)

            if datos is None:
                break

            tipo = datos.get("type")

            # Registrar cliente
            if tipo == "register":

                respuesta = registrar_cliente(
                    datos,
                    addr
                )

                enviar_json(
                    conn,
                    respuesta
                )

                print(
                    f"Cliente registrado: "
                    f"{respuesta['cliente']} "
                    f"({respuesta['ip']}:{respuesta['port']})"
                )

            # Listar clientes
            elif tipo == "list":

                enviar_json(
                    conn,
                    {
                        "type": "list_ok",
                        "clients": list(clientes.values())
                    }
                )

            # Buscar cliente
            elif tipo == "lookup":

                nombre = datos["cliente"]

                if nombre in clientes:

                    cliente = clientes[nombre]

                    enviar_json(
                        conn,
                        {
                            "type": "lookup_ok",
                            "cliente": cliente["cliente"],
                            "ip": cliente["ip"],
                            "port": cliente["port"]
                        }
                    )

                else:

                    enviar_json(
                        conn,
                        {
                            "type": "lookup_error"
                        }
                    )

            # Desregistrar cliente
            elif tipo == "unregister":

                nombre = datos["cliente"]

                if nombre in clientes:
                    del clientes[nombre]

                enviar_json(
                    conn,
                    {
                        "type": "unregister_ok"
                    }
                )

    except Exception as e:

        print(
            f"Error atendiendo cliente {addr}: {e}"
        )

    finally:

        conn.close()


def iniciar_servidor():

    servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor.bind(
        (SERVER_HOST, SERVER_PORT)
    )

    servidor.listen()

    print("=" * 45)
    print("SERVIDOR DE CHAT")
    print("=" * 45)
    print(
        f"Servidor escuchando en "
        f"{SERVER_HOST}:{SERVER_PORT}"
    )
    print("=" * 45)

    while True:

        conn, addr = servidor.accept()

        print(
            f"Nueva conexión desde {addr}"
        )

        # Crear un hilo para cada cliente
        hilo = threading.Thread(
            target=atender_cliente,
            args=(conn, addr),
            daemon=True
        )

        hilo.start()


if __name__ == "__main__":
    iniciar_servidor()