# Requisitos: psutil

import socket
import threading
import json
import psutil
import subprocess
import os

# --- CONFIGURACIÓN ---
HOST = '0.0.0.0'       # Escuchar en todas las interfaces
TCP_PORT = 5000        # Puerto para controlar procesos
UDP_PORT = 5001        # Puerto para ser descubierto
BUFFER_SIZE = 4096

# --- TAREA 3: DESCUBRIMIENTO DE SERVICIOS (UDP) ---
def responder_descubrimiento():
    """
    Escucha en el puerto UDP 5001. Si alguien grita 'BUSCANDO_SERVIDOR',
    responde 'SOY_SERVIDOR_RHEL' para que sepan mi IP.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(('', UDP_PORT))
    print(f"[UDP] Escuchando busquedas en puerto {UDP_PORT}...")
    
    while True:
        try:
            msg, addr = udp.recvfrom(1024)
            if msg.decode().strip() == "BUSCANDO_SERVIDOR":
                # Respondemos al cliente que nos buscó
                udp.sendto("SOY_SERVIDOR_RHEL".encode(), addr)
        except Exception as e:
            print(f"[UDP Error] {e}")

# --- TAREA 1: GESTIÓN DE PROCESOS (Lógica del Sistema) ---
def ejecutar_orden(comando):
    """Recibe un diccionario (JSON) y ejecuta la acción en el SO"""
    accion = comando.get("accion")
    
    if accion == "LISTAR":
        # Devuelve los procesos activos (limitado a 20 para no saturar)
        lista = []
        for p in psutil.process_iter(['pid', 'name', 'status']):
            try:
                lista.append(p.info)
            except:
                pass
            if len(lista) >= 30: break 
        return json.dumps(lista)
    
    elif accion == "MATAR":
        try:
            pid = int(comando.get("pid"))
            proceso = psutil.Process(pid)
            proceso.terminate()
            return f"Proceso {pid} terminado exitosamente."
        except psutil.NoSuchProcess:
            return f"Error: El proceso {pid} no existe."
        except psutil.AccessDenied:
            return f"Error: No tienes permiso para matar al proceso {pid}."
        except Exception as e:
            return f"Error desconocido: {str(e)}"
            
    elif accion == "INICIAR":
        try:
            cmd = comando.get("cmd")
            # subprocess.Popen lanza el proceso y no bloquea el servidor
            subprocess.Popen(cmd, shell=True)
            return f"Comando '{cmd}' lanzado en segundo plano."
        except Exception as e:
            return f"Error al iniciar: {str(e)}"
            
    return "Comando no reconocido"

# --- TAREA 2: SERVIDOR TCP (Conexión Cliente-Servidor) ---
def manejar_cliente(conn, addr):
    print(f"[TCP] Cliente conectado desde: {addr}")
    while True:
        try:
            data = conn.recv(BUFFER_SIZE).decode()
            if not data: break
            
            # Procesar el comando recibido
            comando = json.loads(data)
            respuesta = ejecutar_orden(comando)
            
            # Enviar la respuesta de vuelta
            conn.send(respuesta.encode())
        except ConnectionResetError:
            break
        except Exception as e:
            print(f"[TCP Error] {e}")
            break
            
    conn.close()
    print(f"[TCP] Cliente desconectado: {addr}")

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    print("--- INICIANDO SERVIDOR DE SISTEMAS OPERATIVOS ---")
    
    # 1. Iniciar el hilo de descubrimiento (Segundo plano)
    hilo_udp = threading.Thread(target=responder_descubrimiento, daemon=True)
    hilo_udp.start()
    
    # 2. Iniciar el servidor principal TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, TCP_PORT))
    server.listen()
    print(f"[TCP] Servidor listo y esperando órdenes en puerto {TCP_PORT}...")
    
    while True:
        conn, addr = server.accept()
        # Cada cliente se maneja en un hilo separado
        threading.Thread(target=manejar_cliente, args=(conn, addr)).start()