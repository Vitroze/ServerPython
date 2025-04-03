import socket
import time

# Configuration du serveur
server_ip = "192.168.1.23"  # Remplace par l'IP du serveur
server_port = 12345

# Création du socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

print("Connecté au serveur.")

while True:

    sCommand = input("Entrez une commande (ou 'exit' pour quitter) : ")
    if sCommand.lower() == 'exit':
        break

    # Envoi de la commande au serveur
    client_socket.send(sCommand.encode())

    response = client_socket.recv(1024).decode()

    if len(response) == 0:
        continue 

    print(response)
