# Reporte de Implementación de Seguridad: TLS/SSL y Autenticación

## 1. Introducción
Como parte de las mejoras al sistema de Gestión de Procesos Remoto, se implementaron dos capas fundamentales de seguridad para proteger la integridad y privacidad de las comunicaciones:
1. **Cifrado de la comunicación (TLS/SSL):** Para evitar que la información transmitida (como el listado de procesos o los comandos ejecutados) sea interceptada en texto plano por un atacante.
2. **Control de Acceso (Autenticación):** Para asegurar que un cliente forzosamente compruebe su identidad antes de permitirle enviar instrucciones al servidor.

---

## 2. Implementación de Cifrado (TLS/SSL)

### Generación de Certificados
Dado que el proyecto es una práctica escolar, se optó por utilizar certificados autofirmados generados de manera local utilizando la herramienta por línea de comandos `openssl`. Se generaron dos archivos esenciales en la criptografía asimétrica: `cert.pem` (el certificado público) y `key.pem` (la llave privada del servidor).

### Lado del Servidor (`servidor.py`)
Para habilitar el soporte seguro en el servidor, se importó la librería nativa `ssl` y se configuró el socket TCP tradicional para que sea "envuelto" por un contexto SSL de validación.
Adicionalmente, se configuró el socket con la bandera `SO_REUSEADDR` para evitar bloqueos del puerto tras cierres inesperados.

```python
import ssl

# [NUEVO] --- CONFIGURACIÓN SSL ---
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
```

### Lado del Cliente (`cliente.py`)
El cliente también fue modificado para comunicarse obligatoriamente a través de este canal encriptado. Debido a que nuestro certificado no está firmado por una Entidad Certificadora (CA) comercial, se programó el contexto SSL para que omita explícitamente la verificación del dominio ("hostname").

```python
import ssl

# [NUEVO] --- CONFIGURACIÓN SSL ---
context = ssl.create_default_context()
# Deshabilitar verificación del hostname y certificado 
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

try:
    print(f"\n[CONECTANDO] Intentando conectar a {ip_servidor}:{TCP_PORT}...")
    # Envolvemos nuestro socket conectándolo mediante TLS al nombre del servidor
    client = context.wrap_socket(client, server_hostname=ip_servidor)
    client.connect((ip_servidor, TCP_PORT))
    print("¡Conexión TCP Segura Establecida!")
```

---

## 3. Implementación de Autenticación de Usuarios

Para complementar el cifrado, se agregó una barrera lógica. Este mecanismo bloquea la ejecución de cualquier tarea del sistema operativo si la sesión del socket cliente no ha sido validada.

### Almacenamiento Seguro de Credenciales (Servidor)
Exponer las contraseñas en código claro es una terrible práctica de seguridad. Por ello, se importó la librería `hashlib`. Se estructuró un diccionario donde las claves son los usuarios y los valores son sus respectivas contraseñas hasheadas en **SHA-256**.

```python
import hashlib

# [NUEVO] --- USUARIOS (Usuario: SHA256(Contraseña)) ---
# Diccionario que simula una base de datos de usuarios. 
# Ejemplo -> "admin" : "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918" (hash en hexa)
USUARIOS = {
    "admin": hashlib.sha256("admin".encode()).hexdigest()
}
```

### Solicitud de Credenciales (Cliente)
Inmediatamente después del *"Handshake TLS"* exitoso, y previo a la carga de menú interactivo, el programa frena para solicitar la intervención del usuario:

```python
# [NUEVO] --- PASO 4: Autenticación ---
print("\n--- AUTENTICACIÓN ---")
user = input("Usuario: ")
pwd = input("Contraseña: ")

# Enviamos un mensaje JSON modificado incluyendo nuestros datos bajo la accion "AUTENTICAR".
auth_msg = {"accion": "AUTENTICAR", "user": user, "pass": pwd}
client.send(json.dumps(auth_msg).encode())

auth_resp = client.recv(4096).decode()
print(f"Respuesta Servidor: {auth_resp}")

# Si el servidor responde con "Error", forzamos el cierre de la conexión ("Kill-switch")
if "Error" in auth_resp:
    print("Cerrando cliente por error de autenticación...")
    client.close()
    exit(1)
```

### Validación y Estado en el Servidor (`servidor.py`)
El hilo que maneja a la conexión de un cliente ahora posee una variable de bandera por sesión aislada (`autenticado`). Mientras el valor sea `False`, todas las acciones (como "LISTAR" o "MATAR") estarán denegadas.

```python
    # [NUEVO] Variable de estado para controlar si el cliente actual inició sesión
    autenticado = False
    while True:
        data = conn.recv(4096).decode()
        comando = json.loads(data)
        accion = comando.get("accion")
        
        # [NUEVO] Verificar autenticación
        if not autenticado:
            # Si la acción en el JSON es AUTENTICAR, verificamos las credenciales
            if accion == "AUTENTICAR":
                user = comando.get("user")
                pwd = comando.get("pass")
                
                # Hasheamos la contraseña recibida y la cotejamos en tiempo real con nuestra 'Base de Datos'
                if user and pwd and user in USUARIOS and USUARIOS[user] == hashlib.sha256(pwd.encode()).hexdigest():
                    autenticado = True # ¡Aprobado! Cambiamos el estado del hilo de manera permanente
                    conn.send("Autenticación Exitosa".encode())
                else:
                    conn.send("Error: Credenciales inválidas".encode())
            else:
                # Cualquier otro comando sin antes enviar la acción AUTENTICAR genera este error.
                conn.send("Error: No autenticado. Por favor inicie sesión primero.".encode())
            continue
        
        # Si la bandera de autenticado es True, el bucle ignora la restricción y opera de manera normal.
        respuesta = ejecutar_orden(comando)
        conn.send(respuesta.encode())
```

## 4. Conclusión
La combinación de una capa de transporte envuelta de forma asimétrica (TLS/SSL) mediante OpenSSL y un modelo simplificado —pero robusto— de autenticación por hashes (algoritmo SHA-256) previene las amenazas más comunes de red (sniffing de carga útil) y restringe con éxito el uso del servidor subyacente blindando el entorno de ejecución de procesos ante clientes no autorizados.
