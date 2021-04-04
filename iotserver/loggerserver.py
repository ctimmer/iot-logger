#! /usr/bin/python3
################################################################################
# iotserver.py
################################################################################

import socket
import threading
import time
import json
import mariadb, sys

from loggerconfig import *

db_pool = 0
t_data = threading.local ()     # local thread data
thread_count_high_water = 5     # slow down point

my_hostname = ''
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

initialize_timestamp = ''
unknown_device_type_name = "Unknown"
unknown_device_type_key = 0

#-------------------------------------------------------------------------------
# get_current_timestamp
# Outputs:
#   t_data.current_timestamp
#-------------------------------------------------------------------------------
def get_current_timestamp () :
    sql = ("select current_timestamp")

    cursor = t_data.db_conn.cursor (prepared=True)
    cursor.execute (sql,)
    result = cursor.fetchone ()
    cursor.close ()
    t_data.current_timestamp = result [0].strftime("%Y-%m-%d %H:%M:%S")

# end get_current_timestamp

#-------------------------------------------------------------------------------
# thread_setup
# Inputs:
#   db_conn - From connection pool
# Outputs:
#   t_data.db_conn
#   t_data.current_timestamp
#-------------------------------------------------------------------------------
def thread_setup (db_conn) :

    t_data.db_conn = db_conn
    get_current_timestamp ()

# end thread_setup

#-------------------------------------------------------------------------------
# thread_end
#-------------------------------------------------------------------------------
def thread_end () :

    t_data.db_conn.commit ()
    t_data.db_conn.close ()

# end thread_end

#-------------------------------------------------------------------------------
# set_initialize_timestamp
#-------------------------------------------------------------------------------
def set_initialize_timestamp (db_conn) :
    global initialize_timestamp         # OK, this is only called at startup
    global unknown_device_type_key      # type key for 'unknown' id

    thread_setup (db_conn)

    #---- set start up time
    initialize_timestamp = t_data.current_timestamp # update global

    #---- get 'unknown device type key'
    cursor = db_conn.cursor ()
    query = ("select type_key from device_types where name = %s")
    cursor.execute (query, (unknown_device_type_name, ))
    result = cursor.fetchone ()
    cursor.close ()
    if result :
        (unknown_device_type_key, ) = result    # set unknown type key

    thread_end ()

# end set_initialize_timestamp

#-------------------------------------------------------------------------------
# update_device_log
#-------------------------------------------------------------------------------
def update_device_log (device_key, request_dict) :
    sql = ("INSERT INTO device_log (device_key, log_date, log_data)"
            + " VALUES (%s, %s, %s)")

    #print ("update_device_log:", device_key)
    #print (request_dict)

    if 'nolog' in allowed_actions [request_dict['action']]:
        return

    log_dict = {
        request_dict['action'] : request_dict [request_dict['action']]
        }
    log_json = json.dumps (log_dict)
    # cursor = db_connection.cursor(prepared=True)
    cursor = t_data.db_conn.cursor(prepared=True)
    cursor.execute (sql,
                    (device_key,
                    t_data.current_timestamp,
                    log_json))
    cursor.close ()

# end update_device_log

#-------------------------------------------------------------------------------
# update_device
#-------------------------------------------------------------------------------
def update_device (device_key, device_log_dict, request_dict) :
    sql = ('UPDATE devices SET'
            + ' log_date = %s'
            + ', log_data = %s'
            + ' WHERE device_key = %s')

    #print ()
    #print ('device_update:', device_key)
    #print (device_log_dict)
    #print (request_dict)

    log_id = request_dict ['action']
    if log_id not in device_log_dict:
        device_log_dict [log_id] = {}
    for log_entry_key in request_dict [log_id]:
        device_log_dict [log_id][log_entry_key] \
            = request_dict [log_id][log_entry_key]
        device_log_dict [log_id][log_entry_key]['last_update'] \
            = t_data.current_timestamp
    #print (device_log_dict)
    device_log_json = json.dumps (device_log_dict)
    # cursor = db_connection.cursor (prepared=True)
    cursor = t_data.db_conn.cursor (prepared=True)
    cursor.execute (sql,
                    (t_data.current_timestamp,
                    device_log_json,
                    device_key))
    cursor.close ()
    update_device_log (device_key, request_dict)

# end update_device

#-------------------------------------------------------------------------------
# unknown_device
# Inputs:
#   log_dict_in - From client call
#   t_data.db_conn - From db pool
#   t_data.current_timestamp
#-------------------------------------------------------------------------------
def unknown_device (log_dict_in) :
    device_key = 0
    #print ()
    #print ('unknown_device')
    #print (log_dict_in)

    device_id = log_dict_in ['id']
    log_id = log_dict_in['action']
    log_dict = {                            # All log data
                log_id : log_dict_in [log_id]
                }
    for log_entry_key in log_dict [log_id]: # Set last update
        log_dict [log_id][log_entry_key]['last_update'] \
            = t_data.current_timestamp
    log_json = json.dumps (log_dict)
    cursor = t_data.db_conn.cursor()
    query = ('INSERT INTO devices'
            + ' (device_id, type_key, log_date, log_data)'
            + ' VALUES (%s, %s, %s, %s)')
    cursor.execute (query,                  # Insert device log data
                    (device_id,
                    unknown_device_type_key,
                    t_data.current_timestamp,
                    log_json))
    device_key = (cursor.lastrowid)
    #print ("dk:", device_key)
    cursor.close ()
    update_device_log (device_key, log_dict_in)

