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
        alert( "error" );
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
    $(heartbeat_toggle_button).html ("[HeartBeat: Off]") ;
    $(heartbeat_toggle_button)
        .removeClass("heartbeat_on")
        .addClass("heartbeat_off") ;
    IOTWEB.heartbeat_active = false ;
    }
else
    {
    $(heartbeat_toggle_button).html ("[HeartBeat: On]") ;
    $(heartbeat_toggle_button)
        .removeClass("heartbeat_off")
        .addClass("heartbeat_on") ;
    IOTWEB.heartbeat_active = true ;
    }

} // heartbeat_toggle

//------------------------------------------------------------------------------
// heartbeat_update
//------------------------------------------------------------------------------
function heartbeat_update (data)
{
console.log ("heartbeat_update: " + JSON.stringify (data)) ;

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
    'log_date_cutoff' : IOTWEB.log_date_cutoff
    } ;

$.post("",
        JSON.stringify (request) ,
        null ,
        "json")
    .done (heartbeat_update)
    .fail (function ()
        {
        alert( "error" );
        }) ;

} // heartbeat_check

//------------------------------------------------------------------------------
// initialize - Called when page is first loaded
//------------------------------------------------------------------------------
function initialize ()
{
//alert ('initialize:' + JSON.stringify (IOTWEB.devices))

heartbeat_toggle () ;           // Heartbeat ON
setInterval (heartbeat_check, 10000)

} // init //

$(document).ready (initialize)

