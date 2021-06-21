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

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

from loggerconfig import *

# Globals:
my_hostname = ''
iot_web_server = False
db_connection = False
db_date_format = '%Y-%m-%d %H:%M:%S'
low_date = "0000-00-00 00:00:00"
initialize_timestamp = low_date

error_ids = {
    'OK' :      {'code' : 0 ,
                'system' : 'No error' ,
                'user' : 'No error' ,
                'other' : ''} ,
    'ACTION_MISSING' :  {'code' : -1 ,
                'system' : 'Action missing from request message' ,
                'user' : 'Action identifier required'} ,
    'ACTION_MISSING' :  {'code' : -2 ,
                'system' : "Action requested was not in 'action_dict'" ,
                'user' : 'Action identifier unknown'} ,
    'DATABASE' : {'code' : -100 ,
                'system' : 'Database error' ,
                'user' : 'There is a problem with the database'} ,
    'UNKNOWN' : {"code" : -999 ,
                "system" : "Unknow error reply" ,
                "user" : "Don't know what went wrong"} 
    }

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
        cursor.close ()
        return (result [0].strftime(db_date_format))
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        return (low_date)

# end get_current_timestamp

#-------------------------------------------------------------------------------
# initialize_json_return
#-------------------------------------------------------------------------------
def initialize_json_return () :

    return ({
            'result' : {'error_code' : 0} ,
            'reply' : []
            })

# end initialize_json_return

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
# error_reply_json
#-------------------------------------------------------------------------------
def error_reply_json (error_id, error_message) :
    reply = ''

    return reply

# end error_reply_json

#-------------------------------------------------------------------------------
# error_reply_html
#-------------------------------------------------------------------------------
def error_reply_html (error_id, error_message) :
    reply = ''

    return reply

# end error_reply_html

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
        return (False)                  # No entries copied
    reply_dict [log_id] = temp_dict
    return (True)                       # At least 1 entry copied

# end copy_log_to_reply

#-------------------------------------------------------------------------------
# get_device_list
# Inputs:
#   device_id - If set returns only 1 or none device, "" returns all devices
#-------------------------------------------------------------------------------
def get_device_list (device_id) :
    global db_connection
    sql = 'WITH' \
            + ' device_table (device_id) as (SELECT %s)' \
        + "SELECT" \
            + " devices.device_key" \
            + ",devices.device_id" \
            + ",devices.description" \
            + ",devices.log_date" \
            + ",COALESCE (device_types.name, 'Unknown')" \
        + " FROM" \
            + " device_table" \
            + ",devices" \
            + " LEFT OUTER JOIN" \
            + " device_types" \
            + " ON" \
            + " device_types.type_key = devices.type_key" \
        + " WHERE" \
            + ' (' \
            + ' device_table.device_id = ""' \
            + ' OR' \
            + ' devices.device_id = device_table.device_id' \
            + ' )' \
        + " ORDER BY" \
            + " devices.device_id"

    return_dict = initialize_json_return ()
    try :
        cursor = db_connection.cursor (prepared=True, buffered=True)
        cursor.execute (sql, (device_id,))
        result = cursor.fetchall ()
        for row in result :
            return_dict['reply'].append (
                {
                'device_key' : row [0] ,
                'device_id' : row [1] ,
                'description' : row[2] ,
                'last_log_date' : row[3].strftime (db_date_format) ,
                'type' : row[4]
                })
        #db_connection.commit ()
        cursor.close ()
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_list: {e}")

    return (return_dict)

# end get_device_list

#-------------------------------------------------------------------------------
# get_device_status
#-------------------------------------------------------------------------------
def get_device_status (device_id, log_id) :
    global db_connection
    sql = "SELECT" \
            + " devices.device_id" \
            + ",devices.log_date" \
            + ',devices.log_data' \
            + " FROM" \
            + " devices" \
            + " WHERE" \
            + " devices.device_id = %s"

    return_dict = initialize_json_return ()
    try :
        cursor = db_connection.cursor (buffered=True)
        cursor.execute (sql, (device_id,))
        row = cursor.fetchone ()
        cursor.close ()
        #log_id_data = {}
        #log_data = json.loads (row [2])
        #if log_id in log_data :
            #log_id_data [log_id] = log_data [log_id]
        return_dict['reply'].append (
            {
            'device_id' : row [0] ,
            'last_log_date' : row[1].strftime (db_date_format) ,
            'log_data' : json.loads (row [2])
            })
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_status: {e}")

    return (return_dict)

# end get_device_status

