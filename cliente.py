import socket
import json
import time

# --- CONFIGURACIÓN ---
UDP_PORT = 5001
TCP_PORT = 5000

# --- TAREA 3: MIDDLEWARE / DESCUBRIMIENTO ---
def buscar_servidor_automaticamente():
    print("\n[BUSCANDO] Enviando señal broadcast a la red...")
    scanner = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Habilitar modo Broadcast
    scanner.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    scanner.settimeout(4) # Esperar máximo 4 segundos
    
    ips_encontradas = []
    
    try:
        # Enviar mensaje a TODA la red (255.255.255.255)
        mensaje = "BUSCANDO_SERVIDOR".encode()
        scanner.sendto(mensaje, ('<broadcast>', UDP_PORT))
        
        start_time = time.time()
        while time.time() - start_time < 4:
            try:
                resp, addr = scanner.recvfrom(1024)
                if resp.decode() == "SOY_SERVIDOR_RHEL":
                    print(f" -> ¡Servidor encontrado en {addr[0]}!")
                    if addr[0] not in ips_encontradas:
                        ips_encontradas.append(addr[0])
            except socket.timeout:
                break
    except Exception as e:
        print(f"Error en escaneo: {e}")
    finally:
        scanner.close()
    
    if ips_encontradas:
        return ips_encontradas[0] # Retorna la primera IP hallada
    else:
        print(" -> No se encontraron servidores automáticamente.")
        return None

# --- INTERFAZ DE USUARIO (CLI) ---
def menu():
    print("\n" + "="*40)
    print("   GESTOR DE PROCESOS REMOTO (RHEL)")
    print("="*40)
    print("1. Listar Procesos (Top 30)")
    print("2. Iniciar Programa (ej. firefox &)")
    print("3. Matar Proceso (por PID)")
    print("4. Salir")
    return input("Selecciona una opción: ")

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    ip_servidor = None
    
    # Paso 1: Intentar descubrimiento automático
    print("--- TAREA 3: Descubrimiento de Servicios ---")
    opcion = input("¿Buscar servidor automáticamente? (s/n): ").lower()
    
    if opcion == 's':
        ip_servidor = buscar_servidor_automaticamente()
    
    # Paso 2: Fallback manual
    if not ip_servidor:
        ip_servidor = input("\nIntroduce la IP del Servidor Manualmente: ")

    # Paso 3: Conexión TCP
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"\n[CONECTANDO] Intentando conectar a {ip_servidor}:{TCP_PORT}...")
        client.connect((ip_servidor, TCP_PORT))
        print("¡Conexión TCP Establecida!")
        
        while True:
            opc = menu()
            mensaje = {}
            
            if opc == '1':
                mensaje = {"accion": "LISTAR"}
            elif opc == '2':
                cmd = input("Comando a ejecutar (ej. 'gedit'): ")
                mensaje = {"accion": "INICIAR", "cmd": cmd}
            elif opc == '3':
                pid = input("PID del proceso a matar: ")
                mensaje = {"accion": "MATAR", "pid": pid}
            elif opc == '4':
                print("Cerrando cliente...")
                break
            else:
                print("Opción no válida.")
                continue
                
            # Enviar solicitud
            client.send(json.dumps(mensaje).encode())
            
            # Recibir respuesta
            respuesta_raw = client.recv(4096).decode()
            
            # Mostrar resultados
            if opc == '1':
                # Formatear la lista bonita
                datos = json.loads(respuesta_raw)
                print(f"\n{'PID':<8} {'NOMBRE':<25} {'ESTADO':<10}")
                print("-" * 45)
                for p in datos:
                    print(f"{p['pid']:<8} {p['name']:<25} {p['status']:<10}")
            else:
                print(f"\nRESPUESTA DEL SERVIDOR: {respuesta_raw}")

    except ConnectionRefusedError:
        print("ERROR: No se pudo conectar. Verifica que el servidor esté corriendo.")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        client.close()