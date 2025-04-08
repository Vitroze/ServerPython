import socket
import select
import re
import os

HOST = "0.0.0.0" 
PORT = 12345

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

sockets_list = [server_socket]
clients = {}

sIPReseau = socket.gethostbyname(socket.gethostname())
print(f"Serveur en attente de connexions sur {HOST}:{PORT}...")
print(f"Serveur en attente de connexions sur {sIPReseau} (Réseau)")

tWhiteListIP = [
    "192.168.1.23",
    "172.16.14.249",
    "172.16.15.95",
    "172.16.14.95",
    "172.16.13.55"
]

sIPServo = "172.16.15.95"
eServoMoteur = None

def remove_client(s):
    if s in sockets_list:
        sockets_list.remove(s)
    if s in clients:
        s.close()
        del clients[s]

def sendMessage(s, message):
    try:

        if s == "all":
            for client in sockets_list:
                if client != server_socket:
                    client.send(f"[{sIPReseau} - Serveur]: {message}".encode())
        elif s == "servo":
            if eServoMoteur is not None:
                eServoMoteur.send(message.encode())
        else:
            if s in sockets_list:
                s.send(f"[{sIPReseau} - Serveur]: {message}".encode())

    except Exception as e:
        print(f"Erreur lors de l'envoi du message : {e}")

def saveFile(sFileName, tData):
    try:
        with open(sFileName, "w") as f:
            f.write("Step;Servo;Angle;Time\n")
            
            for i in range(len(tData)):
                line = tData[i].strip()
                f.write(f"{line}\n")
        print(f"Fichier {sFileName} enregistré avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du fichier : {e}")

tTempSave = []

def Min(a, b):
    if a < b:
        return a
    return b

def Max(a, b):
    if a > b:
        return a
    return b

