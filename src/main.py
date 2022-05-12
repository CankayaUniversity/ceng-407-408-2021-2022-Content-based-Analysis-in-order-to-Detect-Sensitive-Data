from threading import Thread
import socket
import sys
import os
import logging
import tensorflow_text
import tensorflow
import msg_parser
import params

class SocketThread(Thread):
    def __init__(self, client_socket, addr, model):
        super().__init__()
        self.client_socket = client_socket
        self.addr = addr
        self.model = model
    def receive(self):
        data = client_socket.recv(1024).decode()
        msg_fpath = str(data).rstrip()
        self.msg_path = os.path.join(params.EML_MOUNT, msg_fpath.rsplit('/', 1)[-1])
    def send(self):
        ret_code = msg_parser.parse(self.msg_path, model)
        if ret_code == 0:
            msg = "ok\r\n"
        else:
            msg = "Mail Cannot Forward!\r\n"
        self.client_socket.send(msg.encode("ascii"))
        self.client_socket.close()
    def run(self):
        self.receive()
        self.send()

if __name__ == "__main__":
    logging.basicConfig(format = "%(asctime)s - %(message)s", filemode = 'a', level = logging.DEBUG)
    model = tensorflow.keras.models.load_model(params.MODEL_PATH)
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        serversocket.bind((params.HOST, params.PORT))
    except:
        sys.exit(1)
    serversocket.listen(params.MAX_REQUESTS)
    while True:
        logging.info("Server is waiting for port %s", params.PORT)
        client_socket, addr = serversocket.accept()
        sock_thread = SocketThread(client_socket, addr, model)
        sock_thread.start()