#-------------------------------------------------------------------------------
# get_device_status_changes
#-------------------------------------------------------------------------------
def get_device_status_changes (log_id, log_date_cutoff) :
    global db_connection
    sql = "SELECT" \
            + " devices.device_id" \
            + ",devices.log_date" \
            + ',devices.log_data' \
            + " FROM" \
            + " devices" \
            + " WHERE" \
            + ' devices.log_date > %s'

    return_dict = initialize_json_return ()
    next_date_cutoff = log_date_cutoff
    try :
        cursor = db_connection.cursor (buffered=True)
        cursor.execute (sql, (log_date_cutoff,))
        result = cursor.fetchall ()
        cursor.close ()
        for row in result :
            last_log_date = row[1].strftime (db_date_format)
            if last_log_date <= log_date_cutoff :
                continue
            if next_date_cutoff < last_log_date :
                next_date_cutoff = last_log_date
            log_dict = {}
            if not copy_log_to_reply (row[2],
                                    log_dict,
                                    log_id,
                                    log_date_cutoff):
                continue
            reply_change_data = {}
            reply_change_data['device_id'] = row [0]
            reply_change_data['last_log_date'] = row[1].strftime(db_date_format)
            reply_change_data['log_data'] = json.loads (row [2])
            return_dict['reply'].append (reply_change_data)
        return_dict ['log_date_cutoff'] = next_date_cutoff
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_status_changes: {e}")

    return (return_dict)

# end get_device_status_changes

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

    return_dict = initialize_json_return ()
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
# get_device_all
#-------------------------------------------------------------------------------
def get_device_all (log_id, type_name) :
    global db_connection
    sql = 'WITH' \
            + ' type_table (type) as (SELECT %s)' \
        + ' SELECT' \
            + ' devices.device_id AS device_id' \
            + ',devices.log_date' \
            + ',devices.log_data' \
            + ',device_types.name' \
        + ' FROM' \
            + ' type_table' \
            + ',devices' \
            + ',device_types' \
        + ' WHERE' \
            + ' devices.type_key = device_types.type_key' \
            + ' AND' \
            + ' (' \
            + ' type_table.type = ""' \
            + ' OR' \
            + ' device_types.name = type_table.type' \
            + ' )' \
        + ' ORDER BY' \
            + ' devices.device_id'

    return_dict = initialize_json_return ()
    next_date_cutoff = low_date
    #set_result_code (return_dict, 1, "OK")
    #print (return_dict)
    try :
        cursor = db_connection.cursor (buffered=True)
        #cursor.execute (sql, ('heartbeat', type_name))
        cursor.execute (sql, (type_name, 'heartbeat'))
        result = cursor.fetchall ()
        cursor.close ()
        for row in result :
            last_log_date = row[1].strftime (db_date_format)
            #if last_log_date <= log_date_cutoff :
                #continue
            if next_date_cutoff < last_log_date :
                next_date_cutoff = last_log_date
            log_dict = {}
            if not copy_log_to_reply (row[2],
                                log_dict,
                                log_id,
                                low_date):
                                ## log_date_cutoff):
                continue
            reply_log_data = {}
            reply_log_data['device_id'] = row [0]
            reply_log_data['last_log_date'] = row[1].strftime(db_date_format)
            #reply_log_data['log_data'] = row [2]
            reply_log_data['log_data'] = json.loads (row [2])
            if type_name != "" :
                reply_log_data['type'] = row [3]
            return_dict['reply'].append (reply_log_data)
        #db_connection.commit ()
        return_dict ['log_date_cutoff'] = next_date_cutoff
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_device_all: {e}")

    return (return_dict)

# end get_device_all

#-------------------------------------------------------------------------------
# get_type_status
#-------------------------------------------------------------------------------
def get_type_status (type_name, log_id, log_date_cutoff) :
    global db_connection
    sql = 'SELECT' \
            + ' devices.device_id AS device_id' \
            + ',devices.log_date' \
            + ',devices.log_data' \
            + ',device_types.name' \
            + ' FROM' \
            + ' devices' \
            + ',device_types'
    sql += ' WHERE'
    if type_name != "" :
        sql += ' device_types.name = %s' \
            + ' AND'
    sql += ' devices.type_key = device_types.type_key' \
            + ' AND' \
            + ' devices.log_date > %s' \
            + ' ORDER BY' \
            + ' devices.device_id'

    return_dict = initialize_json_return ()
    next_date_cutoff = log_date_cutoff
    #set_result_code (return_dict, 1, "OK")
    #print (return_dict)
    try :
        cursor = db_connection.cursor (buffered=True)
        cursor.execute (sql, (type_name, log_date_cutoff))
        result = cursor.fetchall ()
        cursor.close ()
        for row in result :
            last_log_date = row[1].strftime (db_date_format)
            if last_log_date <= log_date_cutoff :
                continue
            if next_date_cutoff < last_log_date :
                next_date_cutoff = last_log_date
            log_dict = {}
            if not copy_log_to_reply (row[2],
                                log_dict,
                                log_id,
                                log_date_cutoff):
                continue
            reply_log_data = {}
            reply_log_data['device_id'] = row [0]
            reply_log_data['last_log_date'] = row[1].strftime(db_date_format)
            #reply_log_data['log_data'] = row [2]
            reply_log_data['log_data'] = json.loads (row [2])
            if type_name != "" :
                reply_log_data['type'] = row [3]
            return_dict['reply'].append (reply_log_data)
        #db_connection.commit ()
        return_dict ['log_date_cutoff'] = next_date_cutoff
    except mariadb.Error as e:
        set_result_code (return_dict, -1, f"get_type_status: {e}")

    return (return_dict)

