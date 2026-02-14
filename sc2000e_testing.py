import socket

HOST = "192.168.1.1"
PORT = 5001

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
print("Listening on port", PORT)

conn, addr = s.accept()
print("Connected:", addr)

while True:
    data = conn.recv(1024)
    if not data:
        break
    print("OCR result:", data.decode())
