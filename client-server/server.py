import socket
from queue import Queue

class Server:
    def __init__(self,host, port):
        self.host = host
        self.port = port
        #we will use IPV4 and TCP protocol
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.cs, addr = serversocket.accept()
        print(f"Connection from {addr} has been established!")
    #send X,Y,Z and gripper state to robot
    def sendPosition(self,x, y, z, gripper_state, queue):
        data = f"{x},{y},{z},{gripper_state}\n"
        print(f"Sending data: ({data}) to robot.")
        self.cs.send(data.encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        queue.put(reply)

    #request camera
    def requestCameraData(self):
        self.cs.send("GET_CAMERA".encode('utf-8'))
        data = self.cs.recv(4096).decode('utf-8')#buffer for image data
        return data
    

    def sendHOme(self,queue):
        self.cs.send("HOME\n".encode('utf-8'))
        reply = self.cs.recv(128).decode('utf-8')
        queue.put(reply)

    def sendTermantion(self):
        self.cs.send("TERMINATE\n".encode('utf-8'))

    def sendEnableSafetyMode(self):
            self.cs.send("ENABLE_SAFETY\n".encode('utf-8'))
            reply = self.cs.recv(128).decode('utf-8')
            print(f"Safety Mode Enabled: {reply}")  
    def sendDisableSafetyMode(self):
            self.cs.send("DISABLE_SAFETY\n".encode('utf-8'))
            reply = self.cs.recv(128).decode('utf-8')
            print(f"Safety Mode Disabled: {reply}")
if __name__ == "__main__":
     host = "169.254.182.135"
     port = 9999
     server = Server(host,port)
     queue = Queue()

     server.sendDisableSafetyMode()
     server.sendPosition(10,20,30,1,queue)
     result = queue.get()
     print(f"Robot Reply: {result}")

     camera_data = server.requestCameraData()
     print(f"Camera data received: {camera_data}...")  

     server.sendTermination()
