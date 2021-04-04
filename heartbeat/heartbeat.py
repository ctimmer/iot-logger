#! /usr/bin/python3
################################################################################
# heatbeat.py
################################################################################

import statsd
import time
import psutil
import multiprocessing
import socket
import os
import pyudev
import json

from loggerconfig import *

#PATHS = [('/', 'root'), ('/data', 'data')]
PATHS = [('/', 'root')]

my_hostname = ''
logger_ip = ''
logger_server_data = {}

server_address_port = 0
client_sender_socket = 0
client_listener_socket = 0

report_interval = 600           # Every 10 minutes
disk_accum_trigger = 21600      # Every 6 hours
disk_accum = 0
cpu_times_accum_trigger = 3600  # Every hour
cpu_times_accum = 0

#-------------------------------------------------------------------------------
# initialize_client_message
#-------------------------------------------------------------------------------
def initialize_client_message (action):

    client_message = {}
    client_message ['action'] = action
    client_message ['id'] = my_hostname
    client_message [action] = {}
    return (client_message)

# end initialize_client_message

#-------------------------------------------------------------------------------
# get_disk_info
#-------------------------------------------------------------------------------
def get_disk_info (heartbeat_data, force):
    global report_interval
    global disk_accum_trigger
    global disk_accum

    if not force:
        disk_accum += report_interval
        if disk_accum < disk_accum_trigger :
            return
        else:
            disk_accum = 0

    disks_dict = {}
    heartbeat_data ['disks'] = disks_dict
    for path, label in PATHS:
        disk_dict = {}
        disks_dict [label] = disk_dict
        disk_usage = psutil.disk_usage(path)
        st = os.statvfs(path)
        total_inode = st.f_files
        free_inode = st.f_ffree
        inode_percentage = int(100*(float(total_inode - free_inode) \
                            / total_inode))
        disk_dict['inode_percent'] = inode_percentage
        disk_dict['total'] = disk_usage.total
        disk_dict['used'] = disk_usage.used
        disk_dict['free'] = disk_usage.free
        disk_dict['percent'] = disk_usage.percent

# end get_disk_info

#-------------------------------------------------------------------------------
# get_memory_info
#-------------------------------------------------------------------------------
def get_memory_info (heartbeat_data):

    memory_dict = {}
    heartbeat_data ['memory'] = memory_dict
    swap = psutil.swap_memory()
    memory_dict['total'] = swap.total
    memory_dict['used'] = swap.used
    memory_dict['free'] = swap.free
    memory_dict['percent'] = swap.percent

    virtual_memory_dict = {}
    heartbeat_data ['virtual_memory'] = virtual_memory_dict
    virtual = psutil.virtual_memory ()
    virtual_memory_dict ['total'] = virtual.total
    virtual_memory_dict ['available'] = virtual.available
    virtual_memory_dict ['used'] = virtual.used
    virtual_memory_dict ['free'] = virtual.free
    virtual_memory_dict ['percent'] = virtual.percent
    virtual_memory_dict ['active'] = virtual.active
    virtual_memory_dict ['inactive'] = virtual.inactive
    virtual_memory_dict ['buffers'] = virtual.buffers
    virtual_memory_dict ['cached'] = virtual.cached

# end get_memory_info

#-------------------------------------------------------------------------------
# get_sensors_info
#-------------------------------------------------------------------------------
def get_sensors_info (heartbeat_data):

    sensors_dict = {}
    heartbeat_data ['sensors'] = sensors_dict
    sensor_data = psutil.sensors_temperatures()
    for sensor_id, sensor_entries in sensor_data.items():
        sensors_dict [sensor_id] = []
        for sensor_item in sensor_entries:
            entry = {}
            sensors_dict [sensor_id].append (entry)
            entry_label = ''
            if 'label' in sensor_item :
                entry_label = sensor.label
            elif 'name' in sensor_item :
                entry_label = sensor.name
            entry ['label'] = entry_label
            entry ['current'] = sensor_item.current
            entry ['high'] = sensor_item.high
            entry ['critical'] = sensor_item.critical

# end get_sensors_info

#-------------------------------------------------------------------------------
# get_cpu_times_info
#-------------------------------------------------------------------------------
def get_cpu_times_info (heartbeat_data, force):
    global report_interval
    global cpu_times_accum_trigger
    global cpu_times_accum

    if not force:
        cpu_times_accum += report_interval
        if cpu_times_accum < cpu_times_accum_trigger :
            return
        else:
            cpu_times_accum = 0

    cpu_times_dict = {}
    heartbeat_data ['cpu_times'] = cpu_times_dict
    cpu_t = psutil.cpu_times()
    cpu_times_dict['user'] = cpu_t.user
    cpu_times_dict['nice'] = cpu_t.nice
    cpu_times_dict['system'] = cpu_t.system
    cpu_times_dict['idle'] = cpu_t.idle
    cpu_times_dict['iowait'] = cpu_t.iowait
    cpu_times_dict['irq'] = cpu_t.irq
    cpu_times_dict['softirq'] = cpu_t.softirq
    cpu_times_dict['steal'] = cpu_t.steal
    cpu_times_dict['guest'] = cpu_t.guest
    cpu_times_dict['guest_nice'] = cpu_t.guest_nice

