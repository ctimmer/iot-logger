#! /usr/bin/python3
################################################################################
# iotwebserver.py
#
#
################################################################################

import http.server
import socketserver
import socket
from urllib.parse import urlparse
from urllib.parse import parse_qs

import mariadb, sys

import time
import json

#import mako
from mako.template import Template

from loggerconfig import *

# Globals:
my_hostname = ''
iot_web_server = False
db_connection = False
db_date_format = '%Y-%m-%d %H:%M:%S'
low_date = "0000-00-00 00:00:00"
initialize_timestamp = low_date

################################################################################
# database functions
################################################################################

#-------------------------------------------------------------------------------
# get_current_timestamp
#-------------------------------------------------------------------------------
def get_current_timestamp () :
    global low_date
    sql = "select current_timestamp" 
    try :
        cursor = db_connection.cursor (prepared=True, buffered=True)
        cursor.execute (sql)
        result = cursor.fetchone ()
        #db_connection.commit ()
        cursor.close ()
        return (result [0].strftime(db_date_format))
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        return (low_date)

# end get_current_timestamp

#-------------------------------------------------------------------------------
# initialize_return_message
#-------------------------------------------------------------------------------
def initialize_return_message () :

    return ({
            'result' : {'error_code' : 0} ,
            'reply' : []
            })

# end initialize_return_message

#-------------------------------------------------------------------------------
# set_result_code
#-------------------------------------------------------------------------------
def set_result_code (return_dict, code, message) :

    return_dict['result']['error_code'] = code
    if message :
        return_dict['result']['error_message'] = message

    return (return_dict)

# end set_result_code

#-------------------------------------------------------------------------------
# copy_log_to_reply
#-------------------------------------------------------------------------------
def copy_log_to_reply (device_log, reply_dict, log_id, date_cutoff) :

    log_dict = json.loads (device_log)  # parse json log data
    if not log_id in log_dict :
        return (False)                  # log_id (eg 'heartbeat') missing
    temp_dict = {log_id : {}}
    copy_count = 0
    for log_key in log_dict [log_id] :
        if log_dict [log_id][log_key]['last_update'] <= date_cutoff :
            continue                    # Old entry, before cut off date
        temp_dict[log_id][log_key] = log_dict [log_id][log_key]
        copy_count += 1
    if copy_count <= 0 :
        return (Fale)                   # No entries copied
    reply_dict [log_id] = temp_dict
    return (True)                       # At least 1 entry copied

# end copy_log_to_reply

#-------------------------------------------------------------------------------
# get_device_list
#-------------------------------------------------------------------------------
def get_device_list () :
    global db_connection
    self = get_device_list
    self.sql = 'SELECT' \
                + ' devices.device_id' \
                + ',devices.description' \
                + ',devices.log_date' \
                + ',device_types.name' \
                + ' FROM' \
                + ' devices' \
                + ',device_types' \
                + ' WHERE' \
                + ' device_types.type_key = devices.type_key' \
                + ' ORDER BY' \
                + ' devices.device_id'

    return_dict = initialize_return_message ()
    try :
        self.cursor = db_connection.cursor (prepared=True, buffered=True)
        self.cursor.execute (self.sql)
        result = self.cursor.fetchall ()
        for row in result :
            return_dict['reply'].append (
                {
                'device_id' : row [0] ,
                'description' : row[1] ,
                'last_log_date' : row[2].strftime (db_date_format) ,
                'type' : row[3]
                })
        #db_connection.commit ()
        self.cursor.close ()
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_list: {e}")

    return (return_dict)

# end get_device_list

#-------------------------------------------------------------------------------
# get_device_type_list
#-------------------------------------------------------------------------------
def get_device_type_list () :
    global db_connection
    sql = 'SELECT' \
            + ' device_types.name' \
            + ' FROM' \
            + ' device_types' \
            + ' ORDER BY' \
            + ' device_types.name'

    return_dict = initialize_return_message ()
    try :
        cursor = db_connection.cursor (prepared=True, buffered=True)
        cursor.execute (sql)
        result = cursor.fetchall ()
        cursor.close ()
        for row in result :
            return_dict['reply'].append (
                {
                'device_type' : row [0]
                })
        #db_connection.commit ()
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_type_list: {e}")

    return (return_dict)

# end get_device_type_list

