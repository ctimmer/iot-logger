#! /usr/bin/python3

import socket
import time
import json
import mariadb, sys

from loggerconfig import *

db_connection = 0
UDPServerSocket = 0

allowed_actions = {
    "alert" : {} ,
    "heartbeat" : {} ,
    "notification" : {} ,
    "ping" : {
        'nolog' : True
        } ,
    "state" : {} 
    }

my_hostname = ''
initialize_timestamp = ''
#current_timestamp = 0
unknown_device_type_name = "Unknown"
unknown_device_type_key = 0

current_timestamp_sql = ("select current_timestamp")
current_timestamp_cursor = False
update_device_sql = ('UPDATE devices SET'
                    + ' log_date = %s'
                    + ', log_data = %s'
                    + ' WHERE device_key = %s')
update_device_cursor = False
update_log_sql = ('INSERT INTO device_log (device_key, log_date, log_data)'
                    + ' VALUES (%s, %s, %s)')
update_log_cursor = False

#-------------------------------------------------------------------------------
# get_current_timestamp
#-------------------------------------------------------------------------------
def get_current_timestamp () :
    global current_timestamp_sql
    global current_timestamp_cursor

    current_timestamp_cursor = db_connection.cursor (prepared=True)
    current_timestamp_cursor.execute (current_timestamp_sql,)
    result = current_timestamp_cursor.fetchone ()
    current_timestamp_cursor.close ()
    return (result [0].strftime("%Y-%m-%d %H:%M:%S"))

# end get_current_timestamp

#-------------------------------------------------------------------------------
# update_device_log
#-------------------------------------------------------------------------------
def update_device_log (device_key, request_dict, time_stamp) :
    global update_log_sql
    global update_log_cursor

    #print ("update_device_log:", device_key)
    #print (request_dict)

    if 'nolog' in allowed_actions [request_dict['action']]:
        return

    log_dict = {
        request_dict['action'] : request_dict [request_dict['action']]
        }
    log_json = json.dumps (log_dict)
    update_log_cursor = db_connection.cursor(prepared=True)
    #query = ('INSERT INTO device_log (device_key, log_date, log_data)'
            #+ ' VALUES (%s, %s, %s)')
    update_log_cursor.execute (update_log_sql,
                                (device_key, time_stamp, log_json))
    update_log_cursor.close ()

# end update_device_log

#-------------------------------------------------------------------------------
# update_device
#-------------------------------------------------------------------------------
def update_device (device_key, device_log_dict, request_dict) :
    global update_device_sql
    global update_device_cursor

    time_stamp = get_current_timestamp ()
    #print ()
    #print ('device_update:', device_key)
    #print (device_log_dict)
    #print (request_dict)

    log_id = request_dict ['action']
    if log_id not in device_log_dict:
        device_log_dict [log_id] = {}
    #device_log_dict [log_id]['last_update'] = time_stamp
    for log_key in request_dict [log_id]:
        device_log_dict [log_id][log_key] \
            = request_dict [log_id][log_key]
        device_log_dict [log_id][log_key]['last_update'] \
            = time_stamp
    #print (device_log_dict)
    device_log_json = json.dumps (device_log_dict)
    update_device_cursor = db_connection.cursor (prepared=True)
    update_device_cursor.execute (update_device_sql,
                                (time_stamp, device_log_json, device_key))
    update_device_cursor.close ()
    update_device_log (device_key, request_dict, time_stamp)

# end update_device

#-------------------------------------------------------------------------------
# unknown_device
#-------------------------------------------------------------------------------
def unknown_device (log_dict_in) :
    time_stamp = get_current_timestamp ()
    device_key = 0
    #print ()
    #print ('unknown_device')
    #print (log_dict_in)

    device_id = log_dict_in ['id']
    log_id = log_dict_in['action']
    log_dict = {
                log_id : log_dict_in [log_id]
                }
    for log_key in log_dict [log_id]:
        log_dict [log_id][log_key]['last_update'] = time_stamp
    #log_dict [log_id]['last_update'] = time_stamp
    log_json = json.dumps (log_dict)
    #print (log_dict)
    #return
    cursor = db_connection.cursor()
    query = ('INSERT INTO devices'
            + ' (device_id, type_key, log_date, log_data)'
            + ' VALUES (%s, %s, %s, %s)')
    cursor.execute (query,
                    (device_id, unknown_device_type_key, time_stamp, log_json))
    device_key = (cursor.lastrowid)
    print ("dk:", device_key)
    cursor.close ()
    update_device_log (device_key, log_dict_in, time_stamp)

