# Once connection is setup client can download any number of files.

import socket
import os
port = 60004
host = ""

#Here we made a socket instance and passed it two parameters. 
#The first parameter is AF_INET and the second one is SOCK_STREAM.
#AF_INET refers to the address family ipv4
#Secondly the SOCK_STREAM means connection oriented TCP protocol
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

    
except socket.error as err:
    print "socket creation failed with error %s" %(err)
    proxy_socket.close()
    raise SystemExit


while True:
    try:
        client_conn, client_addr = proxy_socket.accept()    
        print 'Got connection from', client_addr
        client_data = client_conn.recv(1024)
        print(client_data)
        
        lines = client_data.split('\n')
        print("client_data",client_data)
        
        tokens = lines[0].split()
        url = lines[0].split()[1]
        print(url)
        http_pos = url.find("://")
        if http_pos != -1:
            url = url[(http_pos+3):]
        
        path_pos = url.find("/")
        if path_pos == -1:
            path_pos = len(url)
        
        path_url = url[path_pos:] # Getting the url of  the object
        print(path_url)
        tokens[1] = path_url
        lines[0] = ' '.join(tokens)
        client_data = "\n".join(lines) + '\r\n\r\n' # Generating request to be sent to server
        
        port = -1
        webserver = ""
        port_pos = url.find(":") # Get port number and server address
        if port_pos == -1:
            port = 80
            webserver = url[:path_pos]
        else:
            port = int(url[(port_pos+1):path_pos])
            webserver = url[:port_pos]

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((webserver, port))
        server_socket.sendall(client_data)
       

    except KeyboardInterrupt:
        client_conn.close()
        print('Connection closed by client')
        proxy_socket.close()
        print "\nProxy server shutting down ..."
        break