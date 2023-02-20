from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from twisted.protocols import basic
from threading import Thread

from threading import Event

import queue

import sys
from pathlib import Path

import hashlib
import argparse
import time

download_threads = []

free_downloadthread_indices = []

command_client = None

download_path = "./downloads/"
download_subpath = "client_default"

max_download_files = 10
current_downloading = 0

host = "localhost"
port = 1025

is_test_download = False

test_download_files_list = [
    #"file_128.bin",
    "file_1m.bin",
    #"file_2k.bin",
    "file_128k.bin",
    "file_32k.bin",
    "file_4k.bin",
    "file_4m.bin",
    "file_8k.bin",
    #"file_512.bin",
    "file_512k.bin",
    "file_16k.bin",
    "file_64k.bin",
    "file_2m.bin"
]

test_speed = 0

test_count = 0

total_count = len(test_download_files_list)

test_run_count = 0
test_run_total = 4

test_accume_speed = 0

def displayMsg(msg):
    global is_test_download
    if not is_test_download:
        print(msg)

def getDownloadCombinePath():
    global download_path
    global download_subpath
    return Path.joinpath(Path(download_path), Path(download_subpath))

def accumeAndCheckDownloadComplete(a_speed):
    global test_speed
    global test_count
    global total_count
    global test_accume_speed
    global test_run_count
    global test_run_total

    test_speed += a_speed
    test_count += 1

    if test_count == total_count:
        avg_speed = test_speed/ total_count

        test_count = 0
        test_speed = 0

        test_run_count += 1
        test_accume_speed += avg_speed
        if test_run_count == test_run_total:
            accume_avg_speed = test_accume_speed / test_run_total
            print(f"{accume_avg_speed}")
            reactor.stop()
        else:
            for file_name in test_download_files_list:
                ConstructDownload(file_name)

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
        displayMsg(f"Download {self.file_name} complete!!!")

        reactor.callFromThread(self.download_client.setChecksum, self.md5sum.digest())

class FileDownloadClient(basic.LineReceiver):
    def __init__(self, file_name):
        self.file_name = file_name
        self.file_size = 0
        self.file_data_received = 0

        self.checked_md5sum = None
        self.received_md5sum = None

        self.start_time = 0

        self.end_time = 0

    def compareChecksums(self):
        global current_downloading
        global is_test_download

        # self.end_time = time.time()
        
        if self.checked_md5sum == self.received_md5sum:
            displayMsg(f"Verified {self.file_name} md5 successful!!")
            current_downloading -= 1
            self.transport.loseConnection()
        else:
            displayMsg(f"Verified {self.file_name} md5 failed!!")
            self.transport.loseConnection()

        used_time = self.end_time - self.start_time
        if used_time == 0:
            used_time = 0.001
        displayMsg(f"Download {self.file_name} take {used_time}s")
        speed = (self.file_size / used_time) / (1024 * 1024)
        displayMsg(f"Downlaod speed  {speed}MB/s")

        if is_test_download:
            accumeAndCheckDownloadComplete(speed)

    def setChecksum(self, in_md5sum):
        self.checked_md5sum = in_md5sum
        if self.received_md5sum is not None:
            self.compareChecksums()

    def lineReceived(self, line):
        str_line = line.decode()
        if str_line.startswith("error: "):
            displayMsg(str_line)
            self.transport.loseConnection()
        elif str_line.startswith("md5: "):
            hex_str = str_line[len("md5: "):]
            self.received_md5sum = bytes.fromhex(hex_str)
            
            if self.checked_md5sum is not None:
                self.compareChecksums()
        else:
            self.start_time = time.time()

            self.file_size = int(str_line)
            file_path = Path.joinpath(getDownloadCombinePath(), Path(self.file_name))
            if self.file_size != 0:
                self.download_thread = DownloadThread(file_path, self.file_name, self.file_size, self)
                self.setRawMode()

                self.download_thread.start()
            else:
                with open(file_path, "wb") as fp:
                    displayMsg("Download {self.file_name} complete!!!")

    def rawDataReceived(self, data):
        self.file_data_received += len(data)

        if self.file_data_received >= self.file_size:
            self.end_time = time.time()

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

        displayMsg("Issue file download: %s" % self.file_name)

        current_downloading += 1
        self.sendLine(b"download: %s" % self.file_name.encode())

class FileDownloadFactory(ClientFactory):
    def __init__(self, file_name):
        self.file_name = file_name

    def startedConnecting(self, connector):
        displayMsg('Download Started to connect.')

    def buildProtocol(self, addr):
        displayMsg('Download Connected.')
        return FileDownloadClient(self.file_name)

    def clientConnectionLost(self, connector, reason):
        displayMsg('Download Lost connection.  Reason:' + str(reason))

    def clientConnectionFailed(self, connector, reason):
        displayMsg('Download Connection failed. Reason:' + str(reason))

def SendCommandStr(str_line):
    command_client.sendLineStr(str_line)

def ConstructDownload(file_name):
    global host
    global port
    reactor.connectTCP(host, port, FileDownloadFactory(file_name))

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
        global is_test_download
        global test_download_files_list

        if is_test_download:
            for file_name in test_download_files_list:
                ConstructDownload(file_name)
        else:
            self.input_thread = Thread(target = InputFunc)
            self.input_thread.start()

    def lineReceived(self, line):
        str_line = line.decode()
        displayMsg(str_line)

    def sendLineStr(self, line_str):
        self.sendLine(line_str.encode())

class CommandClientFactory(ClientFactory):
    def startedConnecting(self, connector):
        displayMsg('Started to connect.')

    def buildProtocol(self, addr):
        displayMsg('Connected.')
        global command_client
        command_client = CommandClient()
        return command_client

    def clientConnectionLost(self, connector, reason):
        displayMsg('Lost connection.  Reason:'+ str(reason))

    def clientConnectionFailed(self, connector, reason):
        displayMsg('Connection failed. Reason:' + str(reason))

if __name__ == "__main__":
    host = "localhost"
    port = 1025

    parser = argparse.ArgumentParser("Donwload Client.")
    parser.add_argument('-p', '--port', default=port)
    parser.add_argument('-s', '--host', default=host)
    parser.add_argument('--download', default='')
    parser.add_argument('--testdownload', action='store_true', default=False)
    parser.add_argument('--subfolder', default=download_subpath)

    args = parser.parse_args()
    host = args.host
    port = args.port
    download_subpath = args.subfolder
    is_test_download = args.testdownload

    reactor.connectTCP(host, port, CommandClientFactory())
    reactor.run()