# end get_cpu_times_info

#-------------------------------------------------------------------------------
# get_cpu_percent_info
#-------------------------------------------------------------------------------
def get_cpu_percent_info (heartbeat_data, interval):

    cpu_percent_dict = {}
    heartbeat_data ['cpu_percent'] = cpu_percent_dict
    cpu_t_percent = psutil.cpu_times_percent(interval)
    cpu_percent_dict['user'] = cpu_t_percent.user
    cpu_percent_dict['nice'] = cpu_t_percent.nice
    cpu_percent_dict['system'] = cpu_t_percent.system
    cpu_percent_dict['idle'] = cpu_t_percent.idle
    cpu_percent_dict['iowait'] = cpu_t_percent.iowait
    cpu_percent_dict['irq'] = cpu_t_percent.irq
    cpu_percent_dict['softirq'] = cpu_t_percent.softirq
    cpu_percent_dict['steal'] = cpu_t_percent.steal
    cpu_percent_dict['guest'] = cpu_t_percent.guest
    cpu_percent_dict['guest_nice'] = cpu_t_percent.guest_nice
    cpu_percent_dict['load'] = psutil.cpu_percent(True, 1)

# end get_cpu_percent_info

#-------------------------------------------------------------------------------
# send_heartbeat
#-------------------------------------------------------------------------------
def send_heartbeat (address_port, interval, force):
    global client_sender_socket

    action = 'heartbeat'

    heartbeat_message = initialize_client_message (action)
    heartbeat_data = heartbeat_message [action]
    #heartbeat_message [action] = heartbeat_data
    get_cpu_percent_info (heartbeat_data, interval)
    get_cpu_times_info (heartbeat_data, force)
    get_sensors_info (heartbeat_data)
    get_disk_info (heartbeat_data, force)
    get_memory_info (heartbeat_data)
    #print (heartbeat_message)
    result_json = json.dumps (heartbeat_message)
    bytesToSend = str.encode (result_json)
    client_sender_socket.sendto (bytesToSend, address_port)

# end send_heartbeat

#-------------------------------------------------------------------------------
# heartbeat_loop
#-------------------------------------------------------------------------------
def heartbeat_loop ():
    global report_interval
    global server_adddress_port
    
    send_heartbeat (server_address_port, 2, True)   # Send quick heartbeat

    continue_running = True
    while continue_running :
        send_heartbeat (server_address_port,
                        report_interval ,
                        False)
    # end continue_running

# end heartbeat_loop

#-------------------------------------------------------------------------------
# send_ping
#-------------------------------------------------------------------------------
def send_ping ():
    global CLIENT_CONFIG
    global client_sender_socket
    global server_adddress_port

    action = 'ping'
    ping_message = initialize_client_message (action)
    ping_data = ping_message [action]
    ping_data ['greeting'] = 'Howdy!'
    result_json = json.dumps (ping_message)
    bytesToSend = str.encode (result_json)
    client_sender_socket.sendto (bytesToSend, server_address_port)

# end send_ping

#-------------------------------------------------------------------------------
# client_listener
#-------------------------------------------------------------------------------
def client_listener ():
    global CLIENT_CONFIG
    global client_listener_socket
    global logger_server_data

    buffer_size = CLIENT_CONFIG ['BUFFER_SIZE']
    while(True):
        bytesAddressPair = client_listener_socket.recvfrom (buffer_size)
        message = bytesAddressPair[0]
        address_port = bytesAddressPair[1]       # need to SET
        request_json = message.decode(encoding="ascii", errors="ignore")
        request_dict = json.loads (request_json)
        if request_dict['action'] == "heartbeat":
            # Sending a reply to client
            if 'reply_port' in request_dict :
                address_port = (address [0], request_dict['reply_port'])
            print (address)
            send_heartbeat (address_port, 2, True)
        elif request_dict['action'] == "pong" :
            if 'server' in request_dict :
                logger_server_data = request_dict ['server']
            #print (logger_server_data)
        else :
            print (request_dict)

# end client_listener

#-------------------------------------------------------------------------------
# initialize
#-------------------------------------------------------------------------------
def initialize () :
    global CLIENT_CONFIG
    global client_sender_socket
    global client_listener_socket
    global SERVER_CONFIG
    global server_address_port
    global my_hostname
    global logger_ip

    client_listener_socket = socket.socket(family=socket.AF_INET,
                                    type=socket.SOCK_DGRAM)
    # Bind to address and ip
    client_listener_socket.bind(("", CLIENT_CONFIG ['LISTENER_PORT']))
    print("UDP client listener ready")

    client_sender_socket = socket.socket (family=socket.AF_INET,
                                            type=socket.SOCK_DGRAM)

    my_hostname = socket.gethostname()
    logger_ip = socket.gethostbyname (CLIENT_CONFIG ['LOGGER_HOST'])
    server_address_port = (logger_ip, SERVER_CONFIG ['LISTENER_PORT'])

# end initialize

#-------------------------------------------------------------------------------
# main
#-------------------------------------------------------------------------------

initialize ()

try:
    multiprocessing.Process(target=client_listener).start()
except:
    print ("HEARTBEAT shutting down")

heartbeat_loop ()

