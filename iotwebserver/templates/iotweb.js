//##############################################################################
// iotweb.js
//##############################################################################

//------------------------------------------------------------------------------
// display_device_status
//------------------------------------------------------------------------------
function display_device_status
    (device_id)
{
//alert ("display_device: " + device_id)
// clear_display_area ()
$(display_area).html ('') ;

if (! IOTWEB.devices[device_id])
    {
    return ;
    }

var request =
    {
    'action' : 'device_status_t' ,
    'device_id' : device_id
    } ;

$.post("",
        JSON.stringify (request) ,
        null ,
        "html")
    .done (function (data)
        {
        // alert("success: " + data) ;
        $(display_area).html (data) ;
        })
    .fail (function ()
        {
        console.log ("display_device_status: fail");
        }) ;

} // display_device_status

//------------------------------------------------------------------------------
// heartbeat_toggle
//------------------------------------------------------------------------------
function heartbeat_toggle ()
{
//console.log ("heartbeat_toggle") ;

if (IOTWEB.heartbeat_active)
    {
    $(heartbeat_toggle_indicator).html ("Off") ;
    $(heartbeat_toggle_indicator)
        .removeClass("heartbeat_on")
        .addClass("heartbeat_off") ;
    IOTWEB.heartbeat_active = false ;
    }
else
    {
    $(heartbeat_toggle_indicator).html ("On") ;
    $(heartbeat_toggle_indicator)
        .removeClass("heartbeat_off")
        .addClass("heartbeat_on") ;
    IOTWEB.heartbeat_active = true ;
    }

} // heartbeat_toggle //

//------------------------------------------------------------------------------
// heartbeat_probe
//------------------------------------------------------------------------------
function heartbeat_probe (data)
{
var date_stamp = new Date () ;
var date_diff ;                 // milliseconds
var minutes ;

$.each (IOTWEB.devices ,
        function (device_id, device_data)
        {
        dev_select = "#device_button_" + device_id ;
//console.log (JSON.stringify (device_data)) ;
//console.log (device_data.heartbeat_last_check_in) ;
        date_diff = date_stamp - device_data.heartbeat_last_check_in ;
        minutes = Math.round (((date_diff % 86400000) % 3600000) / 60000) ;
//console.log (minutes.toString()) ;
        $(dev_select)
            .removeClass ("dev_heartbeat_good"
                            + " dev_heartbeat_warning"
                            + " dev_heartbeat_fail") ;
        if (minutes < IOTWEB.heartbeat_warning_minutes)
            {
            $(dev_select).addClass ("dev_heartbeat_good")
            }
        else if (minutes < IOTWEB.heartbeat_fail_minutes)
            {
            $(dev_select).addClass ("dev_heartbeat_warning")
            }
        else
            {
            $(dev_select).addClass ("dev_heartbeat_fail")
            }
        }) ;

} // heartbeat_probe //

//------------------------------------------------------------------------------
// heartbeat_add_device
//------------------------------------------------------------------------------
function heartbeat_add_device (device_data)
{
//console.log ("heartbeat_add_device") ;
var device_id = device_data.device_id ;
var request ;

//---- Initialize device:
IOTWEB.devices[device_id] = {'log_data':{'heartbeat':{}}} ;

request =
    {
    'action' : 'device_list_item_handler_t' ,
    'device_id' : device_id
    } ;

$.post("",
        JSON.stringify (request) ,
        null ,
        "html")
    .done (function (data)
        {
        //console.log (data)
        $('#device_list_tbody').append (data)
        })
    .fail (function ()
        {
        console.log ("heartbeat_add_device: fail");
        }) ;

} // heartbeat_add_device //

//------------------------------------------------------------------------------
// heartbeat_update_device
//------------------------------------------------------------------------------
function heartbeat_update_device (device_data)
{
//console.log ("heartbeat_update_device") ;
var device_id = device_data.device_id ;

if (! IOTWEB.devices[device_id])
    {
    heartbeat_add_device (device_data)
    //return ;                    // Unknown device - skip
    }

$("#dev_activity_outer_" + device_id)   // Clear activity classes
    .removeClass ("activity_div_outer_prev activity_div_outer_off")
    .addClass ("activity_div_outer_on") ;

$.each (device_data.log_data.heartbeat ,
        function (key_id, key_data)
        {
        IOTWEB.devices[device_id]['log_data']['heartbeat'][key_id] = key_data ;
        }) ;

IOTWEB.devices[device_id]['heartbeat_last_check_in'] = new Date () ;

} // heartbeat_update_device //

//------------------------------------------------------------------------------
// heartbeat_update
//------------------------------------------------------------------------------
function heartbeat_update (data)
{
/*
console.log ("heartbeat_update: " + JSON.stringify (data)) ;
heartbeat_update: {"result":{"error_code":0},"reply":[{"device_id":"boinc001","last_log_date":"2021-04-13 19:33:40","log_data":{"heartbeat":{"cpu_percent":{"user":0,"nice":99.9,"system":0.1,"idle":0,"iowait":0,"irq":0,"softirq":0,"steal":0,"guest":0,"guest_nice":0,"load":
*/

$(".activity_div_outer_prev")                   // adjust activity settings
    .removeClass ("activity_div_outer_prev")
    .addClass ("activity_div_outer_off") ;
$(".activity_div_outer_on")
    .removeClass ("activity_div_outer_on")
    .addClass ("activity_div_outer_prev") ;

$.each (data.reply ,                            // Update reported devices
        function (idx, device_data)
        {
        heartbeat_update_device (device_data) ;
        }) ;

IOTWEB.log_date_cutoff = data.log_date_cutoff ; // for next update

heartbeat_probe () ;

} // heartbeat_update

//------------------------------------------------------------------------------
// heartbeat_check
//------------------------------------------------------------------------------
function heartbeat_check ()
{
//console.log ("heartbeat_check") ;

if (! IOTWEB.heartbeat_active)
    {
    return ;
    }

var request =
    {
    'action' : 'device_status_changes' ,
    'log_id' : 'heartbeat' ,
    //'log_date_cutoff' : IOTWEB.date_low       // for TEST
    'log_date_cutoff' : IOTWEB.log_date_cutoff
    } ;

$.post("",
        JSON.stringify (request) ,
        null ,
        "json")
    .done (heartbeat_update)
    .fail (function ()
        {
        console.log ("heartbeat_check: fail");
        }) ;

} // heartbeat_check

//------------------------------------------------------------------------------
// initialize - Called when page is first loaded
//------------------------------------------------------------------------------
function initialize ()
{
//alert ('initialize:' + JSON.stringify (IOTWEB.devices))
var date_stamp = new Date () ;

$.each (IOTWEB.devices ,
        function (device_id, device_data)
        {
        IOTWEB.devices[device_id]['heartbeat_last_check_in'] = date_stamp ;
//console.log (JSON.stringify (device_data)) ;
//console.log (device_data.heartbeat_last_update) ;
        }) ;

heartbeat_toggle () ;           // Heartbeat ON
setInterval (heartbeat_check, (IOTWEB.heartbeat_interval * 1000))

} // init //

$(document).ready (initialize)

