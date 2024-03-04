import socket
import threading
import argparse
import sys
import re
import time

def server(ip, port, format):   #Starts whyperf in server mode.
    #Arguments:
    # ip and port are the IP and port the user wants to use for the server.
    # format: the units the users wants the data to be displayed in
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Creates a TCP socket using the socket module
    # This code runs through ports until it finds an open one
    noport = True               #Used for while loop. Set to false when the server successfully binds to a port
    firstPort = port            #Used to quit the program when server can't bind to a provided IP and every port from 1024-65534.
    while noport:               #Loops through all ports for the given IP and binds to the first available one.
        try:                    #Used to handle exceptions when server can't bind to a port without quitting the program.
            server_socket.bind((ip, port))  #Attempts to bind with provided IP and current port
            noport = False
        except OSError:                     #Excepts error when server cant bind to provided IP and port
            port = port + 1                 #Iterates port for the next bind attempt
        if (port == 65535):
            port = 1024                     #Used to run through remaining ports in the valid range.
        elif (port == firstPort - 1):       #If the current port is the one prior to the first port, an error message is shown. It's worth noting that the last port is never actually tested.
            raise Exception("Could not bind to any port on IP " + str(ip))

    server_socket.listen(5)                 #The server is ready to accept up to 5 simultaneous connections.

    #Prints message when server is ready to handle clients
    print("---------------------------------------------------------")
    print("A whyperf server is listening on " + str(ip) + ":" + str(port))
    print("---------------------------------------------------------")

    def handle_client(client_socket, client_address, thread):   #Starts a thread for every connection
        #Parameters:
        #client_socket:     used to interface with the socket, including sending and receiving data
        #client_address:    used to print client IP and port.
        #thread:            thread counter used to differentiate between the different client connections when printing summary
        print("A whyperf client with IP " + str(client_address[0]) + ":" + str(client_address[1]) + " is connected with server " + str(ip) + ":" + str(port))
        clientStartTime = float(client_socket.recv(1024).decode().rstrip("\x00"))      #Receives client start time from client. The message is stripped from empty bytes.
        duration = 0            #Used to calculate the duration of the test after the test is finished
        received_bytes = 0
        done = False            #Used to exit the while loop when the test is finished

        while not done:         #While loop used to receive data and end the test
            data = client_socket.recv(1024) #Receives data from client
            if (data.decode() == "BYE"):    #If the data is a "BYE" message, the test has ended and the loop can be exited
                clientEndTime = client_socket.recv(1024).decode()           #Recieves end time from client
                duration = float(clientEndTime) - float(clientStartTime)    #Calculates total duration of the test
                client_socket.send("ACK:BYE".encode())                          #Sends "ACK" to client
                client_socket.close()                                       #Closes connection
                done = True
                continue                    #Skips the rest of the while loop so that the bye message isn't added to received_bytes
            received_bytes += len(data) #Adds message length to received bytes.

        #prints statistics after test ends
        if (thread == 0):       #Only the first thread needs to print table decorations
            print("---------------------------------------------------------")
            print(f"ID{' ':<20}Interval{' ':<10}Received{' ':<12}Rate")         #The text is formatted to provide a lot of white space between columns
        printSummary(ip, port, duration, received_bytes, format, thread, 3)     #printSummary method calculates and prints statistics. It always prints with 3 decimals as the server does not know whether the test is num- or time-bound.

        # Global variable threadNr is used to keep track of total number of threads. This is used to avoid printing redundant data, like table headers
        global threadNr
        threadNr -= 1
        client_socket.close()   #Closes client socket

    global threadNr     #Used to keep track of total number of threads
    while True:         #This code can run indefinitely since the server can handle multiple sets of tests without needing to close/restart
        client_socket, client_address = server_socket.accept()  #Accepts client connection

        # Starts handle_client method on a new thread
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, threadNr))
        client_thread.start()

        threadNr += 1       #Increments thread counter
        time.sleep(0.1)     #Waits 0.1s before running the loop again. This gives every connection a bit of headroom to connect. This is only used to make sure that statistics are printed in the correct order when using parallel connections.

