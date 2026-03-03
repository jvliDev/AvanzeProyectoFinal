import socket
import json
import ssl
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from datetime import datetime
import time
import threading

# --- CONFIGURACIÓN ---
UDP_PORT = 5001
TCP_PORT = 5000

class GestorProcesosGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Gestor de Procesos Remoto Seguro (RHEL)")
        self.geometry("800x600")
        self.configure(bg="#f4f4f4")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Variables de red
        self.client_socket = None
        self.ip_servidor = tk.StringVar()
        self.usuario = tk.StringVar()
        self.password = tk.StringVar()
        
        # Control de Auto-Refresco
        self.refresh_job = None
        
        # Iniciar Pantalla de Login
        self.crear_pantalla_login()

    # ===============================
    # PANTALLA DE LOGIN
    # ===============================
    def crear_pantalla_login(self):
        self.frame_login = tk.Frame(self, bg="#ffffff", padx=40, pady=40, relief=tk.RAISED, borderwidth=2)
        self.frame_login.pack(expand=True)
        
        tk.Label(self.frame_login, text="🔐 Conexión Segura (TLS)", font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=(0, 20))
        
        tk.Label(self.frame_login, text="IP del Servidor:", bg="#ffffff").pack(anchor="w")
        tk.Entry(self.frame_login, textvariable=self.ip_servidor, width=30).pack(pady=(0, 10))
        
        tk.Label(self.frame_login, text="Usuario:", bg="#ffffff").pack(anchor="w")
        tk.Entry(self.frame_login, textvariable=self.usuario, width=30).pack(pady=(0, 10))
        
        tk.Label(self.frame_login, text="Contraseña:", bg="#ffffff").pack(anchor="w")
        tk.Entry(self.frame_login, textvariable=self.password, show="*", width=30).pack(pady=(0, 20))
        
        # Botones de Login
        btn_frame = tk.Frame(self.frame_login, bg="#ffffff")
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Descubrir Red", command=self.buscar_servidor_gui, bg="#e0e0e0").pack(side=tk.LEFT, expand=True, padx=5)
        self.btn_conectar = tk.Button(btn_frame, text="Conectar", command=self.conectar_y_autenticar, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_conectar.pack(side=tk.RIGHT, expand=True, padx=5)

    def buscar_servidor_gui(self):
        """Versión adaptada del descubrimiento UDP que bloquea momentaneamente y rellena la IP"""
        self.btn_conectar.config(state=tk.DISABLED)
        self.update()
        
        def tarea_descubrimiento():
            scanner = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            scanner.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            scanner.settimeout(3)
            ip_hallada = ""
            try:
                scanner.sendto("BUSCANDO_SERVIDOR".encode(), ('<broadcast>', UDP_PORT))
                resp, addr = scanner.recvfrom(1024)
                if resp.decode() == "SOY_SERVIDOR_RHEL":
                    ip_hallada = addr[0]
            except:
                pass
            finally:
                scanner.close()
                
            # Volver al hilo principal para actualizar GUI
            self.after(0, self._resultado_descubrimiento, ip_hallada)
            
        threading.Thread(target=tarea_descubrimiento, daemon=True).start()

    def _resultado_descubrimiento(self, ip_hallada):
        self.btn_conectar.config(state=tk.NORMAL)
        if ip_hallada:
            self.ip_servidor.set(ip_hallada)
            messagebox.showinfo("Búsqueda", f"Servidor encontrado en: {ip_hallada}")
        else:
            messagebox.showwarning("Búsqueda", "No se encontraron servidores en la red local.")

    def conectar_y_autenticar(self):
        ip = self.ip_servidor.get().strip()
        user = self.usuario.get().strip()
        pwd = self.password.get().strip()
        
        if not ip or not user or not pwd:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            self.client_socket = context.wrap_socket(sock, server_hostname=ip)
            self.client_socket.settimeout(5) # 5 Segundos de timeout p/ evitar cuelgues de GUI
            self.client_socket.connect((ip, TCP_PORT))
            self.client_socket.settimeout(None) # Remueve timeout para operación normal
            
            # Auth
            auth_msg = {"accion": "AUTENTICAR", "user": user, "pass": pwd}
            self.client_socket.send(json.dumps(auth_msg).encode())
            auth_resp = self.client_socket.recv(4096).decode()
            
            if "Error" in auth_resp:
                self.client_socket.close()
                messagebox.showerror("Autenticación Fallida", auth_resp)
            else:
                # Login Correcto -> Transición a Dashboard
                self.frame_login.destroy()
                self.crear_pantalla_dashboard()
                self.escribir_log("✅ Conexión Segura TLS establecida. Sistema Autenticado.")
                self.request_listar_procesos() # Primera carga

        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar al servidor:\n{str(e)}")
            if self.client_socket:
                self.client_socket.close()

    # ===============================
    # PANTALLA DASHBOARD
    # ===============================
    def crear_pantalla_dashboard(self):
        # Frame Superior: Controles
        frame_top = tk.Frame(self, bg="#f4f4f4", pady=10, padx=10)
        frame_top.pack(fill=tk.X)
        
        tk.Label(frame_top, text="🖥️ Servidor RHEL", font=("Arial", 12, "bold"), bg="#f4f4f4").pack(side=tk.LEFT)
        
        self.btn_refrescar = tk.Button(frame_top, text="🔄 Refrescar", command=self.request_listar_procesos)
        self.btn_refrescar.pack(side=tk.LEFT, padx=10)
        
        tk.Label(frame_top, text="Lanzar Prog.:", bg="#f4f4f4").pack(side=tk.LEFT, padx=(20, 5))
        self.entrada_cmd = tk.Entry(frame_top, width=15)
        self.entrada_cmd.pack(side=tk.LEFT)
        tk.Button(frame_top, text="Iniciar", command=self.request_iniciar_proceso, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_top, text="💀 Matar Seleccionado", command=self.request_matar_proceso, bg="#F44336", fg="white").pack(side=tk.RIGHT)
        
        # Frame Central: Tabla de Procesos
        frame_mid = tk.Frame(self, padx=10, bg="#f4f4f4")
        frame_mid.pack(expand=True, fill=tk.BOTH)
        
        # Treeview (Tabla)
        columnas = ("pid", "name", "status")
        self.tree = ttk.Treeview(frame_mid, columns=columnas, show="headings", selectmode="browse")
        self.tree.heading("pid", text="PID")
        self.tree.heading("name", text="Nombre del Proceso")
        self.tree.heading("status", text="Estado")
        
        self.tree.column("pid", width=80, anchor=tk.CENTER)
        self.tree.column("name", width=350)
        self.tree.column("status", width=100, anchor=tk.CENTER)
        
        # Scrollbar para la tabla
        scrollbar = ttk.Scrollbar(frame_mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame Inferior: Log de Actividades
        frame_bot = tk.Frame(self, padx=10, pady=10, bg="#f4f4f4")
        frame_bot.pack(fill=tk.BOTH)
        
        tk.Label(frame_bot, text="📋 Registro de Actividades:", bg="#f4f4f4").pack(anchor="w")
        
        self.caja_logs = ScrolledText(frame_bot, height=6, bg="#ffffff", state=tk.DISABLED)
        self.caja_logs.pack(expand=True, fill=tk.BOTH)
        
        # Status Bar Inferior
        self.lbl_estado = tk.Label(self, text="  Estado: Conectado y Monitorizando...", bg="#dcdcdc", anchor="w")
        self.lbl_estado.pack(side=tk.BOTTOM, fill=tk.X)


    # ===============================
    # RED Y LÓGICA
    # ===============================
    def escribir_log(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        msg_formateado = f"[{hora}] {mensaje}\n"
        
        self.caja_logs.config(state=tk.NORMAL)
        self.caja_logs.insert(tk.END, msg_formateado)
        self.caja_logs.see(tk.END) # Scroll automático
        self.caja_logs.config(state=tk.DISABLED)

    def enviar_recv(self, payload):
        """Método utilitario para peticiones de red sin crashear GUI"""
        try:
            self.client_socket.send(json.dumps(payload).encode())
            return self.client_socket.recv(16384).decode()
        except Exception as e:
            self.escribir_log(f"❌ Error de red: {e}")
            return None

    def request_listar_procesos(self):
        # Cancelar cualquier auto-refresco pendiente para evitar doble llamado
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
            
        respuesta = self.enviar_recv({"accion": "LISTAR"})
        if respuesta:
            try:
                datos = json.loads(respuesta)
                # Limpiar tabla vieja
                for row in self.tree.get_children():
                    self.tree.delete(row)
                
                # Poblar tabla nueva
                for p in datos:
                    self.tree.insert("", tk.END, values=(p['pid'], p['name'], p['status']))
                    
                self.lbl_estado.config(text=f"  Monitoreo: Última actualización {datetime.now().strftime('%H:%M:%S')} - {len(datos)} procesos listados.")
            except json.JSONDecodeError:
                self.escribir_log("⚠️ Error parseando lista de procesos.")
        
        # Programar el siguiente refresco automático en 5000 ms (5 segundos)
        self.refresh_job = self.after(5000, self.request_listar_procesos)

    def request_iniciar_proceso(self):
        cmd = self.entrada_cmd.get().strip()
        if not cmd:
            return
            
        self.escribir_log(f"⚙️ Solicitando inicio de: '{cmd}'")
        resp = self.enviar_recv({"accion": "INICIAR", "cmd": cmd})
        if resp:
            self.escribir_log(f"Respuesta: {resp}")
            self.entrada_cmd.delete(0, tk.END)
            self.request_listar_procesos() # Refresca instantaneamente
            
    def request_matar_proceso(self):
        item_select = self.tree.selection()
        if not item_select:
            messagebox.showwarning("Aviso", "Selecciona un proceso de la tabla primero.")
            return
            
        valores = self.tree.item(item_select[0], 'values')
        pid_seleccionado = valores[0]
        nombre_sel = valores[1]
        
        if messagebox.askyesno("Confirmar", f"¿Estás seguro de matar el proceso {nombre_sel} (PID: {pid_seleccionado})?"):
            self.escribir_log(f"⚠️ Solicitando terminación de PID {pid_seleccionado} ({nombre_sel})")
            resp = self.enviar_recv({"accion": "MATAR", "pid": pid_seleccionado})
            if resp:
                self.escribir_log(f"Respuesta: {resp}")
                self.request_listar_procesos()

    def on_close(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.destroy()

if __name__ == "__main__":
    app = GestorProcesosGUI()
    app.mainloop()