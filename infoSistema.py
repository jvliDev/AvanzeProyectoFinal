import socket
import platform

host = socket.gethostname()
ip = socket.gethostbyname(host)
os_name = platform.system() + " " + platform.release()

print("\n")
print("      .=+*#%@@@@%#*+=.       Usuario: student@" + host)
print("   .=#@@@@@@@@@@@@@@@@#=.    -------------------------")
print("  +@@@@@@@@@@@@@@@@@@@@@@+   OS:   Red Hat Enterprise Linux")
print(" #@@@@@#*+=-:::-=+*#@@@@@@#  Host: " + host)
print(" @@@@+               +@@@@@  IP:   " + ip)
print(" @@@@.  PROYECTO     .@@@@@  Kernel: " + platform.release())
print(" #@@@@=-  FINAL   -=#@@@@@#  Estado: CONECTADO")
print("  *@@@@@@#*+=--=+*#@@@@@@* ")
print("   .+%@@@@@@@@@@@@@@@@%+.    ")
print("      .-+*#%@@@@%#*+-.       ")
print("\n")