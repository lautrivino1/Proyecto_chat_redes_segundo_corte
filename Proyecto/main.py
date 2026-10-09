import flet as ft
import socket
import json
import threading

from config import SERVER_HOST, SERVER_PORT
from crypto import encriptar, desencriptar


cliente_nombre = ""
puerto_escucha = 0
conexion_servidor = None
lock_servidor = threading.Lock()
destino_actual = None
cliente_registrado = False


# ============================================================
# COMUNICACIÓN JSON
# ============================================================

def enviar_json(sock, datos):
    mensaje = json.dumps(datos) + "\n"
    sock.sendall(mensaje.encode("utf-8"))


def recibir_json(sock):
    archivo = sock.makefile("r", encoding="utf-8")
    linea = archivo.readline()

    if not linea:
        return None

    return json.loads(linea)


# ============================================================
# CONEXIÓN CON EL SERVIDOR
# ============================================================

def conectar_servidor():
    global conexion_servidor

    conexion_servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    conexion_servidor.connect(
        (SERVER_HOST, SERVER_PORT)
    )

    print(
        f"Conectado al servidor "
        f"{SERVER_HOST}:{SERVER_PORT}"
    )


# ============================================================
# REGISTRAR CLIENTE
# ============================================================

def registrar_cliente():
    global cliente_registrado

    with lock_servidor:

        enviar_json(
            conexion_servidor,
            {
                "type": "register",
                "cliente": cliente_nombre,
                "port": puerto_escucha
            }
        )

        respuesta = recibir_json(
            conexion_servidor
        )

    if respuesta and respuesta.get("type") == "register_ok":

        cliente_registrado = True

        print(
            f"Cliente registrado: "
            f"{respuesta['cliente']} "
            f"({respuesta['ip']}:{respuesta['port']})"
        )

        return True

    print(
        "No fue posible registrar "
        "el cliente."
    )

    return False


# ============================================================
# DESREGISTRAR CLIENTE
# ============================================================

def desregistrar_cliente():
    global cliente_registrado
    global conexion_servidor

    if not cliente_registrado:
        return

    try:

        with lock_servidor:

            enviar_json(
                conexion_servidor,
                {
                    "type": "unregister",
                    "cliente": cliente_nombre
                }
            )

            respuesta = recibir_json(
                conexion_servidor
            )

        if respuesta and respuesta.get("type") == "unregister_ok":

            print(
                f"Cliente desregistrado: "
                f"{cliente_nombre}"
            )

        cliente_registrado = False

        if conexion_servidor:

            conexion_servidor.close()
            conexion_servidor = None

    except Exception as e:

        print(
            f"Error desregistrando cliente: {e}"
        )

        cliente_registrado = False

        try:

            if conexion_servidor:
                conexion_servidor.close()

        except Exception:
            pass

        conexion_servidor = None


# ============================================================
# OBTENER CLIENTES
# ============================================================

def obtener_clientes():

    with lock_servidor:

        enviar_json(
            conexion_servidor,
            {
                "type": "list"
            }
        )

        respuesta = recibir_json(
            conexion_servidor
        )

    if respuesta and respuesta.get("type") == "list_ok":

        return respuesta.get(
            "clients",
            []
        )

    return []


# ============================================================
# BUSCAR CLIENTE
# ============================================================

def buscar_cliente(nombre):

    with lock_servidor:

        enviar_json(
            conexion_servidor,
            {
                "type": "lookup",
                "cliente": nombre
            }
        )

        respuesta = recibir_json(
            conexion_servidor
        )

    if respuesta and respuesta.get("type") == "lookup_ok":

        return {
            "cliente": respuesta["cliente"],
            "ip": respuesta["ip"],
            "port": respuesta["port"]
        }

    return None


# ============================================================
# ENVÍO DE MENSAJES DIRECTOS
# ============================================================

def enviar_mensaje_directo(destino, texto):

    informacion = buscar_cliente(destino)

    if not informacion:

        print(
            f"No se encontró "
            f"el cliente {destino}."
        )

        return False

    ip = informacion["ip"]
    puerto = informacion["port"]

    try:

        socket_destino = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        socket_destino.connect(
            (ip, puerto)
        )

        # ----------------------------------------------------
        # ENCRIPTACIÓN
        # ----------------------------------------------------

        mensaje_encriptado = encriptar(texto)

        print()
        print("=" * 55)
        print(
            "              PROCESO DE ENCRIPTACIÓN"
        )
        print("=" * 55)
        print()

        print("Mensaje original:")
        print(texto)

        print()
        print("Encriptando...")

        print()
        print("Mensaje encriptado:")
        print(mensaje_encriptado)

        print()
        print("Enviando mensaje...")

        print("=" * 55)

        enviar_json(
            socket_destino,
            {
                "type": "message",
                "from": cliente_nombre,
                "message": mensaje_encriptado
            }
        )

        socket_destino.close()

        return True

    except Exception as e:

        print()
        print(
            f"Error enviando mensaje: {e}"
        )

        return False