#-------------------------------------------------------------------------------
# get_type_status
#-------------------------------------------------------------------------------
def get_type_status (type_name, log_id, log_date_cutoff) :
    global db_connection
    self = get_type_status
    self.sql = 'SELECT' \
                + ' devices.device_id' \
                + ',device_types.name' \
                + ',devices.log_date' \
                + ',devices.log_data' \
                + ' FROM' \
                + ' devices' \
                + ',device_types' \
                + ' WHERE' \
                + ' device_types.name = %s' \
                + ' AND' \
                + ' devices.type_key = device_types.type_key' \
                + ' AND' \
                + ' devices.log_date > %s' \
                + ' ORDER BY' \
                + ' devices.device_id'

    #print (self.sql)

    return_dict = initialize_return_message ()
    next_date_cutoff = log_date_cutoff
    #set_result_code (return_dict, 1, "OK")
    #print (return_dict)
    try :
        self.cursor = db_connection.cursor (prepared=True, buffered=True)
        self.cursor.execute (self.sql, (type_name, log_date_cutoff))
        result = self.cursor.fetchall ()
        for row in result :
            last_log_date = row[2].strftime (db_date_format)
            if last_log_date <= log_date_cutoff :
                continue
            if next_date_cutoff < last_log_date :
                next_date_cutoff = last_log_date
            log_dict = {}
            if not copy_log_to_reply (row[3],
                                log_dict,
                                log_id,
                                log_date_cutoff):
                continue
            reply_log_data = {
                'device_id' : row [0] ,
                'type' : row[1] ,
                'last_log_date' : last_log_date ,
                'log_data' : log_dict
                }
            return_dict['reply'].append (reply_log_data)
        #db_connection.commit ()
        self.cursor.close ()
        return_dict ['log_date_cutoff'] = next_date_cutoff
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_type_status: {e}")

    return (return_dict)

# end get_type_status

#-------------------------------------------------------------------------------
# get_type_status_all
#-------------------------------------------------------------------------------
def get_type_status_all (type_name, log_id) :

    return (get_type_status (type_name, log_id, low_date))

# end get_type_status_all

################################################################################
# Server functions
################################################################################

#-----------------------------------
# device_list_handler
#-----------------------------------
def device_list_handler (request_dict) :

    return (get_device_list ())

# end device_list_handler

#-----------------------------------
# device_list_handler_t
#-----------------------------------
def device_list_handler_t (request_dict) :

    template_dict =  get_device_list ()

    ### Call mako template

    return (not_implemented)

# end device_list_handler_t

#-----------------------------------
# type_status_handler
#-----------------------------------
def type_status_handler (request_dict) :
# get_type_status (type_name, log_id, log_date_cutoff) :

    date_cutoff = low_date
    if not 'type' in request_dict :
        return (set_result_code (initialize_return_message () , # missing type
                                -1 ,
                                "Missing 'type' entry"))
    if not 'log_id' in request_dict :
        return (set_result_code (initialize_return_message () ,# missing log_id
                                -1 ,
                                "Missing 'log_id' entry"))
    if 'date_cutoff' in request_dict :                         # use cutoff date
        date_cutoff = request_dict ['date_cutoff']

    return (get_type_status (request_dict ['type'] ,           # get the results
                            request_dict ['log_id'] ,
                            date_cutoff))

# end type_status_handler

#-------------------------------------------------------------------------------
# home_page_handler
#-------------------------------------------------------------------------------
def home_page_handler (request_dict) :

    #ret = get_type_status_all ("Computer", "heartbeat")      ## TESTING
    #print (ret)
    #ret = get_type_status ("Computer", "heartbeat", ret['log_date_cutoff'])
    #print (ret)

    mytemplate = Template (filename='templates/home.txt',
                        module_directory='/tmp/mako_modules')
    return (mytemplate.render())

# end home_page_handler

#-------------------------------------------------------------------------------
# maintenence_page_handler
#-------------------------------------------------------------------------------
def maintenence_page_handler (request_dict) :

    #ret = get_type_status_all ("Computer", "heartbeat")      ## TESTING
    #print (ret)
    #ret = get_type_status ("Computer", "heartbeat", ret['log_date_cutoff'])
    #print (ret)

    mytemplate = Template (filename='templates/maintenence.txt',
                        module_directory='/tmp/mako_modules')
    return (mytemplate.render())

# end maintenence_page_handler

#-----------------------------------
# action_dict
#-----------------------------------
action_dict = {
#----
#---- GET requests
#----
    'home' : {
        'handler' : home_page_handler ,
        'content_type' : 'text/html'
        } ,
    'maintenence' : {
        'handler' : maintenence_page_handler ,
        'content_type' : 'text/html'
        } ,
    #'kiosk' : {
        #'handler' : kiosk_page_handler ,
        #'content_type' : 'text/html'
        #} ,
#----
#---- POST requests
#----
    'device_list' : {
        'handler' : device_list_handler ,
        'content_type' : 'application/json'
        } ,
    'device_list_t' : {
        'handler' : device_list_handler_t ,
        'content_type' : 'text/html'
        } ,
    'type_status' : {
        'handler' : type_status_handler ,
        'content_type' : 'application/json'
        } ,
#----
#---- plain text requests
#----
    'error' : {
        'content_type' : 'test/plain'
        }
    }

