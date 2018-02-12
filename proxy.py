# Once connection is setup client can download any number of files.

import socket
import time
import os
import operator
import thread
import threading

port = 60004
host = ""
MAX_CACHE_SIZE = 3
CACHE_DIR = "./cache"
if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)

cached_dic = {} # Dictionary with file names as keys and their last access time as values
locks = {}
proxy_socket = ''

''' Used to make proxy socket '''
def make_proxy_socket():
    '''
    Here we made a socket instance and passed it two parameters. 
    The first parameter is AF_INET and the second one is SOCK_STREAM.
    AF_INET refers to the address family ipv4
    Secondly the SOCK_STREAM means connection oriented TCP protocol
    '''
    try:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "Socket successfully created"

        # Re-use the socket
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Next bind to the port, we have not typed any ip in the ip field 
        # instead we have inputted an empty string this makes the server listen to requests 
        # coming from other computers on the network
        proxy_socket.bind((host, port))
        print "socket binded to %s" %(port)

        # put the socket into listening mode
        #5 connections are kept waiting if the server is busy and 
        #if a 6th socket trys to connect then the connection is refused.
        proxy_socket.listen(5)
        print "socket is listening"

        print "Serving proxy on %s port %s ..." % (
                str(proxy_socket.getsockname()[0]),
                str(proxy_socket.getsockname()[1])
        )

        return proxy_socket

        
    except socket.error as err:
        print "socket creation failed with error %s" %(err)
        proxy_socket.close()
        raise SystemExit

''' Used to free space if cached memory is full '''
def get_space_for_cache(filename):

    ''' If we can add file in the cache '''
    if len(cached_dic) - 1 < MAX_CACHE_SIZE:
        return
    # Clear cache
    else: 
        ''' Sort the cached dictionary wrt to their value '''
        sorted_x = sorted(cached_dic.items(), key=operator.itemgetter(1)); 

        ''' Filename to be deleted will first element of dictionary '''
        file_to_deleted = sorted_x[0][0]

        ''' Deleting file from cache and cache_list '''
        acquire_lock(file_to_deleted)
        del cached_dic[file_to_deleted]
        os.remove(CACHE_DIR + "/" + file_to_deleted)
        release_lock(file_to_deleted)

''' Used to add filename in cached dictionary '''
def add_log(filename,is_cached):

    ''' If file is not in cached dictionary '''
    if not filename in cached_dic:
        ''' Clears space for cache '''
        get_space_for_cache(filename)

        ''' Adds filename and its access time in cached dic '''
        acquire_lock(filename)
        cached_dic[filename] = time.strptime(time.ctime(), "%a %b %d %H:%M:%S %Y")
        release_lock(filename)        
        ''' File is not cached before '''
        is_cached = 0
        
    # If file is in cached dictionary
    else:
        ''' Update the access time of file if it is in cached dic '''
        acquire_lock(filename)
        cached_dic[filename] = time.strptime(time.ctime(), "%a %b %d %H:%M:%S %Y")
        release_lock(filename)
        ''' File is cached before '''
        is_cached = 1
    
    return is_cached

''' Used to modify header if file is cached '''
def modify_header(cache_path,lines):
    if os.path.isfile(cache_path):
        last_mtime = time.strptime(time.ctime(os.path.getmtime(cache_path)), "%a %b %d %H:%M:%S %Y")
        header = time.strftime("%a %b %d %H:%M:%S %Y", last_mtime)
        header = "If-Modified-Since: " + header + '\r'
        while lines[len(lines)-1] == '':
            lines.remove('')
        lines.remove('\r')
        lines.append(header)
        lines.append('\r')
        lines.append('')

''' Returns the server address and port number '''
def parse_port_serverurl(url,path_pos):
    port = -1
    webserver = ""
    port_pos = url.find(":") # Get port number and server address
    if port_pos == -1:
        port = 80
        webserver = url[:path_pos]
    else:
        port = int(url[(port_pos+1):path_pos])
        webserver = url[:port_pos]
    return port,webserver

def acquire_lock(filename):
    if filename in locks:
        lock = locks[filename]
    else:
        lock = threading.Lock()
        locks[filename] = lock
    lock.acquire()

def release_lock(filename):
    if filename in locks:
        lock = locks[filename]
        lock.release()
    else:
        print "Lock problem occured"
        sys.exit()
        
def handle_one_client(client_conn,client_data):
    lines = client_data.split('\n')
    print("client_data",client_data)
    
    tokens = lines[0].split()
    url = lines[0].split()[1]
    #print(url)
    http_pos = url.find("://")
    if http_pos != -1:
        url = url[(http_pos+3):]
    
    path_pos = url.find("/")
    if path_pos == -1:
        path_pos = len(url)
    
    path_url = url[path_pos:] # Getting the url of  the object
    filename = path_url[1:]
    print(path_url)
    tokens[1] = path_url
    lines[0] = ' '.join(tokens)
    is_cached = 0;
    is_cached = add_log(filename,is_cached)
    print('is_cached' ,is_cached)

    cache_path = CACHE_DIR + '/' + filename

    ''' If file is cached then we modify headers to check if file is modified or not '''
    if is_cached:
        modify_header(cache_path, lines)

    ''' Generating request to be sent to server '''
    client_data = "\r\n".join(lines) + '\r\n\r\n'
    port,webserver = parse_port_serverurl(url,path_pos)

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((webserver, port))
        server_socket.sendall(client_data)
        reply = server_socket.recv(4096)
        print('reply ' ,reply)
        
        
        if "304 Not Modified" in reply:
            print("Not Modified")
        else:
            print("Modified")
        
        ''' If file is cached and not modified on the server
            We read the file from cache '''
        if is_cached and "304 Not Modified" in reply:
            acquire_lock(filename)
            f = open(cache_path, "rb")
            chunk = f.read(1024)    
            while len(chunk):
                client_conn.send(chunk)
                ''' Read from cache '''
                chunk = f.read(1024)
            f.close()
            release_lock(filename)
            client_conn.send("\r\n\r\n")

        else:
            acquire_lock(filename)
            f = open(cache_path, "w+")
            while len(reply):
                client_conn.send(reply)
                ''' Write to cache '''
                f.write(reply)
                reply = server_socket.recv(1024)
            f.close()
            release_lock(filename)
            client_conn.send("\r\n\r\n")
        server_socket.close()
        client_conn.close()
        return

    except Exception as e:
        server_socket.close()
        client_conn.close()
        print e
        return


def start_server():
    proxy_socket = make_proxy_socket()
    while True:
        try:
            client_conn, client_addr = proxy_socket.accept()    
            print 'Got connection from', client_addr
            client_data = client_conn.recv(1024)
            print(client_data)
            
            thread.start_new_thread(handle_one_client,(client_conn, client_data))

        except KeyboardInterrupt:
            client_conn.close()
            print('Connection closed by client')
            proxy_socket.close()
            print "\nProxy server shutting down ..."
            break

start_server()