iStepSave = 1
sOnMoveSave = ""
while True:
    try:
        readable, _, _ = select.select(sockets_list, [], [], 0.1)

        for s in readable:
            if s is server_socket:
                client_socket, client_addr = server_socket.accept()
                sockets_list.append(client_socket)
                clients[client_socket] = client_addr
                print(f"Nouvelle connexion de {client_addr}")

                if client_addr[0] not in tWhiteListIP:
                    print(f"Connexion refusée de {client_addr} (IP non autorisée)")

                    sendMessage(client_socket, f"Connexion refusée : IP non autorisée. Si vous pensez que c'est une erreur, veuillez contacter administrateur du serveur (Yanis)")

                    remove_client(client_socket)

                    continue
            
                if client_addr[0] == sIPServo:
                    print(f"Connexion du servo moteur {client_addr}")
                    eServoMoteur = client_socket
                    sendMessage(client_socket, "Vous êtes connecté en tant que servo moteur.")

            else:
                try:
                    message = s.recv(1024).decode()
                    if message:
                        print(f"Message reçu de {clients[s]} : {message}")

                        sCommand = message.split("/")[0].lower().strip()
                        if sCommand == "help":
                            response = "Liste des commandes disponibles :\n"
                            response += "help/ - Afficher la liste de commandes\n"
                            response += "setangles/{ServoN}:{Angle} - Définir l'angle du servo {ServoN}. Infini argument pour le servo N (Exemple : setangles/1:45;2:80\n"
                            response += "sendmovement{ServoN}:{Angle};Time:{iTime} - Envoyer un mouvement du servomoteur au serveur {ServoN} avec l'angle {Angle} et le temps {iTime} en secondes. Seulement pour le servomoteur\n"
                            response += "sendmovement_servo/{iTime} - Envoyer un mouvement au servo moteur avec le temps {iTime} en secondes\n"
                            response += "savemovement/{Nom} - Enregistrer le mouvement avec le nom {Nom} | Arrête la séquence de l'enregistrement des mouvements \n"
                            response += "loadmovement/{Nom}:{Instruction} - Charger le mouvement avec le nom {Nom} ; {Instruction} : 1, ... est le numéro de l'étape à charger\n"
                            response += "listmovement/ - Lister les mouvements enregistrés\n"
                            response += "exit/ - Quitter le serveur\n"
                                                        
                            sendMessage(s, response)

                            continue              
                        elif sCommand == "setangles":
                            if eServoMoteur is None:
                                print("Erreur : Pas de connexion au servo moteur.")
                                sendMessage(s, "Erreur : Pas de connexion au servo moteur.")
                                continue

                            if len(message.split("/")) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue

                            if s == eServoMoteur:
                                continue

                            sendMessage("servo", message)
                        elif sCommand == "savemovement":
                            if len(tTempSave) == 0:
                                sendMessage(s, "Erreur : Pas de mouvement à enregistrer.")
                                continue

                            if len(message.split("/")) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue

                            sName = message.split("/")[1].strip()
                            if sName == "":
                                sendMessage(s, "Erreur : Nom vide.")
                                continue

                            # .csv
                            sName = re.sub(r"[^a-zA-Z0-9_]", "_", sName) 
                            sName = re.sub(r"_{2,}", "_", sName)
                            
                            if not sName.endswith(".csv"):
                                sName += ".csv"

                            sFileName = f"{sName}"

                            saveFile(sFileName, tTempSave)

                            tTempSave = []
                            iStepSave = 1

                        elif sCommand == "sendmovement":
                            if eServoMoteur is None:
                                print("Erreur : Pas de connexion au servo moteur.")
                                sendMessage(s, "Erreur : Pas de connexion au servo moteur.")
                                continue

                            if len(message.split("/")) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue
                            
                            if eServoMoteur != s:
                                print("Erreur : Seul le servomoteur est autorisé à utilisé cette commande")
                                sendMessage(s, "Erreur : Seul le servomoteur est autorisé à utilisé cette commande")
                                
                                continue

                            tArgs = message.split("/")[1].split(";")
                            
                            if len(tArgs) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue

                            iTime = tArgs[-1].strip()
                            iTime = iTime.split(":")[1].strip()

                            if not iTime.isdigit():
                                sendMessage(s, "Erreur : Argument non valide.")
                                continue

                            for i in range(len(tArgs) - 1):
                                if i == len(tArgs) - 1:
                                    continue

                                tArgs[i] = tArgs[i].strip()
                                if tArgs[i] == "":
                                    sendMessage(s, "Erreur : Argument vide.")
                                    continue

                                # f"{ServoN}:{Angle}"
                                iServo = tArgs[i].split(":")[0].strip()
                                iAngle = tArgs[i].split(":")[1].strip()
                                if iServo == "" or iAngle == "" or not iServo.isdigit() or not iAngle.isdigit():
                                    sendMessage(s, "Erreur : Argument vide ou invalide.")
                                    continue

                                tTempSave.append(f"{iStepSave};{iServo};{iAngle};{iTime}")

                            iStepSave += 1

                            print(f"tempSave : {tTempSave}")

                            print(f"Enregistrement du mouvement : {tTempSave}")
                            

                        elif sCommand == "loadmovement": 
                            if eServoMoteur is None:
                                print("Erreur : Pas de connexion au servo moteur.")
                                sendMessage(s, "Erreur : Pas de connexion au servo moteur.")
                                continue

                            if len(message.split("/")) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue


                            tArgs = message.split("/")[1].split(":")
                            if len(tArgs) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue

                            sName = tArgs[0].strip()
                            if sName == "":
                                sendMessage(s, "Erreur : Nom vide.")
                                continue
                            
                            if sName != "" and sName != sOnMoveSave:
                                print("Un mouvement est déjà en cours, veuillez essayer a la fin du mouvement")
                                
                                continue
                            
                            sOnMoveSave = sName
                            if not sName.endswith(".csv"):
                                sName += ".csv"

                            iLine = tArgs[1].strip()
                            if iLine == "":
                                sendMessage(s, "Erreur : Ligne vide.")
                                continue

                            with open(sName, "r") as f:
                                tMovements = f.readlines()

                                sText = ""
                                for i in range(len(tMovements)):
                                    tData = tMovements[i].strip().split(";")

                                    if tData[0] == "Step":
                                        continue

                                    if tData[0] == iLine:
                                        sText += f"{tData[1]}:{tData[2]}:{tData[3]}|"

                                if len(sText) == 0:
                                    sendMessage("servo", f"stop/")
                                    sOnMoveSave = ""

                                    continue

                                sText = sText[:-1] 

                                print(f"sendmovement/{sName}\{sText}")

                                sendMessage("servo", f"sendmovement/{sName}\{sText}")

                        elif sCommand == "listmovement":

                            sText = ""

                            for sFile in os.listdir("."):
                                if sFile.endswith(".csv"):
                                    sFile = sFile.replace(".csv", "")
                                    
                                    with open(sFile + ".csv", "r") as f:
                                        lines = f.readlines()
                                        if len(lines) > 1:
                                            sText += f"* {sFile} ({len(lines) - 1} mouvements/lignes)\n"
                                        else:
                                            sText += f"* {sFile} (0 mouvement/lignes)\n"
                            
                            if sText == "":
                                sText = "Aucun mouvement enregistré."

                            else:
                                sText = "Mouvements enregistrés :\n" + sText

                            sendMessage(s, sText)
                            
                                
                        elif sCommand == "exit":
                            print(f"Client {clients[s]} a quitté.")
                            
                            remove_client(s)

                        elif sCommand == "sendmovement_servo":
                            if eServoMoteur is None:
                                print("Erreur : Pas de connexion au servo moteur.")
                                sendMessage(s, "Erreur : Pas de connexion au servo moteur.")
                                continue

                            if len(message.split("/")) < 2:
                                sendMessage(s, "Erreur : Pas d'arguments fournis.")
                                continue

                            iTime = message.split("/")[1].strip()

                            if iTime == "":
                                sendMessage(s, "Erreur : Argument vide.")
                                continue

                            if not iTime.isdigit():
                                sendMessage(s, "Erreur : Argument non valide.")
                                continue

                            sendMessage("servo", f"sendmovement_servo/{iTime}")
                        else:
                            sendMessage(s, f"Commande Inconnu ({message})")

                    else:
                        print(f"Client {clients[s]} déconnecté")
                        
                        remove_client(s)

                except ConnectionResetError:
                    print(f"Erreur : Connexion interrompue avec {clients[s]}")
                    
                    remove_client(s)

                except Exception as e:
                    print(f"Erreur : {e}")
                    remove_client(s)

    except KeyboardInterrupt:
        print("Arrêt du serveur.")
        break

for s in sockets_list:
    s.close()