# end unknown_device

#-------------------------------------------------------------------------------
# process_request
# Inputs:
#   request_dict - From client 
#   t_data.db_conn - From db pool
#-------------------------------------------------------------------------------
def process_request (request_dict) :
    #print ('process_request')
    #print (request_dict)
    id = request_dict['id']
    #print (id)

    cursor = t_data.db_conn.cursor()
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
# process_request_thread
#-------------------------------------------------------------------------------
def process_request_thread (db_conn, request_dict) :

    thread_setup (db_conn)
    process_request (request_dict)
    thread_end ()
    # time.sleep (95.0)                 # for testing threads

# end process_request_thread

#-------------------------------------------------------------------------------
# ping_handler
#-------------------------------------------------------------------------------
def ping_handler (db_conn, request_dict, reply_ip) :
    global CLIENT_CONFIG
    global initialize_timestamp

    #print ("ping_handler:")
    thread_setup (db_conn)
    reply_dict = {
        'action' : 'pong' ,
        'pong' : request_dict ['ping'] ,
        'server' : {
            'hostname' : my_hostname ,
            'initialized' : initialize_timestamp ,
            'current' : t_data.current_timestamp
            }
        }

    (ip, port) = reply_ip
    result_json = json.dumps (reply_dict)
    bytesToSend = str.encode (result_json)
    UDPServerSocket.sendto (bytesToSend, (ip, CLIENT_CONFIG ['LISTENER_PORT']))

    thread_end ()

# end ping_handler

#-------------------------------------------------------------------------------
# wait_for_request
# Inputs:
#   UDP messsage from client
#-------------------------------------------------------------------------------
def wait_for_request () :
    global SERVER_CONFIG
    global allowed_actions

    while (True):
        bytesAddressPair = UDPServerSocket.recvfrom \
                            (SERVER_CONFIG['BUFFER_SIZE'])
        message = bytesAddressPair[0]
        address = bytesAddressPair[1]
        #clientMsg = "Message from Client:{}".format(message)
        #clientIP  = "Client IP Address:{}".format(address)
        #print ()
        #print(clientIP)
        try :
            request_json = message.decode(encoding="ascii", errors="ignore")
            request_dict = json.loads (request_json)
        except :
            print ("wfr: except")
            continue                        # input message format error
        if not 'id' in request_dict:        # 'id' key missing
            continue
        if not 'action' in request_dict:
            continue                        # No 'action' id in request
        if request_dict ['action'] in allowed_actions:
            action_dict = allowed_actions [request_dict ['action']]
        else :
            # Could add to allowed_actions instead of skipping
            continue                        # unknown 'action' value
        if threading.active_count() >= thread_count_high_water :
            time.sleep (0.5)                # everyone out of the pool
        try:
            db_connection = db_pool.get_connection ()
        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            continue
        if 'handler' in action_dict :
            t1 = threading.Thread (target=action_dict['handler'],
                                    name=request_dict['action'] ,
                                    args=(db_connection,
                                            request_dict,
                                            address))
            t1.start()
        else :
            t1 = threading.Thread (target=process_request_thread,
                                    name=request_dict['action'] ,
                                    args=(db_connection, request_dict))
            t1.start()
        # print ("wfr:", threading.active_count())
        # print (threading.enumerate())
    # end while

# end wait_for_request

#-------------------------------------------------------------------------------
# initialize
# Outputs:
#   UDPServerSocket (global)            # request socket
#   my_hostname (global)                # server hostname
#   db_pool (global)                    # db connection pool
#   thread_count_high_water             # start slow down
#   initialize_timestamp (global)       # startup time
#   unknown_device_type_key (global)    # for seting up new devices
#-------------------------------------------------------------------------------
def initialize () :
    global DB_CONFIG
    global SERVER_CONFIG
    global UDPServerSocket
    global my_hostname
    global db_pool
    global thread_count_high_water

    try :
        UDPServerSocket = socket.socket (family=socket.AF_INET,
                                        type=socket.SOCK_DGRAM)
        # Bind to address and ip
        UDPServerSocket.bind ((SERVER_CONFIG['LOCAL_IP'],
                                SERVER_CONFIG['LISTENER_PORT']))
        my_hostname = socket.gethostname ()
    except e:
        print(f"Error in UDP socket set up: {e}")
        sys.exit(1)
    print("logger server listening")

    try:
        db_pool = mariadb.ConnectionPool (  # initialize db connection pool
            pool_name='db_pool' ,
            pool_size=DB_CONFIG['POOLSIZE'] ,
            pool_reset_connection = False ,
            host=DB_CONFIG['HOSTNAME'] ,
            port=DB_CONFIG['PORT'] ,
            user=DB_CONFIG['USERNAME'] ,
            passwd=DB_CONFIG['PASSWORD'] ,
            database=DB_CONFIG['DATABASE']
            )
        thread_count_high_water = DB_CONFIG['POOLSIZE'] - 2
        #---- Set start time, et. al.
        ts_thread = threading.Thread (target=set_initialize_timestamp,
                                        args=(db_pool.get_connection(),))
        ts_thread.start ()
        ts_thread.join ()               # wait for thread to complete
    except mariadb.Error as e:
        print(f"Error MariaDB Platform: {e}")
        sys.exit(1)
    print ('database connection pool initialized')

    allowed_actions ['ping']['handler'] = ping_handler

# end initialize

#-------------------------------------------------------------------------------
# main
#-------------------------------------------------------------------------------

initialize ()

wait_for_request ()

db_pool.close ()

