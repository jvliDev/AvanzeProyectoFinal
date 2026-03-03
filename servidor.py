import subprocess
import os
import signal
# Librerías añadidas para implementar seguridad (Cifrado y Validación Shadow nativa de Linux)
import ssl
import spwd
from passlib.hosts import linux_context

# --- CONFIGURACIÓN ---
# Escuchar en todas las interfaces disponibles
HOST = '0.0.0.0'
TCP_PORT = 5000
UDP_PORT = 5001

# [NUEVO] --- VALIDACIÓN NATIVA CON LINUX ---
def validar_usuario_linux(username, password):
    """
    Lee /etc/shadow para validar credenciales.
    Nota: Python necesita ejecutarse con permisos root.
    """
    try:
        # Obtiene la entrada de la base de contraseñas de Linux (/etc/shadow)
        entry = spwd.getspnam(username)
        # El hash cifrado real almacenado en el sistema
        hash_sistema = entry.sp_pwdp
        # Usamos passlib para verificar la contraseña interactiva 
        # contra el hash con sal de linux shadow ($y$, $6$, etc).
        return linux_context.verify(password, hash_sistema)
    except KeyError:
        # El usuario no existe en esta máquina Linux
        return False
    except PermissionError:
        print("[ERROR CRÍTICO] ¡El servidor debe ejecutarse con permisos sudo/root para leer usuarios reales!")
        return False

# --- TAREA 3: DESCUBRIMIENTO (UDP) ---
def responder_descubrimiento():
    # Creamos socket UDP
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Importante: Bind a '' permite escuchar en todas las IPs de la máquina
    udp.bind(('', UDP_PORT))
    
    while True:
        try:
            # Esperamos mensaje (buffer de 1024 bytes)
            msg, addr = udp.recvfrom(1024)
            mensaje_decodificado = msg.decode().strip()
            
            # Si alguien pregunta por el servidor...
            if mensaje_decodificado == "BUSCANDO_SERVIDOR":
                # Respondemos solo al que preguntó
                udp.sendto("SOY_SERVIDOR_RHEL".encode(), addr)
        except Exception as e:
            # Ignoramos errores de red momentáneos para no tumbar el servidor
            pass

# --- TAREA 1: GESTIÓN DE PROCESOS (SIN PSUTIL) ---
def obtener_procesos_nativos():
    """Obtiene la lista de procesos usando el comando 'ps' de Linux"""
    try:
        # Ejecutamos 'ps -e' para ver todos los procesos
        # -o pid,comm,stat: Solo queremos PID, Nombre y Estado
        cmd = ["ps", "-e", "-o", "pid,comm,stat"]
        salida = subprocess.check_output(cmd).decode()
        
        lista = []
        # Saltamos la primera linea (encabezados)
        lineas = salida.split('\n')[1:] 
        
        for linea in lineas:
            partes = linea.split()
            # Necesitamos que la línea tenga al menos 3 partes
            if len(partes) >= 3:
                info = {
                    "pid": int(partes[0]),
                    "name": partes[1],
                    "status": partes[2] 
                }
                lista.append(info)
            # Limitamos a 30 para no saturar la red
            if len(lista) >= 30: break 
        return lista
    except Exception as e:
        return [{"pid": 0, "name": f"Error leyendo ps: {str(e)}", "status": "?"}]

def ejecutar_orden(comando):
    accion = comando.get("accion")
    
    if accion == "LISTAR":
        return json.dumps(obtener_procesos_nativos())
    
    elif accion == "MATAR":
        try:
            pid = int(comando.get("pid"))
            # Usamos os.kill (nativo de Python/Linux) en lugar de psutil
            os.kill(pid, signal.SIGTERM)
            return f"Proceso {pid} terminado."
        except ProcessLookupError:
            return "Error: El proceso no existe."
        except PermissionError:
            return "Error: Sin permisos (¿Eres root?)."
        except Exception as e:
            return f"Error: {str(e)}"
            
    elif accion == "INICIAR":
        try:
            cmd = comando.get("cmd")
            # start_new_session=True evita que el proceso muera si cierras el servidor
            subprocess.Popen(cmd, shell=True, start_new_session=True)
            return f"Comando '{cmd}' iniciado."
        except Exception as e:
            return f"Error: {str(e)}"
            
    return "Comando desconocido"

# --- TAREA 2: SERVIDOR TCP ---
def manejar_cliente(conn, addr):
    print(f"[CONEXIÓN] Cliente conectado desde {addr}")
    # Variable de estado para controlar si el cliente actual inició sesión
    autenticado = False
    while True:
        try:
            data = conn.recv(4096).decode()
            if not data: break
            
            comando = json.loads(data)
            accion = comando.get("accion")
            
            # Verificar autenticación nativa de Red Hat
            if not autenticado:
                # Si la acción en el JSON es AUTENTICAR, verificamos las credenciales contra Linux
                if accion == "AUTENTICAR":
                    user = comando.get("user")
                    pwd = comando.get("pass")
                    # Pasamos los datos del cliente a la validación de contraseñas de Linux
                    if user and pwd and validar_usuario_linux(user, pwd):
                        autenticado = True
                        conn.send("Autenticación Exitosa. Sesión validada por Linux.".encode())
                    else:
                        conn.send("Error: Credenciales inválidas o servidor sin permisos root.".encode())
                else:
                    # Si intenta enviar otro comando sin iniciar sesión, devolvemos error.
                    conn.send("Error: No autenticado. Por favor inicie sesión primero.".encode())
                continue

            respuesta = ejecutar_orden(comando)
            conn.send(respuesta.encode())
        except:
            break
    conn.close()

if __name__ == "__main__":
    print("--- SERVIDOR ACTIVO (VERSIÓN NATIVA) ---")
    print(f"Escuchando TCP en puerto {TCP_PORT}")
    print(f"Escuchando UDP en puerto {UDP_PORT}")
    
    # Iniciamos el oído para el descubrimiento UDP en segundo plano
    t_udp = threading.Thread(target=responder_descubrimiento, daemon=True)
    t_udp.start()
    
    # Servidor principal TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reutilizar el puerto (SO_REUSEADDR) para evitar el error "Address already in use"
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, TCP_PORT))
    server.listen()
    
    # --- CONFIGURACIÓN SSL ---
    # Creamos un contexto SSL configurado para actuar como Servidor
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # Cargamos nuestros certificados autofirmados generados con OpenSSL
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    
    # Envolver el socket original TCP con una capa SSL
    server_ssl = context.wrap_socket(server, server_side=True)
    
    while True:
        # Aceptamos las conexiones mediante nuestro nuevo socket envuelto en SSL
        conn, addr = server_ssl.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr)).start()