# ============================================================
# ESCUCHA DE MENSAJES
# ============================================================

def escuchar_mensajes(recibir_mensaje_gui):

    servidor_chat = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor_chat.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor_chat.bind(
        ("0.0.0.0", puerto_escucha)
    )

    servidor_chat.listen()

    print()
    print(
        f"Escuchando mensajes en "
        f"0.0.0.0:{puerto_escucha}"
    )

    while True:

        try:

            conexion, direccion = (
                servidor_chat.accept()
            )

            hilo = threading.Thread(
                target=atender_mensaje,
                args=(
                    conexion,
                    recibir_mensaje_gui
                ),
                daemon=True
            )

            hilo.start()

        except Exception as e:

            print(
                f"Error aceptando mensaje: {e}"
            )


# ============================================================
# ATENDER MENSAJE RECIBIDO
# ============================================================

def atender_mensaje(
    conexion,
    recibir_mensaje_gui
):

    try:

        datos = recibir_json(
            conexion
        )

        if not datos:
            return

        if datos.get("type") != "message":
            return

        remitente = datos.get(
            "from",
            "Desconocido"
        )

        mensaje_encriptado = datos.get(
            "message",
            ""
        )

        # ----------------------------------------------------
        # DESENCRIPTACIÓN
        # ----------------------------------------------------

        print()
        print("=" * 55)
        print(
            "                 MENSAJE RECIBIDO"
        )
        print("=" * 55)
        print()

        print(
            "Mensaje encriptado recibido:"
        )

        print(
            mensaje_encriptado
        )

        print()
        print("Desencriptando...")

        mensaje = desencriptar(
            mensaje_encriptado
        )

        print()
        print("Mensaje desencriptado:")

        print(
            f"{remitente}: {mensaje}"
        )

        print("=" * 55)

        recibir_mensaje_gui(
            remitente,
            mensaje
        )

    except Exception as e:

        print(
            f"Error recibiendo mensaje: {e}"
        )

    finally:

        conexion.close()


# ============================================================
# INTERFAZ GRÁFICA
# ============================================================

