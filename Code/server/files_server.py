from twisted.internet import reactor
import sys, os

from threading import Lock
from threading import Thread
from pathlib import Path

from twisted.application import internet, service
from twisted.internet import protocol
from twisted.protocols import basic

import hashlib
import argparse
import time

a_lock = Lock()

files_list = []

files_path = ""

def watch(file_path):
    global files_list
    global a_lock

    entries = Path(file_path)
    new_list = []
    for entry in entries.iterdir():
        new_list.append(entry.name)
    if files_list != new_list:
        with a_lock:
            files_list = new_list
        for file_name in new_list:
            print(file_name)
        print(f"{file_path} has been changed!!!")

class FileReadThread(Thread):
    def __init__(self, file_server, file_path, chunk_size = 256):
        super().__init__()

        self.file_server = file_server
        self.file_path = file_path
        self.chunk_size = chunk_size

        self.md5sum = hashlib.md5()

    def run(self):
        with open(self.file_path, "rb") as file:
            while True:
                data = file.read(self.chunk_size)
                if data:
                    self.md5sum.update(data)
                    reactor.callFromThread(self.file_server.sendData, data)
                else:
                    reactor.callFromThread(self.file_server.setMD5Checksum, self.md5sum.digest())
                    break

class FileServer(basic.LineReceiver):
    def connectionMade(self):
        print("New client come!")
        self.factory.clients.append(self)

    def connectionLost(self, reason):
        print("Client lost!")
        self.factory.clients.remove(self)

    def sendLineStr(self, str):
        self.sendLine(str.encode())

    def lineReceived(self, line):
        global files_list
        global a_lock
        str_line = line.decode()
        print("received: ", str_line)

        if str_line == "get_files_list":
            file_str_list = "file_list: "
            new_file_list = []
            with a_lock:
                new_file_list = files_list
            for file_name in new_file_list:
                file_str_list += "\r\n"
                file_str_list += file_name
            
            self.sendLineStr(file_str_list)
        elif str_line.startswith("download: "):
            file_name = str_line[len("download: "): ]
            file_path = Path.joinpath(Path(files_path), Path(file_name))
            file_size = 0
            self.download_file_name = file_name
            try:
                file_stat_p = os.stat(file_path)
                file_size = file_stat_p.st_size
                print(f"download: {file_name}, size: {file_size}")
                self.sendLineStr(repr(file_size))
                if file_size > 0:
                    self.file_read_thread = FileReadThread(file_server = self, file_path = file_path)
                    self.file_read_thread.start()
            except FileNotFoundError:
                print("File not found: %s" % file_path)
                self.sendLineStr("error: File not found")
            except:
                print("Other error: %" % file_path)
                self.sendLineStr("error: Other file error")

    def setMD5Checksum(self, md5_data):
        str_sent = "md5: "
        md5_str = md5_data.hex()
        str_sent += md5_str
        self.sendLineStr(str_sent)

        print(f"{self.download_file_name} md5 is {md5_str}")

    def sendData(self, data):
        self.transport.write(data)

if __name__ == "__main__":
    factory = protocol.ServerFactory()
    factory.protocol = FileServer
    factory.clients = []

    port = 1025
    files_path = "./file_hosted/"

    parser = argparse.ArgumentParser(description='Files server.')
    parser.add_argument('-f', '--files_path', default=files_path)
    parser.add_argument('-p', '--port', default=port)

    args = parser.parse_args()
    port = args.port
    files_path = args.files_path

    top_service = service.MultiService()
    tcp_service = internet.TCPServer(1025, factory)
    tcp_service.setServiceParent(top_service)

    watch(files_path)
    s = internet.TimerService(0.5, watch, files_path)
    s.setServiceParent(top_service)

    top_service.startService()
    reactor.run()
    top_service.stopService()