# end unknown_device

#-------------------------------------------------------------------------------
# process_request
#-------------------------------------------------------------------------------
def process_request (request_dict) :
    #print ('process_request')
    #print (request_dict)
    id = request_dict['id']
    #print (id)

    cursor = db_connection.cursor()
    query = ("select device_key,"
            + " log_data from devices"
            + " where devices.device_id = %s")
    cursor.execute (query, (id,))
    result = cursor.fetchone ()
    cursor.close ()
    if result:
        #print (result)
        (device_key, log_data) = result
        log_dict = json.loads (log_data)
        update_device (device_key, log_dict, request_dict)
    else:
        #print ("none")
        unknown_device (request_dict)

# end process_request

#-------------------------------------------------------------------------------
# ping_handler
#-------------------------------------------------------------------------------
def ping_handler (request_dict, reply_ip) :
    global CLIENT_CONFIG
    global initialize_timestamp

    #print ("ping_handler:")
    reply_dict = {
        'action' : 'pong' ,
        'pong' : request_dict ['ping'] ,
        'server' : {
            'hostname' : my_hostname ,
            'initialized' : initialize_timestamp ,
            'current' : get_current_timestamp ()
            }
        }

    (ip, port) = reply_ip
    result_json = json.dumps (reply_dict)
    bytesToSend = str.encode (result_json)
    UDPServerSocket.sendto (bytesToSend, (ip, CLIENT_CONFIG ['LISTENER_PORT']))

# end ping_handler

#-------------------------------------------------------------------------------
# wait_for_request
#-------------------------------------------------------------------------------
def wait_for_request () :
    global SERVER_CONFIG
    global allowed_actions
    while(True):

        bytesAddressPair = UDPServerSocket.recvfrom \
                            (SERVER_CONFIG['BUFFER_SIZE'])
        message = bytesAddressPair[0]
        address = bytesAddressPair[1]
        #clientMsg = "Message from Client:{}".format(message)
        #clientIP  = "Client IP Address:{}".format(address)
        #print ()
        #print(clientIP)
        request_json = message.decode(encoding="ascii", errors="ignore")
        request_dict = json.loads (request_json)
        if not 'action' in request_dict:
            continue
        if not request_dict ['action'] in allowed_actions:
            continue
        action_dict = allowed_actions [request_dict ['action']]
        if not 'id' in request_dict:
            continue
        if not 'handler' in action_dict :
            process_request (request_dict)
        else :
            action_dict ['handler'] (request_dict, address)
        db_connection.commit ()
        # Sending a reply to client
        #UDPServerSocket.sendto(bytesToSend, address)

# end wait_for_request

#-------------------------------------------------------------------------------
# initialize
#-------------------------------------------------------------------------------
def initialize () :

    global DB_CONFIG
    global SERVER_CONFIG
    global UDPServerSocket
    global my_hostname
    global db_connection 
    global initialize_timestamp
    global current_timestamp_cursor
    global unknown_device_type_key

    UDPServerSocket = socket.socket (family=socket.AF_INET,
                                    type=socket.SOCK_DGRAM)
    # Bind to address and ip
    UDPServerSocket.bind ((SERVER_CONFIG['LOCAL_IP'],
                            SERVER_CONFIG['LISTENER_PORT']))
    my_hostname = socket.gethostname ()
    print("logger server listening")

    try:
        db_connection = mariadb.connect (host=DB_CONFIG['HOSTNAME'] ,
                                        port=DB_CONFIG['PORT'] ,
                                        user=DB_CONFIG['USERNAME'] ,
                                        passwd=DB_CONFIG['PASSWORD'] ,
                                        database=DB_CONFIG['DATABASE'])
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    initialize_timestamp = get_current_timestamp ()
    print ('Conndected to database')

    cursor = db_connection.cursor()
    query = ("select type_key from device_types where name = %s")
    cursor.execute (query, (unknown_device_type_name, ))
    result = cursor.fetchone ()
    cursor.close ()
    if result :
        (unknown_device_type_key, ) = result
    #print (unknown_device_type_key)

    allowed_actions ['ping']['handler'] = ping_handler

# end initialize

#-------------------------------------------------------------------------------
# main
#-------------------------------------------------------------------------------

initialize ()

wait_for_request ()

connection.close()