# end get_type_status

################################################################################
# Server functions
################################################################################

#-----------------------------------
# device_list_handler
#-----------------------------------
def device_list_handler (request_dict) :
    device_id = ""

    if 'device_id' in request_dict :
        device_id = request_dict ['device_id']

    return (get_device_list (device_id))

# end device_list_handler

#-----------------------------------
# device_list_handler_t - not implemented
#-----------------------------------
def device_list_handler_t (request_dict) :
    device_id = ""

    if 'device_id' in request_dict :
        device_id = request_dict ['device_id']

    template_dict =  get_device_list (device_id)

    ### Call mako template

    return (not_implemented)

# end device_list_handler_t

#-----------------------------------
# device_list_item_handler_t -
#-----------------------------------
def device_list_item_handler_t (request_dict) :
    #print ("device_list_item_handler_t:" )

    if not 'device_id' in request_dict :
        print ("device_list_item_handler_t: missing device_id")
        return ("")

    device_list_ret = get_device_list (request_dict ['device_id'])

    template_dict = {}
    template_dict['devices'] = {}
    template_dict['device_ids'] = []
    for device_entry in device_list_ret['reply'] :
        template_dict ['devices'][device_entry['device_id']] = {
            'device_key' : device_entry['device_key'] ,
            'description' : device_entry['description'] ,
            'type' : device_entry['type'] 
            }
        template_dict['device_ids'].append (device_entry['device_id'])

    try:
        mylookup = TemplateLookup(directories=['.'])
        mytemplate = Template (filename='templates/home_devices_items.txt',
                                module_directory='/tmp/mako_modules',
                                lookup=mylookup)
        html = mytemplate.render (**template_dict)
        return (html)
    except:
        print(exceptions.text_error_template().render())

    return ""

# end device_list_handler_t

#-----------------------------------
# device_status_handler
#-----------------------------------
def device_status_handler (request_dict) :

    if not 'device_id' in request_dict :
        reply_dict = set_result_code \
                        (initialize_json_return () , # missing device_id
                        -1 ,
                        "Missing 'device_id' entry")
    else :
        reply_dict = get_device_status (request_dict ['device_id'],
                                        low_date)  # get the results

    return (json.dumps (reply_dict))

# end device_status_handler

#-----------------------------------
# device_status_handler_t
#-----------------------------------
def device_status_handler_t (request_dict) :

    if not 'device_id' in request_dict :
        return ("Missing 'device_id' entry")
    status_dict = get_device_status (request_dict ['device_id'],
                                    low_date)   # get the results
    template_dict = status_dict['reply'][0]     # First (only) entry
    #print ("dsht:", template_dict)
    if not 'heartbeat' in template_dict['log_data'] :
        return ("No DEVICE heartbeat information available")

    try :
        mylookup = TemplateLookup(directories=['.'])
        mytemplate = Template (filename='templates/device_status.txt',
                            module_directory='/tmp/mako_modules',
                            lookup=mylookup)
        return (mytemplate.render(**template_dict))
    except Exception as e :
        print (e)
        return ("Template setup/render failed")

# end device_status_handler_t

#-----------------------------------
# device_status_changes_handler
#-----------------------------------
def device_status_changes_handler (request_dict) :

    if not 'log_id' in request_dict :
        reply_dict = set_result_code \
                        (initialize_json_return () , # missing device_id
                        -1 ,
                        "Missing 'log_id' entry")
    else :
        if 'log_date_cutoff' in request_dict :
            log_date_cutoff = request_dict ['log_date_cutoff']
        else :
            log_date_cutoff = low_date
        reply_dict = get_device_status_changes \
                        (request_dict ['log_id'],
                        log_date_cutoff)  # get the results

    return (json.dumps (reply_dict))

