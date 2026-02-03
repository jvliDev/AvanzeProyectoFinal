import socket
import threading
import json
import subprocess
import os
import signal

# --- CONFIGURACIÓN ---
# Escuchar en todas las interfaces disponibles
HOST = '0.0.0.0'
TCP_PORT = 5000
UDP_PORT = 5001

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
    while True:
        try:
            data = conn.recv(4096).decode()
            if not data: break
            
            comando = json.loads(data)
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
    server.bind((HOST, TCP_PORT))
    server.listen()
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr)).start()