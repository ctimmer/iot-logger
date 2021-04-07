#
# mariadb client/server parameters
#

#---- db_config is only needed by the servers
DB_CONFIG = {
    'HOSTNAME' : 'localhost' ,
    'PORT' : 3306 ,         # Raspberry PI or 3307 Synology
    'USERNAME' : 'testuser' ,
    'PASSWORD' : 'testpassword' ,
    'DATABASE' : 'iotlogger' ,
    'POOLSIZE' : 12
    }

SERVER_CONFIG = {
    'LISTENER_PORT' : 5010 ,
    'LOCAL_IP'  : '' ,
    'BUFFER_SIZE' : 16384
    }

CLIENT_CONFIG = {
    'LOGGER_HOST' : 'localhost' ,
    'LISTENER_PORT' : 5011 ,
    'BUFFER_SIZE' : 16384
    }