def client(ip, port, format, duration, numberOfBytes, interval, connections):       #Starts whyperf in client mode
    #Arguments:
    #ip, port:      IP and port the client should connect to.
    #format:        Unit data should be printed in
    #duration:      Duration of test in seconds
    #numberOfBytes: Duration of test in number of bytes
    #interval:      Seconds between printing statistics
    #Connections:   How many parallel connections the test should run

    #The following code determines if test is bound by time or number of bytes. If neither, client starts with default parameters
    testDuration = 0        #Shared variable used for either seconds or number of bytes.
    durationType = ""       #Duration type determines whether test is bound by time or number of bytes. It also is used to determine whether the testDuration variable holds seconds or number of bytes
    if (numberOfBytes == "NA" and duration == "NA"):        #If neither -n nor -t are specified, set to default values
        testDuration = 25
        durationType = "time"
    elif (not numberOfBytes == "NA" and duration == "NA"):  #If only number of bytes is specified,
        testDuration = numberOfBytes                        #set test duration to number of bytes and
        durationType = "bytes"                              #duration type to "bytes".
    elif (numberOfBytes == "NA" and not duration == "NA"):  #If only duration is specified,
        testDuration = duration                             #set test duration to bytes and
        durationType = "time"                               #duration type to "time".
    else:
        #If both -t and -n are used, raise exception
        raise Exception("Could not parse argument -time or -num. Make sure you are using either -n or -t, but not both.")

    #Prints message when client is preparing to connect
    print("---------------------------------------------------------")
    print("A whyperf client is connecting to " + str(ip) + ":" + str(port))

    threads = []  # Array of threads
    for i in range(int(connections)):       #This code runs as many times as there are connections requested by the user (using -P flag)
        # Starts handle_client method on a new thread
        thread = threading.Thread(target=client_connection, args=(ip, port, testDuration, durationType, interval, i, format))
        threads.append(thread)  #Adds current thread to threads-variable
        thread.start()          #Starts thread
        time.sleep(0.01)        #Sleeps 0.01s, again to prevent statistics from being printed in the wrong order