# end device_status_changes_handler

#-----------------------------------
# type_status_handler - not implemented
#-----------------------------------
def type_status_handler (request_dict) :

    date_cutoff = low_date
    if not 'type' in request_dict :
        return (set_result_code (initialize_json_return () , # missing type
                                -1 ,
                                "Missing 'type' entry"))
    if not 'log_id' in request_dict :
        return (set_result_code (initialize_json_return () ,# missing log_id
                                -1 ,
                                "Missing 'log_id' entry"))
    if 'date_cutoff' in request_dict :                         # use cutoff date
        date_cutoff = request_dict ['date_cutoff']

    #return (get_type_status (request_dict ['type'] ,          # get the results
                            #request_dict ['log_id'] ,
                            #date_cutoff))

# end type_status_handler

#-------------------------------------------------------------------------------
# home_page_handler
#-------------------------------------------------------------------------------
def home_page_handler (request_dict) :

    global error_ids

    template_dict = {}

    device_list_ret = get_device_list ("")
    # print ( device_list_ret['reply'] )
    template_dict['devices'] = {}
    template_dict['device_ids'] = []
    for device_entry in device_list_ret['reply'] :
        #print (device_entry['device_id'])   
        template_dict ['devices'][device_entry['device_id']] = {
            'device_key' : device_entry['device_key'] ,
            'description' : device_entry['description'] ,
            'type' : device_entry['type'] 
            }
        template_dict['device_ids'].append (device_entry['device_id'])
    # print (template_dict)

    device_status = get_device_all ('heartbeat', "")
    #print ("ds:", device_status)
    #template_dict ['device_status'] = device_status ['reply']
    template_dict ['log_date_cutoff'] = device_status ['log_date_cutoff']
    for status_entry in device_status ['reply'] :
        device_id = status_entry ['device_id']
        #print ("id:", device_id)
        if device_id in template_dict['devices'] :
            template_dict['devices'][device_id]['log_data'] \
                = status_entry ['log_data']
    template_dict['error_codes'] = error_ids

    # print ("==>td:", template_dict)

    mylookup = TemplateLookup(directories=['.'])
    mytemplate = Template (filename='templates/home.txt',
                            module_directory='/tmp/mako_modules',
                            lookup=mylookup)
    return (mytemplate.render(**template_dict))

# end home_page_handler

#-------------------------------------------------------------------------------
# maintenence_page_handler
#-------------------------------------------------------------------------------
def maintenence_page_handler (request_dict) :

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
    'device_list_item_handler_t' : {
        'handler' : device_list_item_handler_t ,
        'content_type' : 'text/html'
        } ,
    #'type_status' : {
        #'handler' : type_status_handler ,
        #'content_type' : 'application/json'
        #} ,
    'device_status' : {
        'handler' : device_status_handler ,
        'content_type' : 'application/json'
        } , 
    'device_status_changes' : {
        'handler' : device_status_changes_handler ,
        'content_type' : 'application/json'
        } , 
    'device_status_t' : {
        'handler' : device_status_handler_t ,
        'content_type' : 'text/html'
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
    global db_connection

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
        reply = action_dict[action]['handler'] (request_dict)
        db_connection.close ()
        return (reply)
    except mariadb.Error as e:
        request_dict ['action'] = 'error'
        return (f"Error connecting to MariaDB Platform: {e}")

# end request_handler

#-------------------------------------------------------------------------------
# get_handler
#-------------------------------------------------------------------------------
def get_handler (parm_dict) :
    print ("get_handler: ", parm_dict)
    

# end get_handler

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
            request_dict ['action'] = 'home'        # show device status
        elif path_dict.path == '/kiosk' : 
            request_dict ['action'] = 'kiosk'       # kiosk type interface
        elif path_dict.path == '/maintenence' :
            request_dict ['action'] = 'maintenence' # update interface
        else :                                      # js/css/images etc.
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        get_data = request_handler (request_dict)
        self.send_reply (request_dict['action'], get_data)

#---- Inputs:
#----   json formatted reqest message
#---- Outputs:
#----   json formatted reply message
    def do_POST (self):
        try :
            length = int (self.headers ['Content-Length'])
            post_data = self.rfile.read (length).decode ('utf-8')
            # print (post_data)
            request_dict = json.loads (post_data)
            reply_text = request_handler (request_dict)
        except :
            reply_text = json.dumps \
                            (set_result_code (initialize_json_return () ,
                            -1 ,
                           "Invalid input message format"))
        self.send_reply (request_dict['action'], reply_text)

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

