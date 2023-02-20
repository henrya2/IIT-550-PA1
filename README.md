These programs need Python 3.8 with Twisted network library to run.

You need to prepare Python3.8 first in the Linux system.

Then, run make_venv.sh to setup a Python Virtual Environment.

There is no makefile need for python scrips. Just run it with python3. Deployment is not needed either. Just run python with correct arguments.

Use start_server.sh to start the server. --port to specify the port, and --files_path to specify host files folder.

python3 Code/client/client.py to start a client. --port to specifiy the server port, and --host to choose server's ip. 'get_files_list' in the input console will get files list from server. 'download: file_name' will download 'file_name' from server.