def client_connection(ip, port, testDuration, durationType, interval, connectionNo, format):    #Starts the test for every connection requested by user (with -P flag)
    #I intended for this to be nested under client(), but decided against it as I had issues implementing the method correctly.
    #Inherits many of the arguments provided to client(), except:
    #testDuration and durationType:     Used to run the test for as long as the user requests. testDuration can hold either seconds or bytes, depending on the value of durationType
    #connectionNo:                      The ID of this thread. Used to differentiate between parallel connections when printing statistics.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #Creates a TCP socket for the client

    # Tries to connect to socket with provided IP and port, catching exceptions
    try:
        client_socket.connect((ip, port))
    except Exception:
        raise Exception("Could not bind to ip: " + str(ip) + " on port: " + str(port))  #prints error on exception

    #Prints message when client connects to server
    print("Client " + str(connectionNo) + " connected with " + str(ip) + " on port " + str(port))

    time.sleep(0.2) #Waits for other threads to connect and print their "connected" message before printing the table columns
    if(connectionNo == 0): #Only the first client prints the table columns
        print("---------------------------------------------------------")
        print(f"ID{' ':<20}Interval{' ':<8}Transfer{' ':<13}Bandwidth")
    bytesSent = 0                   #Tracks number of bytes sent
    currentInterval = 0             #Used to print start time of the current interval
    bytesSentThisInterval = 0       #Tracks number of bytes sent this interval
    data = bytes(1024)              #Creates data with size of 1024 bytes
    #All variables that are not time-critical are defined before this comment. This is done to
    #reduce the impact setup has on the actual test duration.
    start_time = time.time()
    intervalStartTime = start_time      #Used to print interval as often as specified by the user
    client_socket.send(str(time.time()).encode())  # send start time to server
    if (durationType == "time"):
        while (start_time + testDuration >= time.time()):   #Run test while starttime + duration > current time
            client_socket.send(data)                        #Sends a lot of data in the while loop
            bytesSent += 1024                               #Adds datalength to bytesSent
            bytesSentThisInterval += 1024
            # If intervalStartTime in seconds + interval seconds <= current time, the code prints statistics and resets the interval
            if (intervalStartTime + interval <= time.time()):
                printInterval(ip, port, currentInterval, interval, bytesSentThisInterval, format, connectionNo)
                currentInterval += interval         #iterates start time of current interval by interval specified by the user
                #resets interval data as the new interval has just started
                bytesSentThisInterval = 0
                intervalStartTime = time.time()

                print(f"\r {(float(start_time + testDuration) - float(time.time())):.0f} seconds remaining", end="\r") #Progress indicator
    elif (durationType == "bytes"):
        while (bytesSent < testDuration):                   #Run test while bytes sent < test duration (number of bytes to send)
            client_socket.send(data)                        #Sends a lot of data in the while loop
            bytesSent += 1024                               #Adds datalength to bytesSent
            bytesSentThisInterval += 1024
            # If intervalStartTime in seconds + interval seconds <= current time, the code prints statistics and resets the interval
            if (intervalStartTime + interval <= time.time()):
                printInterval(ip, port, currentInterval, interval, bytesSentThisInterval, format, connectionNo)
                currentInterval += interval         #iterates start time of current interval by interval specified by the user
                #resets interval data as the new interval has just started
                bytesSentThisInterval = 0
                intervalStartTime = time.time()

                print(f"\r {(bytesSent / testDuration) * 100:.2f}% Complete", end="\r") #Progress indicator
    endTime = str(time.time())      #Sets endtime right after test ends

    #In some rare circumstances, the last interval of a test won't be printed. (e.g. when -i and -t are the same value)
    #This code remedies that. It also prints the remaining interval of a bytes-bound test (-n flag) with the correct duration.
    if (bytesSentThisInterval != 0):
        if (durationType == "bytes"):
            interval = float(endTime) - start_time           #Calculates the end time of the last interval in a bytes-bound test
        printInterval(ip, port, currentInterval, interval, bytesSentThisInterval, format, connectionNo) #Prints last interval

    time.sleep(1) #sleep(1) gives the remaining threads an opportunity to print their final interval before printing the table columns
    if(connectionNo == 0): #Only the first client needs to print the table columns
        print("---------------------------------------------------------")
        print(f"ID{' ':<20}Interval{' ':<8}Transfer{' ':<13}Bandwidth")
    if (durationType == "bytes"):
        printSummary(ip, port, interval, bytesSent, format, connectionNo, 3) #Print summary with 3 decimal places on the interval
    else:
        printSummary(ip, port, testDuration, bytesSent, format, connectionNo, 0) #No need for decimals as the test duration can't be a value that isn't round

    #Sends BYE, waits for ACK and closes the connection.
    #Execution is paused multiple times as this was found to reduce issues when quitting the client. It also helps with printing in the correct order
    time.sleep(2)
    client_socket.send("BYE".encode())
    time.sleep(1)
    client_socket.send(endTime.encode())
    msg = client_socket.recv(1024).decode()
    if (msg == "ACK:BYE"
               ""):
        client_socket.close()

#This code is optimised for efficiency as its being called every interval
def printInterval(ip, port, currentInterval, interval, bytesSentThisInterval, format, connectionNo):
    #Prints the current interval of the test
    #Arguments:
    #ip, port:          IP and port client is connected to
    #currentInterval:   The start time of current interval (seconds from test start, not actual time)
    #interval:          User-specified interval length
    #bytesSentThisInterval: Number of bytes sent this interval
    #format:            User-specified unit data should be formatted as
    #connectionNo:      The ID of the thread that prints this interval
    decimal = 0         #How many decimals should be printed in bytes column
    bit = "b"           #Used for formatting Xbps column (bps, Kbps, Mbps)
    if (format == "KB"):
        bytesSentThisInterval /= 1024       #Converts bytes to KB
        decimal = 2                         #Use 2 decimals
        bit = "Kb"                          #Format bps as Kbps
    elif (format == "MB"):
        bytesSentThisInterval /=  1_024_000 #Converts bytes to MB
        decimal = 2                         #Use 2 decimals
        bit = "Mb"                          #Format bps as Mbps

    #Columns are created in advance to simplify formatting
    col1 = f"{ip}:{port}:{connectionNo}"
    col2 = f"{currentInterval} - {float(currentInterval) + float(interval):.2f}"
    col3 = f"{bytesSentThisInterval:.{decimal}f} {format}"
    col4 = f"{(bytesSentThisInterval*8) / interval:.{decimal}f} {bit}ps"
    #Column length can vary. This code calculates the number of empty bytes to print to make columns more aligned
    col1len = 22
    col2len = 32 - len(col1)
    col3len = 29 - len(col2)
    print(f"\r{col1:<{col1len}}{col2:<{col2len}}{col3:<{col3len}}{col4}")    #Prints interval