#-------------------------------------------------------------------------------
# request_handler
#   Validate 'action' value
#   Call 'action' handler function
#-------------------------------------------------------------------------------
def request_handler (request_dict) :
    global action_dict

    if not 'action' in request_dict :       # Check for 'action' key
        request_dict ['action'] = 'error'
        return ("Missing 'action' entry")

    action = request_dict ['action']                       

    if not action in action_dict :          # Validate 'action' value
        request_dict ['action'] = 'error'
        return (f"Invalid action: '{action}'")
 
    try:                                    # Process 'action' handler
        db_connection = mariadb.connect (host=DB_CONFIG['HOSTNAME'] ,
                                        port=DB_CONFIG['PORT'] ,
                                        user=DB_CONFIG['USERNAME'] ,
                                        passwd=DB_CONFIG['PASSWORD'] ,
                                        database=DB_CONFIG['DATABASE'])
        return (action_dict[action]['handler'] (request_dict))
        db_connection.close ()
    except mariadb.Error as e:
        request_dict ['action'] = 'error'
        return (f"Error connecting to MariaDB Platform: {e}")

# end request_handler

#-------------------------------------------------------------------------------
# get_handler
#-------------------------------------------------------------------------------
def Xget_handler (parm_dict) :
    print ("get_handler: ", parm_dict)
    

# end Xget_handler

#-------------------------------------------------------------------------------
# MyServer
#-------------------------------------------------------------------------------
class MyServer (http.server.SimpleHTTPRequestHandler):

    def send_reply (self, action, reply_text) :
        self.send_response (200)
        self.send_header ("Content-type", action_dict[action]['content_type'])
        self.end_headers ()
        self.wfile.write (bytes (reply_text, "utf-8"))
    # end send_reply

#---- Inputs:
#----   path = '/' return home page
#----   otherwise - pass to server to handle
    def do_GET (self):
        path_dict = urlparse(self.path)
        request_dict = parse_qs (path_dict.query)
        if path_dict.path == '/' :
            request_dict ['action'] = 'home'
        elif path_dict.path == '/maintenence' :
            request_dict ['action'] = 'maintenence'
        else :
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        get_data = request_handler (request_dict)
        self.send_reply (request_dict['action'], get_data)
        #--- Old:
            #get_data = get_handler (parse_qs (path_dict.query))
            #self.send_response (200)
            #self.send_header ("Content-type", "text/html")
            #self.end_headers ()
            #self.wfile.write (bytes (get_data, "utf-8"))

#---- Inputs:
#----   json formatted reqest message
#---- Outputs:
#----   json formatted reply message
    def do_POST (self):
        #request_handler (self)
        self.send_response (200)
        self.send_header ("Content-type", "application/json")
        self.end_headers ()
        try :
            length = int (self.headers ['Content-Length'])
            post_data = self.rfile.read (length).decode ('utf-8')
            request_dict = json.loads (post_data)
            reply_dict = request_handler (request_dict)
        except :
            reply_dict = set_result_code (initialize_return_message () ,
                                        -1 ,
                                        "Invalid input message format")
        self.wfile.write (bytes (json.dumps (reply_dict), 'utf-8'))

# end MyServer

################################################################################
# initilize, main
################################################################################

#-------------------------------------------------------------------------------
# initialize
#-------------------------------------------------------------------------------
def initialize () :
    global my_hostname
    global iot_web_server
    global db_connection
    global initialize_timestamp

    my_hostname = socket.gethostname ()

    #iot_web_server = HTTPServer(('localhost',      
                                #SERVER_CONFIG ['LISTENER_PORT']),
                                #MyServer)
    handler_object = MyServer
    iot_web_server = socketserver.TCPServer(("", 5010), handler_object)
    print ("Server started http://%s:%s" % \
            ('localhost', SERVER_CONFIG ['LISTENER_PORT']))

    try:
        db_connection = mariadb.connect (host=DB_CONFIG['HOSTNAME'] ,
                                        port=DB_CONFIG['PORT'] ,
                                        user=DB_CONFIG['USERNAME'] ,
                                        passwd=DB_CONFIG['PASSWORD'] ,
                                        database=DB_CONFIG['DATABASE'])
        cursor = db_connection.cursor ()
        cursor.execute ("SET AUTOCOMMIT=ON")
        #db_connection.commit ()
        cursor.close ()
        initialize_timestamp = get_current_timestamp ()
        db_connection.close ()
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    print ('Conndected to database:%s at %s' 
            % (DB_CONFIG['DATABASE'] ,
            initialize_timestamp))

# end initalize

#-------------------------------------------------------------------------------
# main
#-------------------------------------------------------------------------------

if __name__ == "__main__":        

    initialize ()

    try:
        iot_web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    print ()

    iot_web_server.server_close()
    print("Server stopped.")

