from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from twisted.protocols import basic
from threading import Thread

from threading import Event

import queue

import sys
from pathlib import Path

import hashlib

download_threads = []

free_downloadthread_indices = []

command_client = None

download_path = "./downloads/"
download_subpath = "client_default"

max_download_files = 10
current_downloading = 0

def getDownloadCombinePath():
    global download_path
    global download_subpath
    return Path.joinpath(Path(download_path), Path(download_subpath))

class DownloadThread(Thread):
    def __init__(self, file_path, file_name, file_size, download_client):
        super().__init__()
        
        self.file_path = file_path
        self.file_name = file_name
        self.file_size = file_size
        self.saved_size = 0
        self.simple_queue = queue.SimpleQueue()
        self.finish_event = Event()

        self.md5sum = hashlib.md5()

        self.download_client = download_client

    def receiveData(self, data):
        self.simple_queue.put_nowait(data)

    def run(self):
        with open(self.file_path, "wb") as fp:
            while self.saved_size < self.file_size:
                recv_data = self.simple_queue.get()
                fp.write(recv_data)
                self.saved_size += len(recv_data)

                self.md5sum.update(recv_data)

        self.finish_event.set()
        print(f"Download {self.file_name} complete!!!")

        reactor.callFromThread(self.download_client.setChecksum, self.md5sum.digest())

class FileDownloadClient(basic.LineReceiver):
    def __init__(self, file_name):
        self.file_name = file_name
        self.file_size = 0
        self.file_data_received = 0

        self.checked_md5sum = None
        self.received_md5sum = None

    def compareChecksums(self):
        global current_downloading
        
        if self.checked_md5sum == self.received_md5sum:
            print(f"Verified {self.file_name} md5 successful!!")
            current_downloading -= 1
            self.transport.loseConnection()
        else:
            print(f"Verified {self.file_name} md5 failed!!")

    def setChecksum(self, in_md5sum):
        self.checked_md5sum = in_md5sum
        if self.received_md5sum is not None:
            self.compareChecksums()

    def lineReceived(self, line):
        str_line = line.decode()
        if str_line.startswith("error: "):
            print(str_line)
            self.transport.loseConnection()
        elif str_line.startswith("md5: "):
            hex_str = str_line[len("md5: "):]
            self.received_md5sum = bytes.fromhex(hex_str)
            
            if self.checked_md5sum is not None:
                self.compareChecksums()
        else:
            self.file_size = int(str_line)
            file_path = Path.joinpath(getDownloadCombinePath(), Path(self.file_name))
            if self.file_size != 0:
                self.download_thread = DownloadThread(file_path, self.file_name, self.file_size, self)
                self.setRawMode()

                self.download_thread.start()
            else:
                with open(file_path, "wb") as fp:
                    print("Download {self.file_name} complete!!!")

    def rawDataReceived(self, data):
        self.file_data_received += len(data)

        additional_data = b""
        save_data = None
        if self.file_data_received > self.file_size:
            exceed_size = self.file_data_received - self.file_size
            additional_data = data[len(data) - exceed_size:]
            save_data = data[:len(data) - exceed_size]

            self.file_data_received = self.file_size

        elif self.file_data_received == self.file_size:
            save_data = data
        else:
            save_data = data

        self.download_thread.receiveData(save_data)

        if self.file_data_received >= self.file_size:
            self.setLineMode(additional_data)

    def connectionMade(self):
        global current_downloading

        print("Issue file download: %s" % self.file_name)

        current_downloading += 1
        self.sendLine(b"download: %s" % self.file_name.encode())

class FileDownloadFactory(ClientFactory):
    def __init__(self, file_name):
        self.file_name = file_name

    def startedConnecting(self, connector):
        print('Download Started to connect.')

    def buildProtocol(self, addr):
        print('Download Connected.')
        return FileDownloadClient(self.file_name)

    def clientConnectionLost(self, connector, reason):
        print('Download Lost connection.  Reason:', reason)

    def clientConnectionFailed(self, connector, reason):
        print('Download Connection failed. Reason:', reason)

def SendCommandStr(str_line):
    command_client.sendLineStr(str_line)

def ConstructDownload(file_name):
    reactor.connectTCP("localhost", 1025, FileDownloadFactory(file_name))

def IssueDownloadFromThread(file_name):
    reactor.callFromThread(ConstructDownload, file_name)

def InputFunc():
    while True:
        str_in = input()
        if str_in.startswith("download: "):
            IssueDownloadFromThread(str_in[len("download: "):])
        else:
            if command_client is not None:
                reactor.callFromThread(SendCommandStr, str_in)

class CommandClient(basic.LineReceiver):
    def connectionMade(self):
        pass
        # self.sendLine(b"get_files_list")
        self.input_thread = Thread(target = InputFunc)
        self.input_thread.start()

    def lineReceived(self, line):
        str_line = line.decode()
        print(str_line)

    def sendLineStr(self, line_str):
        self.sendLine(line_str.encode())

class CommandClientFactory(ClientFactory):
    def startedConnecting(self, connector):
        print('Started to connect.')

    def buildProtocol(self, addr):
        print('Connected.')
        global command_client
        command_client = CommandClient()
        return command_client

    def clientConnectionLost(self, connector, reason):
        print('Lost connection.  Reason:', reason)

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed. Reason:', reason)

if __name__ == "__main__":
    host = "localhost"
    port = 1025
    reactor.connectTCP(host, port, CommandClientFactory())
    reactor.run()