def printSummary(ip, port, duration, bytesSent, format, connectionNo, intervalDecimals):
    #Arguments:
    #ip, port:          IP and port the method calling this method is connected to
    #duration:          Total duration of test
    #bytesSent:         Number of bytes sent in total
    #format:            User-specified unit data should be formatted as
    #connectionNo:      The ID of the thread that prints this summary
    #intervalDecimals:  Prints duration with 0 or 3 decimals. 3 decimals are used when client runs test with -num, as the duration is rarely round.
    decimal = 0         #How many decimals should be printed in bytes column
    bit = "b"           #Used for formatting Xbps column (bps, Kbps, Mbps)
    if (format == "KB"):
        bytesSent /= 1024                   #Converts bytes to KB
        decimal = 2                         #Use 2 decimals
        bit = "Kb"                          #Format bps as Kbps
    elif (format == "MB"):
        bytesSent /= 1_024_000              #Converts bytes to MB
        decimal = 2                         #Use 2 decimals
        bit = "Mb"                          #Format bps as Mbps

    #Columns are created in advance to simplify formatting
    col1 = f"{ip}:{port}:{connectionNo}"
    col2 = f"0 - {duration:.{int(intervalDecimals)}f}"
    col3 = f"{bytesSent:.{decimal}f} {format}"
    col4 = f"{(bytesSent*8) / duration:.{decimal}f} {bit}ps"
    #Column length can vary. This code calculates the number of empty bytes to print to make columns more aligned
    col1len = 22
    col2len = 32 - len(col1)
    col3len = 29 - len(col2)

    print(f"{col1:<{col1len}}{col2:<{col2len}}{col3:<{col3len}}{col4}") #Prints interval

def checkPort(val): #Checks input of -p port flag
    try:
        value = int(val)            #Port must be an integer
    except ValueError:
        raise argparse.ArgumentTypeError("Expected an integer but you entered a string")
    if (value < 1024 or value > 65535):     #Port must be in valid range
        raise argparse.ArgumentTypeError(str(value) + " is not a valid port")
    return value
