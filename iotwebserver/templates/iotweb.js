//##############################################################################
// iotweb.js
//##############################################################################

//------------------------------------------------------------------------------
// switch_display_tab
//------------------------------------------------------------------------------
function switch_display_tab
    (tab_id)
{

$(".display_area_tab_on")
    .removeClass ("display_area_tab_on")
    .addClass ("display_area_tab_off") ;
$("#display_area_tab_" + tab_id)
    .removeClass ("display_area_tab_off")
    .addClass ("display_area_tab_on") ;

$(".display_area_div").css ("display" ,"none")
$("#display_area_" + tab_id).css ("display", "block")

} // switch_display_tab //

//------------------------------------------------------------------------------
// display_device_status
//------------------------------------------------------------------------------
function display_device_status
    (device_id)
{
//console.log ("display_device: " + device_id)

$(display_area_status).html ('') ;
switch_display_tab ('status') ;

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
        $(display_area_status).html (data) ;
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
//IOTWEB.devices[device_id]['log_data']['heartbeat'] = {} ;
    //= device_data.log_data.heartbeat ;

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
// build_chart_plot_data
//------------------------------------------------------------------------------
function build_chart_plot_data
    (entry_id ,
    data_id ,
    parms)
{
//console.log ('build_chart_plot_data') ;
//console.log (entry_id) ;
//console.log (data_id) ;
//console.log (JSON.stringify (parms)) ;

var plot_data = [] ;

$.each (parms ,
        function (idx, log_data)
        {
        date_key = new Date (log_data.log_date).getTime () ;    // to be fixed
        if (log_data[entry_id])
            {
            if (log_data[entry_id][data_id])
                {
                plot_data.push ([date_key, log_data[entry_id][data_id]]) ;
                }
            }
        }) ;

return (plot_data) ;

} // build_chart_plot_data //

//------------------------------------------------------------------------------
// byte_formatter
//------------------------------------------------------------------------------
function byte_formatter
    (val, axis)
{
//console.log ("BF:" + val.toString() + " " + JSON.stringify(axis)) ;
//console.log ("BF:" + val.toString()) ;

var multiplier = 10 ;
var ret_val = val / 1000000000 ;
var ret_val = Math.round(ret_val * multiplier) / multiplier;

return (ret_val.toString()) ;

} // byte_formatter //

//------------------------------------------------------------------------------
// build_history_chart
//------------------------------------------------------------------------------
function build_history_chart
    (parms)
{
//console.log ("build_history_chart") ;
var plot_idx = parms.plot_idx ;
var plot_heading = $('[name="chart_heading"]')[plot_idx] ;
var select_fun ;

var plot_data = build_chart_plot_data
                    (parms.entry_id ,
                    parms.data_id ,
                    parms.data) ;

IOTWEB.plot[plot_idx].data =
    [
    {
    //"label" : parms.data_id ,
    "color" : "black" ,
    "data" : plot_data ,
    "lines" :
        {
        show : true ,
        lineWidth: 2,
        shadowSize: 0
        } ,
    points :
        {
        show: false
        }
    }
    ] ;

IOTWEB.plot[plot_idx].options =
    {
    "grid" :
        {  
        hoverable: true ,
        backgroundColor: { colors: ["#96CBFF", "#75BAFF"] }
        },
    "xaxis" :
        {
        mode: "time",
        //tickSize: [5, "day"], 
        //tickLength: 0,
        axisLabel: "Date/Time",
        axisLabelUseCanvas: true,
        axisLabelFontSizePixels: 10,
        axisLabelFontFamily: 'Verdana, Arial',
        axisLabelPadding: 5,
        color: "black"
        } ,
    "yaxis" :
        {
        position: "left",
        tickSize: [500000000], 
        tickFormatter: byte_formatter ,
        min: 0,
        max: 8000000000,
        color: "black",
        axisLabel: "GigaBytes",
        axisLabelUseCanvas: true,
        axisLabelFontSizePixels: 10,
        axisLabelFontFamily: 'Verdana, Arial',
        axisLabelPadding: 2       
        } ,
    "selection" :
        {
        mode: "x"
        }
    }

IOTWEB.plot[plot_idx].place_holder
    = $('[name="chart_place_holder"]')[plot_idx] ;
$(IOTWEB.plot[plot_idx].place_holder).css ("display", "block") ;

if (parms.chart_heading)
    {
    $(plot_heading).css ("display", "block")
    $(plot_heading).text (parms.chart_heading) ;
    IOTWEB.plot[plot_idx].data.label = "" ;
    }
else
    {
    IOTWEB.plot[plot_idx].data.label = parms.data_id ;
    }

if (parms.min)
    {
    IOTWEB.plot[plot_idx].options.yaxis.min = parms.min ;
    }
if (parms.max)
    {
    IOTWEB.plot[plot_idx].options.yaxis.max = parms.max ;
    }

IOTWEB.plot[plot_idx].plot
    = $.plot($(IOTWEB.plot[plot_idx].place_holder) ,
                IOTWEB.plot[plot_idx].data ,
                IOTWEB.plot[plot_idx].options) ;

select_fun = function (event, ranges)
            {        
            var idx = plot_idx ;
            // clamp the zooming to prevent eternal zoom
            if (ranges.xaxis.to - ranges.xaxis.from < 0.00001)
                {
				ranges.xaxis.to = ranges.xaxis.from + 0.00001;
			    }
            if (ranges.yaxis.to - ranges.yaxis.from < 0.00001)
                {
                ranges.yaxis.to = ranges.yaxis.from + 0.00001;
                }
//IOTWEB.plot[idx].plot =
            $.plot($(IOTWEB.plot[idx].place_holder) ,
                                IOTWEB.plot[idx].data ,
                                $.extend (true,
                                            {},
                                            IOTWEB.plot[idx].options ,
                                            {
                                            xaxis:
                                                {
                                                min: ranges.xaxis.from ,
                                                max: ranges.xaxis.to 
                                                }
                                            })
                            ) ;
            };
$(IOTWEB.plot[plot_idx].place_holder)
    .bind("plotselected",
            select_fun) ;

// FIX: doesn't redraw x axis ticks
$(plot_heading).click(function ()
        {
        var idx = plot_idx ;
        IOTWEB.plot[idx].plot
            = $.plot($(IOTWEB.plot[idx].place_holder) ,
                        IOTWEB.plot[idx].data ,
                        IOTWEB.plot[idx].options) ;
		});

} // build_history_chart

//------------------------------------------------------------------------------
// log_history_chart
//------------------------------------------------------------------------------
function log_history_chart
    (parms)
{
//console.log ('log_history_chart') ;
//console.log (parms.device_id) ;
//console.log (parms.log_id) ;
//console.log (JSON.stringify (parms.data)) ;

var entry_id = "virtual_memory" ;
var chart_parameters =
    {
    "device_id" : parms.device_id ,
    "log_id" : parms.log_id ,
    "entry_id" : entry_id ,
    "data" : parms.data.reply ,
    "min" : 0 ,
    "max" : 8000000000
    } ;
var plot_idx = 0 ;

if (chart_parameters.data.length > 0)
    {
    if (chart_parameters.data[0][entry_id].total)
        {
        var new_max = chart_parameters.data[0][entry_id].total ;
        $.each (
            [
            1000000000 ,
            2000000000 ,
            4000000000 ,
            8000000000 ,
            16000000000 ,
            32000000000
            ] ,
            function (idx, bytes)
            {
            if (new_max < bytes)
                {
                new_max = bytes ;
                return false ;
                }
            return true ;
            }) ;
        //if (new_max < 1000000000)
            //{
            //new_max = 1000000000 ;
            //}
        //else if (new_max < 2000000000)
            //{
            //new_max = 2000000000 ;
            //}
        chart_parameters.max = new_max ;
        }
    }

$(".chart_place_holder .chart_heading").css ("display" ,"none")
switch_display_tab ('chart') ;
chart_parameters.entry_id = entry_id ;

chart_parameters.plot_idx = 0 ;
chart_parameters.chart_id = "chart_1" ;
chart_parameters.chart_heading = "Available Memory" ;
chart_parameters.data_id = "available" ;
build_history_chart (chart_parameters) ;

chart_parameters.plot_idx++ ;
chart_parameters.data_id = "used" ;
chart_parameters.chart_heading = "Used Memory" ;
chart_parameters.chart_id = "chart_2" ;
build_history_chart (chart_parameters) ;

chart_parameters.plot_idx++ ;
chart_parameters.data_id = "free" ;
chart_parameters.chart_heading = "Free Memory" ;
chart_parameters.chart_id = "chart_3" ;
build_history_chart (chart_parameters) ;

} // log_history_chart //

//------------------------------------------------------------------------------
// log_history
//------------------------------------------------------------------------------
function log_history
    (device_id,
    log_id ,
    entry_list)
{
//console.log ("log_history") ;
//console.log (device_id) ;
//console.log (log_id) ;
//console.log (entry_list) ;

var request =
    {
    'action' : 'log_history' ,
    'device_id' : device_id ,
    'log_id' : log_id
    } ;
var chart_parameters =
    {
    'device_id' : device_id ,
    'log_id' : log_id
    } ;

if (entry_list)
    {
    request.entry_list = entry_list ;
    chart_parameters.entry_list = entry_list ;
    }

$.post("",
        JSON.stringify (request) ,
        null ,
        "json")
    .done (function (data)
        {
        var parameters = chart_parameters ;
        parameters.data = data ;
        log_history_chart (parameters) ;
        })
    .fail (function ()
        {
        console.log ("log_history: fail") ;
        }) ;

} // log_history

//------------------------------------------------------------------------------
// initialize - Called when page is first loaded
//------------------------------------------------------------------------------
function initialize ()
{
//alert ('initialize:') ;
//alert ('initialize:' + JSON.stringify (IOTWEB.devices)) ;
var date_stamp = new Date () ;
var idx ;

$.each (IOTWEB.devices ,
        function (device_id, device_data)
        {
        IOTWEB.devices[device_id]['heartbeat_last_check_in'] = date_stamp ;
//console.log (JSON.stringify (device_data)) ;
//console.log (device_data.heartbeat_last_update) ;
        }) ;

heartbeat_toggle () ;           // Heartbeat ON
setInterval (heartbeat_check, (IOTWEB.heartbeat_interval * 1000))

for (idx = 0 ; idx < 10 ; idx++)
    {
    IOTWEB.plot[idx] =
        {
        place_holder : null ,
        data : {} ,
        options : {} ,
        plot : null
        }
    }

} // initialize //

$(document).ready (initialize)

