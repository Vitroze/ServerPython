import picorobotics
import utime
import usocket as socket
import network


station = network.WLAN(network.STA_IF)
station.active(True)
station.connect("Etudiant", "S@intPhilippe1515Neri")

iTimeOut = 100
while iTimeOut > 0:
    if station.status() >= 3:
        break;
    iTimeOut -= 1
    print("Waiting for Wi-Fi connection...")
    utime.sleep(1)

if station.status() != 3:
    raise RuntimeError('Failed to establish a network connection')
else:
    print('Connection successful!')
    network_info = station.ifconfig()
    print('IP address:', network_info[0])
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

server_ip = "172.16.14.95"  
server_port = 12345

# Création du socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

print("Connecté au serveur.")

board = picorobotics.KitronikPicoRobotics()

tAllAngles = [0] * 6

def readAngle(iServoMoteur):
    return tAllAngles[iServoMoteur - 1]

def writeAngle(iServoMoteur, iAngle):
    tAllAngles[iServoMoteur - 1] = iAngle

    board.servoWrite(iServoMoteur, iAngle)


csv_filename = "angles_servo.csv"

angles = ["0" for _ in range(6)]

data = {
    1: {"iMin": 0, "iMax": 120, "ini": 20}, # 30
    2: {"iMin": 0, "iMax": 70, "ini": 50},
    3: {"iMin": 0, "iMax": 180, "ini": 100}, # 100 
    4: {"iMin": 0, "iMax": 140, "ini": 100}, # 100
    5: {"iMin": 0, "iMax": 180, "ini": 100}, # 100
    6: {"iMin": 20, "iMax": 100, "ini": 20} # 20
}

def Clamp(iValue, iMin, iMax):
    if iValue > iMax:
        return iMax
    if iValue < iMin:
        return iMin
    return iValue

with open(csv_filename, mode='w') as file:
    file.write("Servo 1,Servo 2,Servo 3,Servo 4,Servo 5,Servo 6\n")

for key, value in data.items():
    if key == 2:
        continue 

    iMin = value["iMin"]
    iMax = value["iMax"]
    ini = value["ini"]

    angle = Clamp(ini, iMin, iMax)
   # board.servoWrite(key, angle)
    
    writeAngle(key, angle)

    print(f"Servo {key} initialisé à {angle}°")
    angles[key - 1] = str(angle)

    utime.sleep(0.1)

with open(csv_filename, mode='a') as file:
    file.write(",".join(angles) + "\n")

print("Positions initiales enregistrées.")

utime.sleep(3)

iStep = 1

while True:
   # iServoMoteur = int(input("Quel servomoteur vous voulez modifier ? "))
    sResponse = client_socket.recv(1024).decode()
    
    if sResponse == "":
        continue
    
    print("Réponse Serveur : ", sResponse)
    
    tData = sResponse.split("/")
    
    if len(tData) < 2:
        continue
    
    sCommand = tData[0]
    sArgs = tData[1] 
    
    if sCommand == "setangles":
        tDataCommand = sArgs.split(";")
        for sMessage in tData:
            tInfo = sMessage.split(":")
            iServoMoteur = int(tInfo[0])
            iAngle = int(tInfo[1])
            
            if iServoMoteur not in [1, 2, 3, 4, 5, 6]:
                print("Veuillez entrer un numéro de servomoteur valide.")
                continue

            #iAngle = int(input(f"L'angle du servo moteur n°{iServoMoteur} : "))
            iMin = data[iServoMoteur]["iMin"]
            iMax = data[iServoMoteur]["iMax"]
            iAngle = Clamp(iAngle, iMin, iMax)

          #  board.servoWrite(iServoMoteur, iAngle)
            
            writeAngle(iServoMoteur, iAngle)

            print(f"Servo {iServoMoteur} angle : {iAngle}°")

            # angles[iServoMoteur - 1] = str(iAngle)

            # with open(csv_filename, mode='a') as file:
            #     file.write(",".join(angles) + "\n")

            utime.sleep(0.5)
    elif sCommand == "sendmovement_servo":
        iTime = int(sArgs)
        print(f"Temps de mouvement : {iTime} secondes")

        sAllAngles = "sendmovement/"
        for i in range(1, 7):
            sAllAngles += f"{i}:{board.servoRead(i)};"

        sAllAngles += f"Time:{iTime}"

        print("Angles actuels : ", sAllAngles)

        client_socket.send(sAllAngles.encode())
    elif sCommand == "sendmovement":
        sNameFile = sArgs.split("\\")[0]
        tAllAngles = sArgs.split("\\")[1].split("|")
        iTime = int(tAllAngles[0].split(":")[2])
        print(f"Nom du fichier : {sNameFile}")
        print(f"Temps de mouvement : {iTime} secondes")

        for sMessage in tAllAngles:
            print(sMessage.split(":"))
            iServoMoteur = int(sMessage.split(":")[0])
            iAngle = int(sMessage.split(":")[1])
            if iServoMoteur not in [1, 3, 4, 5, 6]:
                print("Veuillez entrer un numéro de servomoteur valide.")
                continue

            writeAngle(iServoMoteur, iAngle)
            print(f"Servo {iServoMoteur} angle : {iAngle}°")

        print("Mouvement en cours...")
        utime.sleep(iTime)
        print("Mouvement terminé.")

        iStep += 1

        client_socket.send(f"loadmovement/{sNameFile}:{iStep}".encode())
        

    elif sCommand == "stop":
        iStep = 1

print(f"Données enregistrées dans {csv_filename}")