def checkIP(val): #Checks input of -I serverip flag
    if (val == "localhost"): #Used to skip regex, as "localhost" does not match the pattern of an IPv4 address
        return "localhost"
    ipcheck = re.match(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", str(val))     #regex for IPv4 address
    ipOK = bool(ipcheck)
    if (ipOK):
        splitIP = val.split(".")        #Splits IP at decimal point
        for byte in splitIP:            #For every octet, check if it's in the valid range og 0-255
            if (int(byte) < 0 or int(byte) > 255):
                raise argparse.ArgumentTypeError(str(val) + "is not a valid IPv4 address")
    return val      #Return user specified IP if all checks pass
def checkFormat(val): #Checks input of -f format flag
    val = val.upper()       #Converted to uppercase to simplify if-statements
    if val == "B":
         return "B"
    elif val == "KB":
        return "KB"
    elif val == "MB":
        return "MB"
    else:
        raise Exception("Could not parse format. Supported output formats are B, KB or MB. Actual: " + str(val))
def checkTime(val): #Checks input of -t time flag
    if (val == "NA"): #NA is used in place of None. If val is NA, the user has not specified a value
        return "NA"
    try:
        seconds = int(val)      #Time must be an integer
    except ValueError:
        raise argparse.ArgumentTypeError("Duration is not valid. Expected time in seconds. Actual: " + str(val))
    if (seconds <= 0):          #Time must be positive
        raise argparse.ArgumentTypeError("Duration can't be 0 or negative")
    return seconds              #Return user-specified value if all checks pass
def checkNum(val): #Checks input of -n num flag
    if (val == "NA"): #NA is used in place of None. If val is NA, the user has not specified a value
        return "NA"
    val = val.casefold()            #converts all text to lowercase to simplify regex and if-statements
    numCheck = re.match(r"([0-9]{1,25})((?:b|kb|mb){1,2})", str(val))       #regex for the expected input (<numberofbytes><format>)
    numOK = bool(numCheck)
    if (numOK):
        items = numCheck.groups()               #Creates an array with the number and string provided by user
        if (items[1] == "kb"):
            return int(items[0]) * 1024         #Returns the number converted to KB
        elif (items[1] == "mb"):
            return int(items[0]) * 1_024_000    #Returns the number converted to MB
        elif (items[1] == "b"):
            return items[0]                     #Returns the number with no conversion as its already in bytes
    raise Exception("Could not interpret your input " + str(val) + ". Enter number of bytes ending with either B, KB or MB")        #If no return statement is run, the user must have provided an invalid value

def checkInterval(val): #Checks input of -i interval flag
    val = int(val)                      #Interval must be an integer
    if(val < 1 or val > 120):           #interval must be in valid range
        raise argparse.ArgumentTypeError("Interval " + str(val) + " is not valid. Valid range is 1-120")
    return val                          #Returns user-specified value if all checks pass

def checkParallel(val): #Checks input of -P parallel flag
    val = int(val)                      #Value must be an integer
    if (val < 1 or val > 5):            #Value must be in valid range, up to 5 parallel connections are allowed
        raise argparse.ArgumentTypeError("Can't run " + str(val) + " parallel connections. Valid range is 1-5")
    return val                          #Returns user-specified value if all checks pass

threadNr = 0  #Used by server to keep track of number of threads.
sys.tracebacklimit = 0  # Used to throw exceptions without traceback.

parser = argparse.ArgumentParser(description="positional arguments", epilog="end of help")      #Initialises argsparse parser

# Arguments
parser.add_argument('-s', '--server', action='store_true', default=False, help="Start in server mode. Default")
parser.add_argument('-c', '--client', action='store_true', default=False, help="Start in client mode")
parser.add_argument('-b', '--bind', type=checkIP, default="127.0.0.1",
                    help="Bind to provided IPv4 address. Default 127.0.0.1")
parser.add_argument('-p', '--port', type=checkPort, default="8088", help="Bind to provided port. Default 8088")
parser.add_argument('-f', '--format', type=checkFormat, default="MB",
                    help="Specify output format. Supported: B, KB, MB. Default MB")
parser.add_argument('-I', '--serverip', type=checkIP, default="127.0.0.1")
parser.add_argument('-t', '--time', type=checkTime, default="NA", help="Duration of test in seconds")
parser.add_argument('-n', '--num', type=checkNum, default="NA",
                    help="Number of bytes to transfer. Must end with B, KB or MB")
parser.add_argument('-i', '--interval', type=checkInterval, default="5",
                    help="Update frequency for statistics in seconds")
parser.add_argument('-P', '--parallel', type=checkParallel, default="1", help="Create parallel connections to server")
args = parser.parse_args()        #Parses arguments provided by user

if (args.server and args.client):
    #An instance of whyperf can't run both server and client at the same time
    raise Exception("Can't run server and client in the same instance")
elif (args.server and not args.client):
    #If only -s is provided, run in server mode
    server(args.bind, args.port, args.format)
elif (not args.server and args.client):
    #If only -c is provided, run in client mode
    client(args.serverip, args.port, args.format, args.time, args.num, args.interval, args.parallel)
else:
    #If neither -s nor -c is provided, or parsing failed, raise an exception.
    raise Exception("Error: you must run either in server or client mode")
