# Reporte Técnico: Gestor de Procesos Remoto con Seguridad Nativa

Este documento describe la arquitectura técnica y el funcionamiento interno del software "Gestor de Procesos Remoto", el cual ha sido diseñado para operar nativamente en infraestructuras **Red Hat Enterprise Linux (RHEL)**. 

Se detallan a continuación los tres pilares de esta implementación: Autenticación, Seguridad Perimetral/Red y la Interfaz Gráfica de Usuario.

---

## 1. Integración de Autenticación Linux (PAM / Shadow)
El software no utiliza bases de datos propias para guardar contraseñas. Para cumplir con altos estándares de seguridad, el servidor valida el acceso utilizando exclusivamente cuentas de usuarios reales registradas en el sistema anfitrión.

### ¿Cómo funciona internamente?
- Cuando el servidor (`servidor.py`) recibe las credenciales enviadas por el cliente, utiliza la librería **`spwd`** de Python. 
- Esta librería tiene la capacidad de abrir y leer directamente el archivo `/etc/shadow`, el cual es el archivo core de Linux donde se guardan las contraseñas reales.
- Se extrae el *hash* de la contraseña almacenada junto con su *sal* criptográfica (el valor `$` dentro del string).
- Posteriormente, la librería **`passlib.hosts.linux_context`** toma la contraseña plana del cliente y la procesa criptográficamente usando el mismo algoritmo que el sistema base de Red Hat para determinar si "empatan".
- **Requisito Operativo**: Dado que `/etc/shadow` es un archivo crítico (protegido con permisos estandarizados dictados por SELinux), el script del servidor debe ejecutarse obligatoriamente bajo privilegios de superusuario (`sudo`).

---

## 2. Encriptación (TLS/SSL) y Descubrimiento
Todas las transacciones de red –incluido el propio login y el listado de procesos– están completamente cifradas.

### ¿Cómo funciona internamente?
- **Protocolo Base**: La aplicación usa Sockets que corren por el protocolo `TCP/IP` usando el puerto `5000`.
- **Certificados**: Se generaron localmente usando la herramienta *OpenSSL* un par de llaves: la llave privada (`key.pem`) y un certificado autofirmado X.509 (`cert.pem`).
- **Envoltorio TLS**:
  - Antes de que el socket TCP del servidor escuche información, se inicializa un objeto `ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)`.
  - Este objeto envuelve (hace un *Wrap* de) las comunicaciones. Las secuencias de bites viajan ofuscadas y el núcleo del cliente es el único que puede descifrarlas.
- **Descubrimiento UDP**: Para evitar que el cliente deba conocer la IP de antemano de memoria, la aplicación se comunica disparando un "grito de presencia" a la IP global `255.255.255.255` (Broadcast). Esto usa un socket tipo datagrama en el puerto UDP `5001`.

---

## 3. Interfaz Gráfica y Gestión en Tiempo Real (GUI)
El cliente fue modernizado desde una terminal hasta una aplicación gráfica basada en **Tkinter**, que además se ejecuta de forma pseudo-asíncrona.

### ¿Cómo funciona internamente?
- Se aplicó el paradigma de Programación Orientada a Objetos (OOP).
- **Control Asíncrono de Procesos (`after`)**: La ventana nunca se "congela" esperando que RHEL imprima los recursos en pantalla. Esto se debe a un ciclo asíncrono infinito declarado con `self.after(5000, request_listar_procesos)`. Esto significa que cada 5 segundos, el programa lanza la llamada `LISTAR` al modelo subyacente de manera transparente y purga el contenido del contenedor de la Tabla (`Treeview`).
- **Filtrado JSON**: La información en crudo viene del servidor empaquetada en formato JSON, con un array que contiene Diccionarios. El cliente de Tkinter *deserializa* este JSON y extrae únicamente PID, Nombre, y Status (*Running, Sleeping, Idle...*) para popular las columnas.
- **Log de Eventos**: Cada vez que el administrador hace clic en el botón *"Matar Seleccionado"* o *"Iniciar"*, la clase inserta la hora y la acción en tiempo real en un widget tipo `Text` ubicado en la parte inferior, proporcionando un canal de auditoría gráfica muy claro que permanece guardado en la memoria de la ventana para revisión posterior.