def main(page: ft.Page):

    global cliente_nombre
    global puerto_escucha
    global destino_actual

    page.title = "Chat"

    page.window.width = 960
    page.window.height = 640

    # ========================================================
    # CIERRE DE LA APLICACIÓN
    # ========================================================

    page.window.prevent_close = True

    async def cerrar_aplicacion(e):

        print()
        print("=" * 55)
        print("CERRANDO CLIENTE")
        print("=" * 55)

        desregistrar_cliente()

        print(
            "Cliente desregistrado correctamente."
        )

        print("=" * 55)

        await page.window.destroy()


    def manejar_evento_ventana(e):

        if e.type == ft.WindowEventType.CLOSE:

            page.run_task(
                cerrar_aplicacion,
                e
            )


    page.window.on_event = manejar_evento_ventana


    contenido = ft.Column(
        expand=True
    )

    page.add(contenido)


    # ========================================================
    # REGISTRO
    # ========================================================

    def mostrar_registro():

        contenido.controls.clear()

        contenido.alignment = (
            ft.MainAxisAlignment.CENTER
        )

        contenido.horizontal_alignment = (
            ft.CrossAxisAlignment.CENTER
        )

        nombre_input = ft.TextField(
            label="Identificador",
            hint_text="Ej: Laura",
            width=350
        )

        puerto_input = ft.TextField(
            label="Puerto de escucha",
            hint_text="Ej: 5001",
            width=350,
            keyboard_type=ft.KeyboardType.NUMBER
        )

        mensaje_error = ft.Text(
            "",
            color=ft.Colors.RED
        )


        def registrarse(e=None):

            global cliente_nombre
            global puerto_escucha

            nombre = (
                nombre_input.value.strip()
            )

            puerto_texto = (
                puerto_input.value.strip()
            )

            mensaje_error.value = ""


            # ------------------------------------------------
            # VALIDAR IDENTIFICADOR
            # ------------------------------------------------

            if not nombre:

                mensaje_error.value = (
                    "Ingrese un identificador."
                )

                page.update()

                return


            # ------------------------------------------------
            # VALIDAR PUERTO
            # ------------------------------------------------

            if not puerto_texto:

                mensaje_error.value = (
                    "Ingrese un puerto."
                )

                page.update()

                return


            try:

                puerto = int(
                    puerto_texto
                )

            except ValueError:

                mensaje_error.value = (
                    "El puerto debe ser numérico."
                )

                page.update()

                return


            if puerto < 1 or puerto > 65535:

                mensaje_error.value = (
                    "El puerto debe estar "
                    "entre 1 y 65535."
                )

                page.update()

                return


            cliente_nombre = nombre
            puerto_escucha = puerto


            # ------------------------------------------------
            # CONECTAR CON SERVIDOR
            # ------------------------------------------------

            try:

                conectar_servidor()

                registrado = (
                    registrar_cliente()
                )

                if not registrado:

                    mensaje_error.value = (
                        "No fue posible registrarse "
                        "en el servidor."
                    )

                    page.update()

                    return

                mostrar_chat()

            except Exception as error:

                mensaje_error.value = (
                    f"No se pudo conectar: {error}"
                )

                page.update()


        boton_registro = ft.Button(
            "Registrarse",
            icon=ft.Icons.LOGIN,
            on_click=registrarse
        )


        contenido.controls.extend(
            [
                ft.Text(
                    "Chat",
                    size=30,
                    weight=ft.FontWeight.BOLD
                ),

                ft.Text(
                    "Registra tu cliente "
                    "para comenzar"
                ),

                ft.Container(
                    height=20
                ),

                nombre_input,

                puerto_input,

                mensaje_error,

                ft.Container(
                    height=10
                ),

                boton_registro
            ]
        )

        page.update()


    # ========================================================
    # CHAT
    # ========================================================

    def mostrar_chat():

        contenido.controls.clear()

        contenido.alignment = (
            ft.MainAxisAlignment.START
        )

        contenido.horizontal_alignment = (
            ft.CrossAxisAlignment.STRETCH
        )


        # ====================================================
        # HISTORIAL DE CONVERSACIONES
        # ====================================================

        historiales = {}


        mensajes = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True
        )


        mensaje_input = ft.TextField(
            hint_text="Escribe un mensaje...",
            expand=True,
            border_radius=30,
            content_padding=15
        )


        titulo_chat = ft.Text(
            "Seleccione un destino",
            size=20,
            weight=ft.FontWeight.BOLD
        )


        # ====================================================
        # BURBUJA DE MENSAJE
        # ====================================================

        def burbuja(
            texto,
            enviado=False
        ):

            if enviado:

                alineacion = (
                    ft.MainAxisAlignment.END
                )

                fondo = ft.Colors.BLUE_100

            else:

                alineacion = (
                    ft.MainAxisAlignment.START
                )

                fondo = ft.Colors.GREY_200


            return ft.Row(
                [
                    ft.Container(
                        content=ft.Text(
                            texto,
                            size=15
                        ),

                        padding=12,

                        border_radius=15,

                        bgcolor=fondo
                    )
                ],

                alignment=alineacion
            )


        # ====================================================
        # MOSTRAR HISTORIAL
        # ====================================================

        def mostrar_historial(destino):

            mensajes.controls.clear()

            historial = historiales.get(
                destino,
                []
            )

            for mensaje in historial:

                tipo = mensaje["tipo"]
                texto = mensaje["texto"]

                mensajes.controls.append(
                    burbuja(
                        texto,
                        enviado=(
                            tipo == "enviado"
                        )
                    )
                )

            mensajes.update()


        # ====================================================
        # RECIBIR MENSAJE EN LA INTERFAZ
        # ====================================================

        def recibir_mensaje(
            remitente,
            texto
        ):

            # ------------------------------------------------
            # Crear historial si no existe
            # ------------------------------------------------

            if remitente not in historiales:

                historiales[remitente] = []


            # ------------------------------------------------
            # Guardar mensaje recibido
            # ------------------------------------------------

            historiales[remitente].append(
                {
                    "tipo": "recibido",
                    "texto": (
                        f"{remitente}: {texto}"
                    )
                }
            )


            # ------------------------------------------------
            # Mostrar si el chat está seleccionado
            # ------------------------------------------------

            if destino_actual == remitente:

                mensajes.controls.append(
                    burbuja(
                        f"{remitente}: {texto}",
                        enviado=False
                    )
                )

                titulo_chat.value = (
                    f"Chat con {remitente}"
                )

                page.update()


        # ====================================================
        # LISTA DE DESTINOS
        # ====================================================

        lista_destinos = ft.ListView(
            expand=True,
            spacing=5
        )


        # ====================================================
        # SELECCIONAR DESTINO
        # ====================================================

        def seleccionar_destino(
            cliente
        ):

            global destino_actual

            destino_actual = (
                cliente["cliente"]
            )

            titulo_chat.value = (
                f"Chat con "
                f"{cliente['cliente']}"
            )

            mostrar_historial(
                destino_actual
            )

            page.update()


        # ====================================================
        # CARGAR DESTINOS
        # ====================================================

        def cargar_destinos():

            try:

                clientes_registrados = (
                    obtener_clientes()
                )

            except Exception as e:

                print(
                    f"Error obteniendo clientes: {e}"
                )

                return


            lista_destinos.controls.clear()


            for cliente in clientes_registrados:

                # --------------------------------------------
                # No mostrarme a mí mismo
                # --------------------------------------------

                if (
                    cliente["cliente"]
                    == cliente_nombre
                ):
                    continue


                texto = (
                    f"{cliente['cliente']} "
                    f"{cliente['ip']}:"
                    f"{cliente['port']}"
                )


                boton = ft.Container(

                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.DEVICE_HUB,
                                size=22
                            ),

                            ft.Text(
                                texto,
                                size=15
                            )
                        ]
                    ),

                    padding=10,

                    border_radius=8,

                    ink=True,

                    on_click=lambda e, c=cliente:
                        seleccionar_destino(c)
                )


                lista_destinos.controls.append(
                    boton
                )


            page.update()


        # ====================================================
        # ACTUALIZACIÓN AUTOMÁTICA
        # ====================================================

        def actualizar_destinos_automaticamente():

            while True:

                try:

                    cargar_destinos()

                except Exception as e:

                    print(
                        "Error actualizando "
                        f"destinos: {e}"
                    )

                threading.Event().wait(3)


        # ====================================================
        # ENVIAR MENSAJE
        # ====================================================

        def enviar(e=None):

            global destino_actual

            texto = (
                mensaje_input.value.strip()
            )


            if not texto:
                return


            # ------------------------------------------------
            # VALIDAR DESTINO
            # ------------------------------------------------

            if not destino_actual:

                page.show_dialog(
                    ft.SnackBar(
                        ft.Text(
                            "Seleccione primero "
                            "un destino."
                        )
                    )
                )

                return


            # ------------------------------------------------
            # ENVIAR POR SOCKET
            # ------------------------------------------------

            enviado = enviar_mensaje_directo(
                destino_actual,
                texto
            )


            if enviado:

                # --------------------------------------------
                # Crear historial si no existe
                # --------------------------------------------

                if destino_actual not in historiales:

                    historiales[destino_actual] = []


                # --------------------------------------------
                # Guardar mensaje enviado
                # --------------------------------------------

                historiales[destino_actual].append(
                    {
                        "tipo": "enviado",
                        "texto": texto
                    }
                )


                # --------------------------------------------
                # Mostrar mensaje
                # --------------------------------------------

                mensajes.controls.append(
                    burbuja(
                        texto,
                        enviado=True
                    )
                )


                mensaje_input.value = ""

                page.update()


        mensaje_input.on_submit = enviar


        boton_enviar = ft.Button(
            "Enviar",
            icon=ft.Icons.SEND,
            on_click=enviar
        )


        # ====================================================
        # PANEL IZQUIERDO
        # ====================================================

        panel_izquierdo = ft.Container(

            width=290,

            padding=20,

            content=ft.Column(

                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.DEVICES,
                                size=25
                            ),

                            ft.Text(
                                "Destinos",
                                size=18,
                                weight=ft.FontWeight.BOLD
                            )
                        ]
                    ),

                    ft.Text(
                        "Cliente — IP:Puerto",
                        size=12
                    ),

                    ft.Divider(),

                    lista_destinos
                ],

                expand=True
            )
        )


        # ====================================================
        # PANEL DEL CHAT
        # ====================================================

        panel_chat = ft.Container(

            expand=True,

            padding=15,

            content=ft.Column(

                [
                    titulo_chat,

                    ft.Divider(),

                    mensajes,

                    ft.Row(
                        [
                            mensaje_input,
                            boton_enviar
                        ]
                    )
                ],

                expand=True
            )
        )


        # ====================================================
        # CONSTRUIR INTERFAZ
        # ====================================================

        contenido.controls.append(

            ft.Row(
                [
                    panel_izquierdo,

                    ft.VerticalDivider(
                        width=1
                    ),

                    panel_chat
                ],

                expand=True
            )
        )


        page.update()


        # ====================================================
        # HILO PARA RECIBIR MENSAJES
        # ====================================================

        hilo_escucha = threading.Thread(

            target=escuchar_mensajes,

            args=(
                recibir_mensaje,
            ),

            daemon=True
        )

        hilo_escucha.start()


        # ====================================================
        # HILO PARA ACTUALIZAR DESTINOS
        # ====================================================

        hilo_destinos = threading.Thread(

            target=actualizar_destinos_automaticamente,

            daemon=True
        )

        hilo_destinos.start()


        # ====================================================
        # PRIMERA CARGA DE DESTINOS
        # ====================================================

        cargar_destinos()


    # ========================================================
    # INICIAR
    # ========================================================

    mostrar_registro()


# ============================================================
# EJECUTAR APLICACIÓN
# ============================================================

try:

    ft.run(main)

except Exception as e:

    print()

    print("=" * 55)

    print(
        "ERROR EN LA APLICACIÓN"
    )

    print("=" * 55)

    print(e)