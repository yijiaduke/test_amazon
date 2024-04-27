import socket
import threading
import world_amazon_pb2
import amazon_ups_pb2

from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.encoder import _VarintEncoder
from google.protobuf.internal.decoder import _DecodeVarint


# HOST = "vcm-38978.vm.duke.edu"
# PORT = 23456
# # MAX_BUFFER = 65535

# AMAZON_HOST = "vcm-38978.vm.duke.edu"
# AMAZON_PORT = 22222
socket_lock = threading.Lock()

wharehouse_num= 2

world_fd = None
ups_fd = None
current_seqnum = 0
send_ups_seqnum = []
send_world_seqnum = []

def get_seqnum():
    global current_seqnum
    with socket_lock:
        current_seqnum += 1
        return current_seqnum
    

def encode_varint(value):
    """ Encode an int as a protobuf varint """
    data = []
    _VarintEncoder()(data.append, value, False)
    return b''.join(data)


def decode_varint(data):
    """ Decode a protobuf varint to an int """
    return _DecodeVarint(data, 0)[0]

def create_client_socket(host, port):
    """Creates and returns a socket connected to the given host and port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    return s

def create_server_socket(host, port):
    # Create a socket object
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Enable port reuse
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to the host and port
        s.bind((host, port))
        # Listen for incoming connections
        s.listen()

        # print(f"Server listening on {host}:{port}")
        print(f"Server listening on {host}:{port}")
        global ups_fd
        # Accept incoming connection
        ups_fd, addr = s.accept()

        # print(f"Connected to {addr}")

        # You can now use the 'conn' object to send and receive data with the client
        print(f"socket with ups:{ups_fd}")
        return ups_fd


def create_Aconnect_msg(worldid, is_amazon, wharehouse_num):
    Aconnect = world_amazon_pb2.AConnect()
    if worldid is not None:
        Aconnect.worldid = worldid
    Aconnect.isAmazon = is_amazon
    for whid in range(1, wharehouse_num+1):
        AInitWarehouse = Aconnect.initwh.add()
        AInitWarehouse.id = whid
        AInitWarehouse.x = whid +1
        AInitWarehouse.y = whid + 2
    # AInitWarehouse = Aconnect.initwh.add()
    # AInitWarehouse.id = 1
    # AInitWarehouse.x = 1
    # AInitWarehouse.y = 1
    # AInitWarehouse = Aconnect.initwh.add()
    # AInitWarehouse.id = 2
    # AInitWarehouse.x = 1
    # AInitWarehouse.y = 1
    print (Aconnect)
    return Aconnect

def recv_world_msg(world_fd, msg_type):
    """ Receive a message, prefixed with its size, from a TCP/IP socket """
    # Receive the size of the message data
    data = b''
    while True:
        try:
            data += world_fd.recv(1)
            size = decode_varint(data)
            break
        except IndexError:
            pass
    # Receive the message data
    data = world_fd.recv(size)
    # Decode the message
    if msg_type== "AConnected":
        AConnected_msg = world_amazon_pb2.AConnected()
        AConnected_msg.ParseFromString(data)
        print("AConnected_msg: \n", AConnected_msg, "\n")
        return AConnected_msg
    elif msg_type== "AResponses":
        AResponses_msg = world_amazon_pb2.AResponses()
        AResponses_msg.ParseFromString(data)
        print("AResponses_msg: ", AResponses_msg, "\n")
        return AResponses_msg

def createConnectWorldId_msg(world_id):
    msg = amazon_ups_pb2.ConnectWorldId()
    msg.world_id = world_id
    msg.seq_num = current_seqnum
    print("ConnectWorldId_msg: \n", msg, "\n")
    return msg

def createRequestTruck_msg(warehouse_id,x,y,destx,desty,ship_id):
    AtoUCommands_msg = amazon_ups_pb2.AtoUCommands()
    msg = AtoUCommands_msg.truckReqs.add()
    current_seqnum= get_seqnum()
    msg.seq_num = current_seqnum
    msg.warehouse_id  = warehouse_id
    msg.warehouse_x= x
    msg.warehouse_y= y
    msg.dest_x = destx
    msg.dest_y = desty
    msg.ship_id = ship_id
    print("RequestTruck_msg\n", AtoUCommands_msg, "\n")
    return  AtoUCommands_msg

def createDeliverPackage(ship_id):
    AtoUCommands_msg = amazon_ups_pb2.AtoUCommands()
    msg = AtoUCommands_msg.delivReqs.add()
    current_seqnum= get_seqnum()
    msg.seq_num = current_seqnum
    msg.ship_id = ship_id
    print("DeliverPackage_msg\n", AtoUCommands_msg, "\n")
    return AtoUCommands_msg


def build_connect_world():
    global world_fd 
    world_fd = create_client_socket(HOST, PORT) 
    print(f"socket with world:{world_fd}")
    try:
        Aconnect_msg = create_Aconnect_msg(None, True, wharehouse_num)
        serialized_msg = Aconnect_msg.SerializeToString() 
        len_prefix = _VarintBytes(len(serialized_msg))
        world_fd.sendall(len_prefix + serialized_msg)
        Aconnected_msg = recv_world_msg(world_fd, "AConnected")
        worldid= Aconnected_msg.worldid
        print(f"Aconnected_msg: \n{Aconnected_msg}\n")
        return world_fd, worldid
    # finally:
    #     client_socket.close()  # Ensure the socket is closed
    except:
        print("Error: build_connect_world() failed")


def sendToUPS(ups_fd,msg):
    serialized_msg = msg.SerializeToString()
    len_prefix = _VarintBytes(len(serialized_msg))
    with socket_lock:
        ups_fd.sendall(len_prefix+ serialized_msg)
    return
def sendToWorld(world_fd, msg):
    serialized_msg = msg.SerializeToString()
    len_prefix = _VarintBytes(len(serialized_msg))
    with socket_lock:
        world_fd.sendall(len_prefix+ serialized_msg)
    return

def recv_Ups_msg(ups_fd, msg_type):
    # Receive the size of the message data
    data = b''
    while True:
        try:
            data += ups_fd.recv(1)
            size = decode_varint(data)
            break
        except IndexError:
            pass
    # Receive the message data
    data = ups_fd.recv(size)
    # Decode the message
    if msg_type== "UtoACommands":
        UtoACommands_msg = amazon_ups_pb2.UtoACommands()
        UtoACommands_msg.ParseFromString(data)
        print("UtoACommands_msg:\n ", UtoACommands_msg, "\n")

def listen_to_ups(ups_fd):
    while True:
        try:
            msg_type = "UtoACommands"  # Assuming you're only expecting this type of message
            UtoACommands_msg = recv_Ups_msg(ups_fd, msg_type)
            if UtoACommands_msg:
                print("UtoACommands_msg:\n ", UtoACommands_msg, "\n")
                # Process the message here
        except Exception as e:
            print(f"Error while receiving UPS message: {e}")
            break  # Exit the loop if there's an error



def main():
    # Establish connections
    
    world_fd, world_id = build_connect_world()
    ups_fd = create_server_socket(AMAZON_HOST, AMAZON_PORT)

    # Start listening threads
    ups_listener_thread = threading.Thread(target=listen_to_ups, args=(ups_fd,))
    ups_listener_thread.start()

    # Example: Sending a message after starting listening threads
    msg = createConnectWorldId_msg(world_id)  # Just as an example, create your message
    sendToUPS(ups_fd,msg)  # Send the message

    msg = createRequestTruck_msg(2,3,4,222,333,988)
    sendToUPS(ups_fd,msg)
    # Continue with other tasks
    # You can also start other threads here for different tasks

if __name__ == "__main__":
    main()
