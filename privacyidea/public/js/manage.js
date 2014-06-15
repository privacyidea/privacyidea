window.onerror = error_handling;
LOGIN_CODE = 576;

encodings = [
    "ascii","big5","big5hkscs",
    "cp037","cp424","cp437",
    "cp500","cp720","cp737",
    "cp775","cp850","cp852",
    "cp855","cp856","cp857",
    "cp858","cp860","cp862",
    "cp863","cp864","cp865",
    "cp866","cp869","cp874",
    "cp875","cp932","cp949",
    "cp950","cp1006","cp1026",
    "cp1140","cp1250","cp1251",
    "cp1252","cp1253","cp1254",
    "cp1255","cp1256","cp1257",
    "cp1258","euc_jp","euc_jis_2004",
    "euc_jisx0213","euc_kr",
    "gb2312","gbk","gb18030",
    "hz","iso2022_jp",
    "iso2022_jp_1","iso_2022_jp_2",
    "iso2022_jp_2004",
    "iso2022_jp_3",
    "iso2022_jp_ext",
    "iso2022_kr",
    "latin_1",
    "iso8859_1",
    "iso8859_2",
    "iso8859_3",
    "iso8859_4",
    "iso8859_5",
    "iso8859_6",
    "iso8859_7",
    "iso8859_8",
    "iso8859_9",
    "iso8859_10",
    "iso8859_13",
    "iso8859_14",
    "iso8859_15",
    "iso8859_16",
    "johab",
    "koi8_r","koi8_u",
    "mac_cyrillic",
    "mac_greek",
    "mac_iceland",
    "mac_latin2",
    "mac_roman",
    "mac_turkish",
    "ptcp154",
    "shift_jis",
    "shift_jis_2004",
    "shift_jisx0213",
    "utf_32",
    "utf_32_be",
    "utf_32_le",
    "utf_16",
    "utf_16_be",
    "utf_16_le",
    "utf_7",
    "utf_8",
    "utf_8_sig"
];

function error_handling(message, file, line){
    Fehler = "We are sorry. An internal error occurred:\n" + message + "\nin file:" + file + "\nin line:" + line +
    "\nTo go on, reload this web page.";
    alert(Fehler);
    return true;
}

// We need this dialogs globally, so that we do not create more than one instance!

var $dialog_ldap_resolver;
var $dialog_file_resolver;
var $dialog_sql_resolver;
var $dialog_scim_resolver;
var $dialog_edit_realms;
var $dialog_ask_new_resolvertype;
var $dialog_resolvers;
var $dialog_realms;
var $dialog_resolver_ask_delete;
var $dialog_realm_ask_delete;
var $dialog_show_enroll_url;
var $dialog_token_info;
var $dialog_setpin_token;
var $dialog_view_temporary_token;
var $dialog_import_policy;
var $dialog_tokeninfo_set;

var $tokentypes;

var $tokenConfigCallbacks = {};
var $tokenConfigInbacks = {};

// FIXME: global variable should be worked out
var g = {};
    g.display_genkey = false;
    g.running_requests = 0;
    g.resolver_to_edit = "";
    g.realm_to_edit = "";
    g.resolvers_in_realm_to_edit = "";
    g.realms_of_token = new Array();

ERROR = "error";



function len(obj) {
  var len = obj.length ? --obj.length : -1;
    for (var k in obj)
      len++;
  return len;
}


function log(text){
    var time = new Date();
    var hours = time.getHours();
    var minutes = time.getMinutes();
    minutes = ((minutes < 10) ? "0" : "") + minutes;
    var seconds = time.getSeconds();
    seconds = ((seconds < 10) ? "0" : "") + seconds;

    var day = time.getDate();
    day = ((day < 10) ? "0" : "") + day;
    var month = time.getMonth();
    month = ((month < 10) ? "0" : "") + month;
    var year = time.getFullYear();

    var datum = year + '/' + month + '/' + day + ' ' + hours + ':' + minutes + ':' + seconds;

    $('#logText').html(datum + ": " + text + '<br>' + $('#logText').html());
}


function error_flexi(data){
    // we might do some mods here...
    alert_info_text("text_error_fetching_list", "", ERROR);
}

function pre_flexi(data){
    // we might do some mods here...
    if (data.result) {
        if (data.result.status == false) {
            alert_info_text(data.result.error.message);
        }
    }
    else {
        return data;
    }
}

function load_flexi(){
    var new_realm = $('#realm').val();
    $('#user_table').flexOptions({
        params: [{
            name: 'realm',
            value: new_realm
        }]
    });
    return true;
}


function alert_info_text(s, param1, display_type) {
	/*
	 * If the parameter is the ID of an element, we pass the text from this very element
	 */
	str = s;
	try {
		if (param1) {

			$('#'+s+' .text_param1').html(param1);
		}
		if ( $('#'+s).length > 0 ) { // Element exists!
			s=$('#'+s).html();
		} else {
			s = str;
		}

    }
    catch (e) {
        s=str;
    }
    if (display_type == ERROR) {
    	$('#info_box').addClass("error_box");
    	$('#info_box').removeClass("info_box");
    } else {
    	$('#info_box').addClass("info_box");
    	$('#info_box').removeClass("error_box");
    }
	$('#info_text').html(s);
	$('#info_box').show();
}

function alert_box(title, s, param1) {
	/*
	 * If the parameter is the ID of an element, we pass the text of this very element
	 */
	str = s;
	try {
		if (param1) {
			$('#'+s+' .text_param1').html(param1);
		}
		if ( $('#'+s).length > 0 ) { // Element exists!
			s=$('#'+s).html();
		} else {
			s = str;
		}

    }
    catch (e) {
        s=str;
    }
    title_t = title;
    try {
        title_t=$('#'+title).text();
    } catch(e) {
        title_t = title;
    }

     $('#alert_box').dialog("option", "title", title_t);
     $('#alert_box_text').html(s);
     $('#alert_box').dialog("open");

}

// ####################################################
//
//  functions for seletected tokens and selected users
//

function get_selected_tokens(){
    var selectedTokenItems = new Array();
    var tt = $("#token_table");
    $('.trSelected', tt).each(function(){
        var id = $(this).attr('id');
        var serial = id.replace(/row/, "");
        //var serial = $(this).attr('cells')[0].textContent;
        selectedTokenItems.push(serial);
    });
    return selectedTokenItems;
}

function get_selected_users(){
	/*
	 * This function returns the list of selected users.
	 * Each list element is an object with
	 *  - login
	 *  - resolver
	 */
    var selectedUserItems = new Array();
    var tt = $("#user_table");
    var selected = $('.trSelected', tt);
    selected.each(function(){
    	var user = new Object();
    	user = { resolver:"" , login:"" };
    	column = $('td', $(this));
    	column.each(function(){
    		var attr = $(this).attr("abbr");
    		if (attr == "useridresolver") {
    			var resolver = $('div', $(this)).html().split('.');
    			user.resolver = resolver[resolver.length-1];

    		}
    	});

        var id = $(this).attr('id');
        user.login = id.replace(/row/, "");
        selectedUserItems.push(user);
    });
    return selectedUserItems;
}

function get_selected_policy(){
    var selectedPolicy = new Array();
    var pt = $('#policy_table');
    $('.trSelected', pt).each(function(){
        var id = $(this).attr('id');
        var policy = id.replace(/row/, "");
        selectedPolicy.push(policy);
	});
    return selectedPolicy;
}

function get_scope_actions(actionObjects) {
	/*
	 * This function returns the allowed actions from the action Objects
	 * as an array of strings/actionnames
	 */
	var actions = Array();
	for (var k in actionObjects) {
		action = k;
		if ("int"==actionObjects[k].type) {
			action = k+"=<int>";
		} else
		if ("str"==actionObjects[k].type) {
			action = k+"=<string>";
		};
		actions.push(action);
	}
    return actions.sort();
}

function get_scope_action_objects(scope) {
	/*
	 * This function returns the allowed actions within a scope
	 * as an array og action objects with "desc" and "type"
	 *   
	 */
	var actions = Array();
	var resp = clientUrlFetchSync("/system/getPolicyDef",{"scope" : scope, "session" : getsession()}, true, "Error fetching policy definitions:");
    obj = jQuery.parseJSON(resp);
    if (obj.result.status) {
		actions = obj.result.value;
    }
    return actions;
}

function get_selected_mobile(){
    var selectedMobileItems = new Array();
    var tt = $("#user_table");

    var yourAbbr = "mobile";
    var column = tt.parent(".bDiv").siblings(".hDiv").find("table tr th").index($("th[abbr='" + yourAbbr + "']",
    			".flexigrid:has(#user_table)"));

    $('.trSelected', tt).each(function(){
        //var value = tt.children("td").eq(column).text();
        var value = $('.trSelected td:eq(5)', tt).text();
        selectedMobileItems.push(value);
    });
    return selectedMobileItems;
}

function get_selected_email() {
	var selectedEmailItems = new Array();
	var tt = $('#user_table');
	var yourAbbr = "email";
	var column = tt.parent(".bDiv").siblings(".hDiv").find("table tr th").index($("th[abbr='"+yourAbbr+"']",
				 ".flexigrid:has(#user_table)"));
	$('.trSelected', tt).each(function(){
        //var value = tt.children("td").eq(column).text();
        var value = $('.trSelected td:eq(4)', tt).text();
        selectedEmailItems.push(value);
    });
    return selectedEmailItems;
}

function get_selected(){
    var selectedUserItems = get_selected_users();
    var selectedTokenItems = get_selected_tokens();
    document.getElementById('selected_tokens').innerHTML = selectedTokenItems.join(", ");
    // we can only select a single user
    if ( selectedUserItems.length > 0 )
    	document.getElementById('selected_users').innerHTML = selectedUserItems[0].login;
    else
    	document.getElementById('selected_users').innerHTML = "";

    if (selectedTokenItems.length > 0) {
        if (selectedUserItems.length == 1) {
            $("#button_assign").button("enable");
        }
        else {
            $("#button_assign").button("disable");
        }
        $("#button_unassign").button("enable");
        $("#button_tokenrealm").button("enable");
        $("#button_getmuli").button("enable");
        $("#button_enable").button("enable");
        $("#button_disable").button("enable");
        $("#button_delete").button("enable");
        $("#button_setpin").button("enable");
        $("#button_resetcounter").button("enable");
        if (selectedTokenItems.length == 1) {
            $("#button_resync").button("enable");
            $('#button_losttoken').button("enable");
            $('#button_getmulti').button("enable");
            $("#button_tokeninfo").button("enable");
          }
        else {
            $("#button_resync").button("disable");
            $("#button_losttoken").button("disable");
            $('#button_getmulti').button("disable");
            $("#button_tokeninfo").button("disable");
        }
    }
    else {
        disable_all_buttons();
    }
    $("#button_enroll").button("enable");

    // The policies (we can select only one)
    if ($('#tabs').tabs('option', 'selected') == 2) {
        policy = get_selected_policy().join(',');
        if (policy) {
            $.post('/system/getPolicy', {'name' : policy,
            							'display_inactive': '1',
            							'session':getsession()} ,
             function(data, textStatus, XMLHttpRequest){
                if (data.result.status == true) {
                    policies = policy.split(',');
                    pol = policies[0];
                    var pol_active = data.result.value[pol].active;
                    if (pol_active == undefined) {
                    	pol_active = "True";
                    }
                    $('#policy_active').attr("checked", pol_active=="True" );
                    $('#policy_name').val(pol);
                    $('#policy_action').val(data.result.value[pol].action);
                    $('#policy_scope').val(data.result.value[pol].scope);
                    $('#policy_scope_combo').val(data.result.value[pol].scope);
                    $('#policy_realm').val(data.result.value[pol].realm);
                    $('#policy_user').val(data.result.value[pol].user);
                    $('#policy_time').val(data.result.value[pol].time);
                    $('#policy_client').val(data.result.value[pol].client || "");
                    renew_policy_actions();
                }
            });
        }
    }

};

function disable_all_buttons(){
    $('#button_assign').button("disable");
    $('#button_unassign').button("disable");
    $('#button_tokenrealm').button("disable");
    $('#button_getmulti').button("disable");
    $('#button_enable').button("disable");
    $('#button_disable').button("disable");
    $('#button_setpin').button("disable");
    $('#button_delete').button("disable");
    $('#button_resetcounter').button("disable");
    $("#button_resync").button("disable");
    $("#button_tokeninfo").button("disable");
    $("#button_losttoken").button("disable");
}

function init_$tokentypes(){
/*
 * initalize the list of all avaliable token types
 * - required to show and hide the dynamic enrollment section
 */
    var options = $('#tokentype > option');
    if ($tokentypes == undefined) {$tokentypes = {};};
	options.each(
	  function(i){
		var key = $(this).val();
		var title = $(this).text();
		$tokentypes[key] = title;
	  }
	);
}



function get_server_config() {
/*
 * retrieve the privacyidea server config
 *
 * return the config as dict
 * or raise an exception
 */

    var $systemConfig = {};
    var resp = clientUrlFetchSync('/system/getConfig', {"session" : getsession()});
    try {
        var data = jQuery.parseJSON(resp);
        if (data.result.status == false) {
            //console_log("Failed to access privacyidea system config: " + data.result.error.message);
            throw("" + data.result.error.message);
        }else {
            $systemConfig = data.result.value;
            //console_log("Access privacyidea system config: " + data.result.value);
        }
    }
    catch (e) {
        //console_log("Failed to access privacyidea system config: " + e);
        throw(e);
    }
	return $systemConfig;
}

function get_resolver_list() {
	/*
	 * retrieve the list of resolvers known to the system
	 */
	var $resolver_list = Array();
	var resp = clientUrlFetchSync('/system/get_resolver_list', {"session" : getsession()});
	try {
		var data = jQuery.parseJSON(resp);
        if (data.result.status == false) {
            throw("" + data.result.error.message);
        }else {
            $resolver_list = data.result.value.resolvertypes;
        }
	} catch (e) {
		throw(e);
	}
	return $resolver_list;
}

function load_token_config() {


	var selectTag = $('#tab_token_settings');
	selectTag.find('div').each(
		function() {
		  var attr =$(this).attr('id');
		  var n= attr.split("_");
		  var tt = n[0];
		  $tokenConfigCallbacks[tt] = tt+'_get_config_params';
		  $tokenConfigInbacks[tt]   = tt+'_get_config_val';
		}
	);

	// might raise an error, which must be catched by the caller
	$systemConfig = get_server_config();

    for (tt in $tokenConfigInbacks) {
    	try{
    		var functionString = ''+$tokenConfigInbacks[tt]+'';
			var funct = window[functionString];
			var exi = typeof funct;
			var l_params = {};
			if (exi == 'function') {
				l_params = window[functionString]();
			}

	    	for (var key in l_params) {
	    		if (key in $systemConfig) {
	    			try{
	    				//alert('Val = >' + $systemConfig[key] + '<');
	    				//console_log("  " + key + ": " + l_params[key] + '  ' +  $systemConfig[key] + 'not found!');
	    				$('#'+l_params[key]).val( $systemConfig[key] );

	    			} catch(err) {
	    				//console_log('error ' + err + "  " + key + ": " + l_params[key] + '  ' + 'not found!')
	    			}
	    		}
			}
		}
		catch(err) {
			//console_log('callbacack for ' + tt + ' not found!')
		}
	}
	return;
}
/*
callback save_token_config()
*/
function save_token_config(){
    show_waiting();
    /* for every token call the getParamCallback */
    var params = {'session': getsession()};
    for (tt in $tokenConfigCallbacks) {
    	try{
    		var functionString = ''+$tokenConfigCallbacks[tt];
			var funct = window[functionString];
			var exi = typeof funct;
			var l_params = {};
			if (exi == 'function') {
				l_params = window[functionString]();
			}
	    	for (var key in l_params) {
  				params[key] = l_params[key];
			}
		}
		catch(err) {
			//console_log('callbacack for ' + tt + ' not found!')
		}


    }
    //console_log(params)
    $.post('/system/setConfig', params,
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_token_save_error", "", ERROR);
        }
    });
}


/*
 * Retrieve session cookie if it does not exist
 */


function getsession(){
	var session = "";
	if (document.cookie) {
		session = getcookie("privacyidea_session");
		if (session == "") {
			alert("there is no privacyidea_session cookie");
		}
	}
	return session;
}


function reset_waiting() {
	g.running_requests = 0;
	hide_waiting();
}

// ####################################################
//
//  URL fetching
// The myURL needs to end with ? if it has no parameters!


function clientUrlFetch(myUrl, params, callback, parameter){
	/*
	 * clientUrlFetch - to submit a asyncronous http request
	 *
	 * @remark: introduced the params (:dict:) so we could switch to
	 * 			a POST request, which will allow more and secure data
	 */
    var session = getsession();
	//myUrl = myUrl + "&session=" + session;
	params['session'] = session;

	show_waiting();

	g.running_requests = g.running_requests +1 ;

    $.ajax({
        url: myUrl,
        data : params,
        async: true,
        type: 'POST',
        complete: function(xhdr, textStatus) {
        	g.running_requests = g.running_requests -1;
        	if (g.running_requests <= 0) {
        		hide_waiting();
        		g.running_requests = 0;
        	}
    		if (callback != null) {
    			callback(xhdr, textStatus, parameter);
    		}
        }
      });
}

function clientUrlFetchSync(myUrl,params){
	/*
	 * clientUrlFetchSync - to submit a syncronous  http request
	 *
	 * @remark: introduced the params (:dict:) so we could switch to
	 * 			a POST request, which will allow more and secure data
	 */

    var session = getsession();
	//myUrl 	= myUrl + "&session=" + session;
	params['session'] = session;

	show_waiting();

    var resp = $.ajax({
        url: myUrl,
        data : params,
        async: false,
        type: 'POST',
        }
    ).responseText;
    hide_waiting();
    return resp;
}


// ####################################################
// get overall number of tokens
function get_tokennum(){
    // sorry: we need to do this synchronously
    var resp = clientUrlFetchSync('/admin/show', {"session" : getsession(),
    												'page':1,'pagesize':1,
                                                  'filter' : '/:token is active:/'});
    if (resp == undefined) {
    	alert('Server is not responding');
    	return 0;
    }
    var obj = jQuery.parseJSON(resp);
    return obj.result.value.resultset.tokens;
}





function check_serial(serial){
	var resp = clientUrlFetchSync('/admin/check_serial',{'serial':serial, "session" : getsession()});
	var obj = jQuery.parseJSON(resp);
   	return obj.result.value.new_serial;
}

// ####################################################
//
//  Token functions
//

function reset_buttons() {
	$("#token_table").flexReload();
    $('#selected_tokens').html('');
    disable_all_buttons();
}

function token_function_callback(xhdr, textStatus) {
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	alert_info_text(obj.result.error.message);
    }
	reset_buttons();
}

function assign_callback(xhdr, textStatus, serial) {
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	alert_info_text(obj.result.error.message, "", ERROR);
    } else
    	view_setpin_after_assigning([serial]);
	reset_buttons();
}


function token_disable(){
    tokentab = 0;
    tokens = get_selected_tokens();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/disable", {"serial": serial, "session" : getsession()}, token_function_callback);
    }
}


function token_enable(){
    tokentab = 0;
    tokens = get_selected_tokens();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/enable", {"serial": serial, "session" : getsession()}, token_function_callback);
    }
}


function token_delete(){
    tokentab = 0;
    tokens = get_selected_tokens();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/remove", {"serial": serial, "session" : getsession()}, token_function_callback);
    }
}

function token_assign(){
    tokentab = 0;
    tokens = get_selected_tokens();
    user = get_selected_users();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/assign", {"serial": serial,
        								"session" : getsession(),
        								"user": user[0].login,
        								'resConf':user[0].resolver,
        								'realm': $('#realm').val()}, assign_callback, serial);
    }
}

function token_unassign(){
    tokentab = 0;
    tokens = get_selected_tokens();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/unassign", {"serial": serial, "session" : getsession()}, token_function_callback);
    }
}


function token_reset(){
    tokentab = 0;
    tokens = get_selected_tokens();
    count = tokens.length;
    for (i = 0; i < count; i++) {
        serial = tokens[i];
        clientUrlFetch("/admin/reset", {"serial" : serial, "session" : getsession()}, token_function_callback);
    }
}

function token_resync_callback(xhdr, textStatus) {
	var resp = xhdr.responseText;
	var obj = jQuery.parseJSON(resp);
    if (obj.result.status) {
            if (obj.result.value)
                alert_info_text("text_resync_success");
            else
                alert_info_text("text_resync_fail", "", ERROR);
        }
    reset_buttons();
}

function token_resync(){
    var tokentab = 0;
    var tokens = get_selected_tokens();
    var count = tokens.length;
    for (i = 0; i < count; i++) {
        var serial = tokens[i];
        clientUrlFetch("/admin/resync", {"serial" : serial, 
        								"session" : getsession(), 
        								"otp1" : $('#otp1').val(), 
        								"otp2":  $('#otp2').val()}, token_resync_callback);
    }
}

function losttoken_callback(xhdr, textStatus){
	var resp = xhdr.responseText;

	obj = jQuery.parseJSON(resp);
    if (obj.result.status) {
        var serial = obj.result.value.serial;
        var end_date = obj.result.value.end_date;
        var password = obj.result.value.password;
        $('#temp_token_serial').html(serial);
        $('#temp_token_password').html(password);
        $('#temp_token_enddate').html(end_date);
        $dialog_view_temporary_token.dialog("open");
    } else {
    	alert_info_text("text_losttoken_failed", obj.result.error.message, ERROR);
    }
    $("#token_table").flexReload();
    $('#selected_tokens').html('');
    disable_all_buttons();
    log('Token ' + tokens + ' lost.');
}

function token_losttoken() {
	var tokentab = 0;
	var tokens = get_selected_tokens();
    var count = tokens.length;
    for (i = 0; i < count; i++) {
        var serial = tokens[i];
        resp = clientUrlFetch("/admin/losttoken", {"serial" : serial, "session" : getsession()}, losttoken_callback);
    }
}


/****************************************************************************
 * PIN setting
 */

function setpin_callback(xhdr, textStatus) {
	var resp = xhdr.responseText;
	var obj = jQuery.parseJSON(resp);
    if (obj.result.status) {
            if (obj.result.value)
                alert_info_text("text_setpin_success");
            else
                alert_info_text("text_setpin_failed", obj.result.error.message, ERROR);
        }
}

function token_setpin(){
	var token_string = $('#setpin_tokens').val();
	var tokens = token_string.split(",");
    var count = tokens.length;
    var pin = $('#pin1').val();
    var pintype = $('#pintype').val();

	for ( i = 0; i < count; i++) {
		var serial = tokens[i];
		if (pintype.toLowerCase() == "otp") {
            clientUrlFetch("/admin/set", {"serial" : serial , "pin" : pin, "session" : getsession()}, setpin_callback);
		} else if ((pintype.toLowerCase() == "motp")) {
			clientUrlFetch("/admin/setPin", {"serial" : serial, "userpin" : pin, "session" : getsession()}, setpin_callback);
		} else if ((pintype.toLowerCase() == "ocrapin")) {
            clientUrlFetch("/admin/setPin", {"serial" : serial, "userpin" : pin, "session" : getsession()}, setpin_callback);
		} else
			alert_info_text("text_unknown_pintype", pintype, ERROR);
	}

}

function view_setpin_dialog(tokens) {
	/*
	 * This function encapsulates the set pin dialog and is
	 * called by the button "set pin" and can be called
	 * after enrolling or assigning tokesn.
	 *
	 * Parameter: array of serial numbers
	 */
	var token_string = tokens.join(", ");
    $('#dialog_set_pin_token_string').html(token_string);
    $('#setpin_tokens').val(tokens);
    $dialog_setpin_token.dialog('open');
}


function view_setpin_after_enrolling(tokens) {
	/*
     * TODO: depending on the OTP PIN type (o,1,2,) we can display
     * or not display it. In case of no OTP PIN or AD PIN, we don't want to see this dialog!
     */
    view_setpin_dialog(tokens);
}

function view_setpin_after_assigning(tokens) {
	/*
     * TODO: depending on the OTP PIN type (o,1,2,) we can display
     * or not display it. In case of no OTP PIN or AD PIN, we don't want to see this dialog!
     */
    view_setpin_dialog(tokens);
}

/******************************************************************************
 *  token info
 */
function token_info(){
    var tokentab = 0;
    var tokens = get_selected_tokens();
    var count = tokens.length;
    if (count != 1) {
        alert_info_text("text_only_one_token_ti");
        return false;
    }
    else {
        var serial = tokens[0];
        var resp = clientUrlFetchSync("/manage/tokeninfo",{"serial" : serial, "session" : getsession()});
        return resp;
    }
}


function get_token_type(){
    var tokentab = 0;
    var tokens = get_selected_tokens();
    var count = tokens.length;
    var ttype = "";
    if (count != 1) {
        alert_info_text("text_only_one_token_type");
        return false;
    }
    else {
        var serial = tokens[0];
        var resp = clientUrlFetchSync("/admin/show",{"serial" : serial, "session" : getsession()});
        try {
            var obj = jQuery.parseJSON(resp);
            ttype = obj['result']['value']['data'][0]['privacyIDEA.TokenType'];
        }
        catch (e) {
            alert_info_text("text_fetching_tokentype_failed", e, ERROR);
        }
        return ttype;
    }
}

function tokeninfo_redisplay() {
	var tokeninfo = token_info();
    $dialog_token_info.html(tokeninfo);
    set_tokeninfo_buttons();
}

function token_info_save(){
    var info_type = $('input[name="info_type"]').val();
    var info_value = $('#info_value').val();

    var tokens = get_selected_tokens();
    var count = tokens.length;
    var serial = tokens[0];
    if (count != 1) {
        alert_info_text("text_only_one_token_ti");
        return false;
    }
    else {
    	// see: http://stackoverflow.com/questions/10640159/key-for-javascript-dictionary-is-not-stored-as-value-but-as-variable-name
    	var param={"serial" : serial, "session" : getsession()};
    	param[info_type] = info_value;
        var resp = clientUrlFetchSync("/admin/set", param);
        var rObj = jQuery.parseJSON(resp);
        if (rObj.result.status == false) {
        	alert(rObj.result.error.message);
        }
    }

    // re-display
    tokeninfo_redisplay();
    return true;
}



function enroll_callback(xhdr, textStatus, p_serial) {
	var resp = xhdr.responseText;
    var obj = jQuery.parseJSON(resp);
    var serial = p_serial;

    //alert('TODO: enroll_callback - return from init the values, which makes this easier')

    $('#dialog_enroll').hide();
    if (obj.result.status) {
    	if (obj.hasOwnProperty('detail')) {
		   var detail = obj.detail;
		   if (detail.hasOwnProperty('serial')) {
		      serial = detail.serial;
		   }
    	}
        alert_info_text("text_created_token", serial);
        if (true == g.display_genkey) {

        	// display the QR-Code of the URL. tab
      	    var users = get_selected_users();
        	var emails = get_selected_email();
        	$('#token_enroll_serial').html(serial);
        	if (users.length >= 1) {
        		$('#token_enroll_user').html("<a href=mailto:" +emails[0]+">"+users[0].login+"</a>");
        	} else {
        		$('#token_enroll_user').html("---");
        	}


        	var dia_text = '<div id="qr_url_tabs"><ul>';
			// TAB header
        	for (var k in obj.detail) {
        		var theDetail = obj.detail[k];
        		if (theDetail != null && theDetail.hasOwnProperty('description') ){
        			dia_text += '<li><a href="#url_content_'+k+'">'+theDetail.description+'</a></li>';
        		}
        	};
        	dia_text += '</ul>';
        	//console_log(obj.detail);
        	// TAB content
        	for (var k in obj.detail) {
        		var theDetail = obj.detail[k];
        		if (theDetail != null && theDetail.hasOwnProperty('description') ){
        			//console_log(theDetail)
	        		dia_text += '<div id="url_content_'+k+'">';
			    	var desc = theDetail.description;
	        		var value = theDetail.value;
	        		var img   = theDetail.img;
	        		dia_text += "<p>";
	        		var href = "<a href='"+ value+ "'>"+desc+"</a>";
	        		dia_text += href;
	        		var qr_code = img;
	        		dia_text += "<br/>";
	        		dia_text += qr_code;
	        		dia_text += "</p>";
	        		dia_text += "</div>";
        		}
        	}
        	// serial number
        	dia_text += '<input type=hidden id=enroll_token_serial value='+serial+'>';
        	// end of qr_url_tabs
        	dia_text += '</div>';

        	$('#enroll_url').html(dia_text);
        	$('#qr_url_tabs').tabs();
        	$dialog_show_enroll_url.dialog("open");
        } else {
        	view_setpin_after_enrolling([serial]);
        }
    }
    else {
        alert_info_text("text_error_creating_token", obj.result.error.message, ERROR);
    }
    $('#token_table').flexReload();
}



function token_enroll(){
    
    var users = get_selected_users();
    var url = '/admin/init';
    var params = {"session" : getsession()};
    var serial = '';
    // User
    if (users[0]) {
        params['user'] = users[0].login;
        params['resConf'] = users[0].resolver;
        params['realm'] = $('#realm').val();
    }
    // when the init process generated a key, this will be displayed to the administrator
    g.display_genkey = false;
    // get the token type and call the geturl_params() method for this token - if exist
    var typ = $('#tokentype').val();
	// dynamic tokens might overwrite this description
	params['description']='webGUI_generated';

	/* switch can be removed by default, if token migration is completed*/

    switch (typ) {
		case 'ocra':
			params['sharedsecret'] = 1;
            // If we got to generate the hmac key, we do it here:
            if  ( $('#ocra_key_cb').attr('checked') ) {
            	params['genkey']	= 1;
            } else {
	            // OTP Key
    	        params['otpkey'] 	= $('#ocra_key').val();
            }
            break;

        default:
        	if (typ in $tokentypes)
			{  /*
			    * the dynamic tokens must provide a function to gather all data from the form
				*/
				var params = {};
				var functionString = typ + '_get_enroll_params';
				var funct = window[functionString];
				var exi = typeof funct;

				if (exi == 'undefined') {
					alert('undefined function '+ functionString + ' for tokentype ' + typ  );
				}
				if (exi == 'function') {
					params = window[functionString]();
				}
			} else {
	            alert_info_text("text_enroll_type_error", "", ERROR);
	            return false;
            }
    }
	params['type'] = typ;
	if (params['genkey'] == 1){
		g.display_genkey = true;
	}
    clientUrlFetch(url, params, enroll_callback, serial);

}

function get_enroll_infotext(){
    var users = get_selected_users();
    $("#enroll_info_text_user").hide();
    $("#enroll_info_text_nouser").hide();
    $("#enroll_info_text_multiuser").hide();
    if (users.length == 1) {
    	$("#enroll_info_text_user").show();
    	$('#enroll_info_user').html(users[0].login+" ("+users[0].resolver+")");
    }
    else
        if (users.length == 0) {
            $("#enroll_info_text_nouser").show();
        }
        else {
        	$("#enroll_info_text_multiuser").show();
        }
}

function tokentype_changed(){
    var $tokentype = $("#tokentype").val();
    var html = "unknown tokentype!";

    // might raise an error, which must be catched by the caller
    $systemConfig = get_server_config();

    // verify that the tokentypes is a defined dict
    if ($tokentypes == undefined) {
    	$tokentypes = {};
    }

    if (len($tokentypes) > 0) {
    	for (var k in $tokentypes){
    		var tt = '#token_enroll_'+k;
    		//console_log(tt);
    		$(tt).hide();
    	}
    }

	$('#token_enroll_ocra').hide();

    switch ($tokentype) {
		case "ocra":
			$('#token_enroll_ocra').show();
            break;
        case undefined:
        	break;
		default:
			// call the setup default method for the token enrollment, before shown
			var functionString = ''+$tokentype+'_enroll_setup_defaults';
			var funct = window[functionString];
			var exi = typeof funct;
			try{
				if (exi == 'function') {
					var l_params = window[functionString]($systemConfig);
				}
			}
			catch(err) {
				//console_log('callbacack for ' + functionString + ' not found!')
			}

			$('#token_enroll_'+$tokentype).show();
			break;
    }
}



// ##################################################
// Icon functions for the dialogs

function do_dialog_icons(){
    $('.ui-dialog-buttonpane').find('button:contains("Cancel")').button({
        icons: {
            primary: 'ui-icon-cancel'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("New")').button({
        icons: {
            primary: 'ui-icon-plusthick'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Delete")').button({
        icons: {
            primary: 'ui-icon-trash'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Save")').button({
        icons: {
            primary: 'ui-icon-disk'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Set PIN")').button({
        icons: {
            primary: 'ui-icon-pin-s'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Edit")').button({
        icons: {
            primary: 'ui-icon-pencil'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("load tokenfile")').button({
        icons: {
            primary: 'ui-icon-folder-open'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("load token file")').button({
        icons: {
            primary: 'ui-icon-folder-open'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Set Default")').button({
        icons: {
            primary: 'ui-icon-flag'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Enroll")').button({
        icons: {
            primary: 'ui-icon-plusthick'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Resync")').button({
        icons: {
            primary: 'ui-icon-refresh'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("unassign token")').button({
        icons: {
            primary: 'ui-icon-pin-arrowthick-1-w'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("delete token")').button({
        icons: {
            primary: 'ui-icon-pin-trash'
        }
    });
    $('.ui-dialog-buttonpane').find('button:contains("Close")').button({
        icons: {
            primary: 'ui-icon-closethick'
        }
    });
    //$('.ui-dialog-buttonpane').find('button:contains("Clear Default")').button({
    //	icons: {primary: 'ui-icon-pin-s'}});
}

// #################################################
//
// realms and resolver functions
//
function _fill_realms(widget, also_none_realm){
    var defaultRealm = "";
    $.post('/system/getRealms', {'session':getsession()} ,
     function(data, textStatus, XMLHttpRequest){
        // value._default_.realmname
        // value.XXXX.realmname
        //var realms = "Realms: <select id=realm>"
        var realms = "";
        // we need to calculate the length:
        if (1==also_none_realm) {
        	realms += "<option></option>";
        }
        var realmCount = 0;
        var value = {};
        if (data.hasOwnProperty('result')) {
        	value = data.result.value;
        }
        for (var i in value) {
            realmCount += 1;
		}
		var defaultRealm;
        for (var i in value) {
            if (value[i]['default']) {
                realms += "<option selected>";
                defaultRealm = i;
            }
            else
                if (realmCount == 1) {
                    realms += "<option selected>";
                    defaultRealm = i;
                }
                else {
                    realms += "<option>";
                }
            //realms += data.result.value[i].realmname;
            // we use the lowercase realm name
            realms += i;
            realms += "</option>";
        }

        //realms += "</select>";
        widget.html(realms);
    });
    return defaultRealm;
}

function fill_realms() {
	var defaultRealm = _fill_realms($('#realm'), 0);
	return defaultRealm;
}

function get_realms(){
    var realms = new Array();
    var resp = $.ajax({
        	url: '/system/getRealms',
        	async: false,
        	data: { 'session':getsession()},
        	type: "POST"
    	}).responseText;
    var data = jQuery.parseJSON(resp);
	for (var i in data.result.value) {
		realms.push(i);
    };
    return realms;
}

// ####################################################
//
//  jQuery stuff
//

function get_serial_by_otp_callback(xhdr, textStatus) {
	var resp = xhdr.responseText;
	var obj = jQuery.parseJSON(resp);
    if (obj.result.status == true) {
    	if (obj.result.value.success==true) {
    		if (""!=obj.result.value.serial) {
    			var text="Found the token: "+obj.result.value.serial;
    			if (obj.result.value.user_login != "") {
    				text += "\nThe token belongs to " + obj.result.value.user_login+" ("+obj.result.value.user_resolver+")";
    			}
    			alert_info_text(text);
    		}
    		else
    			alert_info_text("text_get_serial_no_otp");
    	}else{
    		alert_info_text("text_get_serial_error", "", ERROR);
    	}
    } else {
    	alert_info_text("text_failed", obj.result.error.message, ERROR);
    }
}
// get Serial by OTP
function getSerialByOtp(otp, type, assigned, realm) {
	var param = {"session" : getsession()};
	param["otp"] = otp;
	if (""!=type) {
		param["type"]=type;
	}
	if (""!=assigned) {
		param["assigned"] = assigned;
	}
	if (""!=realm) {
		param["realm"] = realm;
	}
	clientUrlFetch('/admin/getSerialByOtp', param, get_serial_by_otp_callback);

}


function checkpins(){
    var pin1 = $('#pin1').val();
    var pin2 = $('#pin2').val();
    if (pin1 == pin2) {
        $('#pin1').removeClass('ui-state-error');
        $('#pin2').removeClass('ui-state-error');
    }
    else {
        $('#pin1').addClass('ui-state-error');
        $('#pin2').addClass('ui-state-error');
    }
    return false;
}


function ldap_resolver_ldaps() {
	/*
	 * This function checks if the LDAP URI is using SSL.
	 * If so, it displays the CA certificate entry field.
	 */
	var ldap_uri = $('#ldap_uri').val();
	if (ldap_uri.toLowerCase().match(/^ldaps:/)) {
		$('#ldap_resolver_certificate').show();
	} else {
		$('#ldap_resolver_certificate').hide();
	}
	return false;
}

function parseXML(xml, textStatus){
    var version = $(xml).find('version').text();
    var status = $(xml).find('status').text();
    var value = $(xml).find('value').text();
    var message = $(xml).find('message').text();

    if ("error" == textStatus) {
        alert_info_text("text_privacyidea_comm_fail", "", ERROR);
    }
    else {
        if ("False" == status) {
            alert_info_text("text_token_import_failed", message, ERROR);
        }
        else {
            // reload the token_table
            $('#token_table').flexReload();
            $('#selected_tokens').html('');
            disable_all_buttons();
            alert_info_text("text_token_import_result", value);
            
        }
    }
	hide_waiting();
};

function parsePolicyImport(xml, textStatus) {
	var version = $(xml).find('version').text();
    var status = $(xml).find('status').text();
    var value = $(xml).find('value').text();
    var message = $(xml).find('message').text();

    if ("error" == textStatus) {
        alert_info_text("text_privacyidea_comm_fail", "", ERROR);
    }
    else {
        if ("False" == status) {
            alert_info_text("text_policy_import_failed", message);
        }
        else {
            // reload the token_table
            $('#policy_table').flexReload();
            alert_info_text("text_policy_import_result", value);
        }
    }
	hide_waiting();
};

function import_policy() {
	show_waiting();
	$('#load_policies').ajaxSubmit({
		data: { session:getsession() },
		type: "POST",
		error: parsePolicyImport,
		success: parsePolicyImport,
		dataType: 'xml'
	});
	return false;
}

function load_tokenfile(type){
    show_waiting();
    if ("aladdin-xml" == type) {
		$('#load_tokenfile_form_aladdin').ajaxSubmit({
			data: { session:getsession() },
			type: "POST",
			error: parseXML,
			success: parseXML,
			dataType: 'xml'
		});
	}
	else
		if ("feitian" == type) {
			$('#load_tokenfile_form_feitian').ajaxSubmit({
				data: { session:getsession() },
				type: "POST",
				error: parseXML,
				success: parseXML,
				dataType: 'xml'
			});
		}
		else
			if ("pskc" == type) {
				$('#load_tokenfile_form_pskc').ajaxSubmit({
					data: { session:getsession() },
					type: "POST",
					error: parseXML,
					success: parseXML,
					dataType: 'xml'
				});
			}
			else
				if ("dpw" == type) {
					$('#load_tokenfile_form_dpw').ajaxSubmit({
						data: { session:getsession() },
						type: "POST",
						error: parseXML,
						success: parseXML,
						dataType: "xml"
					});
				} else
                if ("dat" == type) {
                    $('#load_tokenfile_form_dat').ajaxSubmit({
                        data: { session:getsession() },
                        type: "POST",
                        error: parseXML,
                        success: parseXML,
                        dataType: "dat"
                    });
                }
                else
				if ("vasco" == type) {
					$('#load_tokenfile_form_vasco').ajaxSubmit({
						data: { session:getsession() },
						type: "POST",
						error: parseXML,
						success: parseXML,
						dataType: "xml"
					});
				} else
				if ("oathcsv" == type) {
					$('#load_tokenfile_form_oathcsv').ajaxSubmit({
						data: { session:getsession() },
						type: "POST",
						error: parseXML,
						success: parseXML,
						dataType: "xml"
					});
				}

				if ("yubikeycsv" == type) {
					$('#load_tokenfile_form_yubikeycsv').ajaxSubmit({
						data: { session:getsession() },
						type: "POST",
						error: parseXML,
						success: parseXML,
						dataType: "xml"
					});
				}

				else {
					alert_info_text( "text_import_unknown_type", "", ERROR);
				};
    return false;
}


function load_system_config(){
    show_waiting();
    $.post('/system/getConfig', { 'session':getsession()} ,
     function(data, textStatus, XMLHttpRequest){
        // checkboxes this way:
        hide_waiting();
        checkBoxes = new Array();
        if (data.result.value.DefaultResetFailCount == "True") {
            checkBoxes.push("sys_resetFailCounter");
        };
        if (data.result.value.splitAtSign == "True") {
            checkBoxes.push("sys_splitAtSign");
        };
        if (data.result.value.allowSamlAttributes == "True") {
            checkBoxes.push("sys_allowSamlAttributes");
        };
        if (data.result.value.PrependPin == "True") {
            checkBoxes.push("sys_prependPin");
        };
        if (data.result.value.FailCounterIncOnFalsePin == "True") {
            checkBoxes.push("sys_failCounterInc");
        };
        if (data.result.value.AutoResync == "True") {
            checkBoxes.push("sys_autoResync");
        };
        if (data.result.value.PassOnUserNotFound == "True") {
            checkBoxes.push("sys_passOnUserNotFound");
        };
        if (data.result.value.PassOnUserNoToken == "True") {
            checkBoxes.push("sys_passOnUserNoToken");
        };
        if (data.result.value['selfservice.realmbox'] == "True") {
            checkBoxes.push("sys_realmbox");
        }
        $("input:checkbox").val(checkBoxes);
        $('#sys_maxFailCount').val(data.result.value.DefaultMaxFailCount);
        $('#sys_syncWindow').val(data.result.value.DefaultSyncWindow);
        $('#sys_otpLen').val(data.result.value.DefaultOtpLen);
        $('#sys_countWindow').val(data.result.value.DefaultCountWindow);
        $('#sys_challengeTimeout').val(data.result.value.DefaultChallengeValidityTime);
        $('#sys_autoResyncTimeout').val(data.result.value.AutoResyncTimeout);
        $('#sys_mayOverwriteClient').val(data.result.value.mayOverwriteClient);
        // OCRA stuff
        $('#ocra_default_suite').val(data.result.value.OcraDefaultSuite);
        $('#ocra_default_qr_suite').val(data.result.value.QrOcraDefaultSuite);
        $('#ocra_max_challenge').val(data.result.value.OcraMaxChallenges);
        $('#ocra_challenge_timeout').val(data.result.value.OcraChallengeTimeout);

        /*todo call the 'tok_fill_config.js */

    });
}

function save_system_config(){
    show_waiting();
    $.post('/system/setConfig', {
        'DefaultMaxFailCount': $('#sys_maxFailCount').val(),
        'DefaultSyncWindow': $('#sys_syncWindow').val(),
        'DefaultOtpLen': $('#sys_otpLen').val(),
        'DefaultCountWindow': $('#sys_countWindow').val(),
        'DefaultChallengeValidityTime': $('#sys_challengeTimeout').val(),
        'AutoResyncTimeout': $('#sys_autoResyncTimeout').val(),
        'mayOverwriteClient': $('#sys_mayOverwriteClient').val(),
        'totp.timeShift': $('#totp_timeShift').val(),
        'totp.timeStep': $('#totp_timeStep').val(),
        'totp.timeWindow': $('#totp_timeWindow').val(),
        'OcraDefaultSuite' : $('#ocra_default_suite').val(),
        'QrOcraDefaultSuite' : $('#ocra_default_qr_suite').val(),
        'OcraMaxChallenges' : $('#ocra_max_challenge').val(),
        'OcraChallengeTimeout' : $('#ocra_challenge_timeout').val(),
        'session':getsession()},
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_system_save_error", "", ERROR);
        }
    });

    var allowsaml = "False";
    if ($("#sys_allowSamlAttributes").is(':checked')) {
        allowsaml = "True";
    }
    var fcounter = "False";
    if ($("#sys_failCounterInc").is(':checked')) {
        fcounter = "True";
    }
    var splitatsign = "False";
    if ($("#sys_splitAtSign").is(':checked')) {
        splitatsign = "True";
    }
    var prepend = "False";
    if ($("#sys_prependPin").is(':checked')) {
        prepend = "True";
    }
    var autoresync = "False";
    if ($('#sys_autoResync').is(':checked')) {
        autoresync = "True";
    }
    var passOUNFound = "False";
    if ($('#sys_passOnUserNotFound').is(':checked')) {
        passOUNFound = "True";
    }
    var passOUNToken = "False";
    if ($('#sys_passOnUserNoToken').is(':checked')) {
        passOUNToken = "True";
    }
    var defaultReset = "False";
    if ($("#sys_resetFailCounter").is(':checked')) {
        defaultReset = "True";
    }
    var realmbox = "False";
    if ($("#sys_realmbox").is(':checked')) {
        realmbox = "True";
    }
    $.post('/system/setConfig', { 'session':getsession(),
    		'PrependPin' :prepend,
    		'FailCounterIncOnFalsePin' : fcounter ,
    		'splitAtSign' : splitatsign,
    		'DefaultResetFailCount' : defaultReset,
    		'AutoResync' :    autoresync,
    		'PassOnUserNotFound' : passOUNFound,
    		'PassOnUserNoToken' : passOUNToken,
    		'selfservice.realmbox' : realmbox,
    		'allowSamlAttributes' : allowsaml },
     function(data, textStatus, XMLHttpRequest){
        if (data.result.status == false) {
            alert_info_text("text_system_save_error_checkbox", "", ERROR);
        }
    });
}

function save_ldap_config(){
    // Save all LDAP config
    var resolvername = $('#ldap_resolvername').val();
    var resolvertype = "ldapresolver";
    var ldap_map = {
        '#ldap_uri': 'LDAPURI',
        '#ldap_basedn': 'LDAPBASE',
        '#ldap_binddn': 'BINDDN',
        '#ldap_password': 'BINDPW',
        '#ldap_timeout': 'TIMEOUT',
        '#ldap_sizelimit': 'SIZELIMIT',
        '#ldap_loginattr': 'LOGINNAMEATTRIBUTE',
        '#ldap_searchfilter': 'LDAPSEARCHFILTER',
        '#ldap_userfilter': 'LDAPFILTER',
        '#ldap_mapping': 'USERINFO',
        '#ldap_uidtype': 'UIDTYPE',
        '#ldap_noreferrals' : 'NOREFERRALS',
        '#ldap_certificate': 'CACERTIFICATE',
    };
    var url = '/system/setResolver?name='+resolvername+'&type='+resolvertype+'&';
    for (var key in ldap_map) {
        var data = $(key).serialize();
        var new_data = data.replace(/^.*=/, ldap_map[key] + '=');
        url += new_data + "&";
    }
    // checkboxes
    var noreferrals="False";
    if ($("#ldap_noreferrals").attr('checked')) {
        noreferrals = "True";
    }
    url += "NOREFERRALS="+noreferrals+"&";

    url += "session="+getsession();
    show_waiting();
    $.post(url,
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_error_ldap", data.result.error.message, ERROR);
        } else {
        	resolvers_load();
        	$dialog_ldap_resolver.dialog('close');
        }
    });
    return false;
}

function save_realm_config(){
    var realm = $('#realm_name').val();
    show_waiting();
    $.post('/system/setRealm', {
    	'realm' :realm,
    	'resolvers' : g.resolvers_in_realm_to_edit,
    	'session':getsession() },
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
        	alert_info_text("text_error_realm", data.result.error.message, ERROR);
        } else {
        	fill_realms();
        	realms_load();
        	alert_info_text("text_realm_created", realm);
        }
    });
}

function save_tokenrealm_config(){
    var tokens = get_selected_tokens();
    var realms = g.realms_of_token.join(",");
    for (var i = 0; i < tokens.length; ++i) {
        serial = tokens[i];
        show_waiting();
        $.post('/admin/tokenrealm', {
          'serial' :serial,
          'realms' : realms,
          'session':getsession()},
         function(data, textStatus, XMLHttpRequest){
            hide_waiting();
            if (data.result.status == false) {
                alert_info_text("text_error_set_realm", data.result.error.message, ERROR);
            }
            else {
                $('#token_table').flexReload();
            }
         });
    }
}

function save_file_config(){
   /*
    * save the passwd resolver config
    */
    var resolvername = $('#file_resolvername').val();
    var resolvertype = "passwdresolver";
    var fileName = $('#file_filename').val();
    var params = {};
    params['name'] = resolvername;
    params['type'] = resolvertype;
    params['fileName'] = fileName;
    params['session'] = getsession();
    show_waiting();
    $.post('/system/setResolver', params,
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_error_save_file", data.result.error.message, ERROR);
        } else {
            resolvers_load();
            $dialog_file_resolver.dialog('close');
        }
    });
}


function save_scim_config() {
    // Save all SCIM config
    var resolvername = $('#scim_resolvername').val();
    var resolvertype = "scimresolver";
    var map = {
    	'#scim_authserver' : "authserver",
    	'#scim_resourceserver' : "resourceserver",
    	'#scim_client' : "client",
    	'#scim_secret' : "secret",
    	'#scim_mapping' : "mapping"
    };
    var url = '/system/setResolver?name='+resolvername+'&type='+resolvertype+'&';
    for (var key in map) {
        var data = $(key).serialize();
        var new_data = data.replace(/^.*=/, map[key] + '=');
        url += new_data + "&";
    }
    url += '&session='+getsession();
    show_waiting();
    $.post(url,
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_error_save_scim", data.result.error.message, ERROR);
        } else {
        	resolvers_load();
        	$dialog_scim_resolver.dialog('close');
        }
    });
    return false;
}


function save_sql_config(){
    // Save all SQL config
    var resolvername = $('#sql_resolvername').val();
    var resolvertype = "sqlresolver";
    var map = {
        '#sql_database': 'Database',
        '#sql_driver': 'Driver',
        '#sql_server': 'Server',
        '#sql_port': 'Port',
        '#sql_limit': 'Limit',
        '#sql_user': 'User',
        '#sql_password': 'Password',
        '#sql_table': 'Table',
        '#sql_mapping': 'Map',
        '#sql_where': 'Where',
        '#sql_conparams': 'conParams',
        '#sql_encoding' : 'Encoding'
    };
    var url = '/system/setResolver?name='+resolvername+'&type='+resolvertype+'&';
    for (var key in map) {
        var data = $(key).serialize();
        var new_data = data.replace(/^.*=/, map[key] + '=');
        url += new_data + "&";
    }
    url += '&session='+getsession();
    show_waiting();
    $.post(url,
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        if (data.result.status == false) {
            alert_info_text("text_error_save_sql", data.result.error.message, ERROR);
        } else {
        	resolvers_load();
        	$dialog_sql_resolver.dialog('close');
        }
    });
    return false;
}


// ----------------------------------------------------------------
//   Realms
function realms_load(){
    g.realm_to_edit = "";
    show_waiting();
    $.post('/system/getRealms', { 'session': getsession() },
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        var realms = '<ol id="realms_select" class="select_list" class="ui-selectable">';
        for (var key in data.result.value) {
            var default_realm = "";
            var resolvers = "";
            var resolver_list = data.result.value[key].useridresolver;
            for (var reso in resolver_list) {
                var r = resolver_list[reso].split(".");
                resolvers += r[r.length - 1] + " ";
            }

            if (data.result.value[key]['default']) {
                default_realm = " (Default) ";
            }

            realms += '<li class="ui-widget-content">' + key + default_realm + ' [' + resolvers + ']</li>';
        }
        realms += '</ol>';
        $('#realm_list').html(realms);
        $('#realms_select').selectable({
            stop: function(){
                $(".ui-selected", this).each(function(){
                    var index = $("#realms_select li").index(this);
                    g.realm_to_edit = this.innerHTML;
                }); // end of each
            } // end of stop function
        }); // end of selectable
    }); // end of $.post
}

function realm_ask_delete(){
	// replace in case of normal realms
    var realm = g.realm_to_edit.replace(/^(\S+)\s+\[(.*)$/, "$1");
	// replace in case of default realm
	realm = realm.replace(/^(\S+)\s+\(Default\)\s+\[(.*)$/, "$1");

	$('#realm_delete_name').html(realm);
	$dialog_realm_ask_delete.dialog('open');
}

// -----------------------------------------------------------------
//   Resolvers


function resolvers_load(){
    show_waiting();
    $.post('/system/getResolvers', {'session':getsession()},
     function(data, textStatus, XMLHttpRequest){
        hide_waiting();
        var resolvers = '<ol id="resolvers_select" class="select_list" class="ui-selectable">';
        var count = 0;
        for (var key in data.result.value) {
            //resolvers += '<input type="radio" id="resolver" name="resolver" value="'+key+'">';
            //resolvers += key+' ('+data.result.value[key].type+')<br>';
            resolvers += '<li class="ui-widget-content">' + key + ' [' + data.result.value[key].type + ']</li>';
            count = count +1 ;
        }
        resolvers += '</ol>';
        if (count > 0) {
	        $('#resolvers_list').html(resolvers);
	        $('#resolvers_select').selectable({
	            stop: function(){
	                $(".ui-selected", this).each(function(){
	                    var index = $("#resolvers_select li").index(this);
	                    g.resolver_to_edit = this.innerHTML;
	                }); // end of each
	            } // end of stop function
	        }); // end of selectable
        } // end of count > 0
        else {
        	$('#resolvers_list').html("");
        	g.resolver_to_edit = "";
        };
    }); // end of $.post
}


function resolver_delete(){
	var reso = $('#delete_resolver_name').html();
	show_waiting();
	$.post('/system/delResolver', { 'resolver' : reso, 'session':getsession()},
	 function(data, textStatus, XMLHttpRequest){
		hide_waiting();
		if (data.result.status == true) {
			resolvers_load();
			if (data.result.value == true)
				alert_info_text("text_resolver_delete_success", reso);
			else
				alert_info_text("text_resolver_delete_fail", reso, ERROR);
		}
		else {
			alert_info_text("text_resolver_delete_fail", data.result.error.message, ERROR);
		}
	});
}

function realm_delete(){
	var realm = $('#realm_delete_name').html();
	$.post('/system/delRealm', {'realm' : realm,'session':getsession()},
	 function(data, textStatus, XMLHttpRequest){
		if (data.result.status == true) {
			fill_realms();
			realms_load();
			alert_info_text("text_realm_delete_success", realm);
		}
		else {
			alert_info_text("text_realm_delete_fail", data.result.error.message, ERROR);
		}
		hide_waiting();
	});
}

function resolver_ask_delete(){
   if (g.resolver_to_edit.length >0 ) {
    if (g.resolver_to_edit.match(/(\S+)\s(\S+)/)) {
        var reso = g.resolver_to_edit.replace(/(\S+)\s+\S+/, "$1");
        var type = g.resolver_to_edit.replace(/\S+\s+(\S+)/, "$1");

		$('#delete_resolver_type').html(type);
		$('#delete_resolver_name').html(reso);
		$dialog_resolver_ask_delete.dialog('open');
    }
    else {
        alert_info_text("text_regexp_error", g.resolver_to_edit, ERROR);
    }
   }
}

function resolver_edit_type(){
    var reso = g.resolver_to_edit.replace(/(\S+)\s+\S+/, "$1");
    var type = g.resolver_to_edit.replace(/\S+\s+\[(\S+)\]/, "$1");
    switch (type) {
        case "ldapresolver":
            resolver_ldap(reso);
            break;
        case "sqlresolver":
            resolver_sql(reso);
            break;
        case "scimresolver":
            resolver_scim(reso);
            break;
        case "passwdresolver":
            resolver_file(reso);
            break;
    }
}


function resolver_new_type(){
	var $list = get_resolver_list();
	if ($.inArray("PasswdIdResolver", $list) >=0 ) {
		$('#button_new_resolver_type_file').show();
	} else {
		$('#button_new_resolver_type_file').hide();
	}
	if ($.inArray("LDAPIdResolver", $list) >= 0) {
		$('#button_new_resolver_type_ldap').show();
	} else {
		$('#button_new_resolver_type_ldap').hide();
	}
	if ($.inArray("SQLIdResolver", $list) >= 0) {
		$('#button_new_resolver_type_sql').show();
	} else {
		$('#button_new_resolver_type_sql').hide();
	}
	if ($.inArray("SCIMIdResolver", $list) >= 0) {
		$('#button_new_resolver_type_scim').show();
	} else {
		$('#button_new_resolver_type_scim').hide();
	}
	
	
	$dialog_ask_new_resolvertype.dialog('open');
}

function add_token_config()
{

	if ($tokentypes == undefined) {
    	$tokentypes = {};
    }

    if (len($tokentypes) > 0) {
    	for (var k in $tokentypes){
    		var tt = '#token_enroll_'+k;
    		//console_log(tt);
    		$(tt).hide();
    	}
    }
}

function set_tokeninfo_buttons(){
/*
 * enables the tokeninfo buttons.
 * As tokeninfo HTML is read from the server via /manage/tokeninfo
 * jqeuery needs to activate the buttons after each call.
 */
	$('#ti_button_desc').button({
		icons: { primary: 'ui-icon-pencil' },
		text: false
	});
	$('#ti_button_desc').click(function(){
    	$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="description">\
				<input id=info_value name=info_value></input>\
				');
		translate_dialog_ti_description();
        $dialog_tokeninfo_set.dialog('open');
    });

    $('#ti_button_otplen').button({
		icons: { primary: 'ui-icon-pencil' },
		text: false
	});
	$('#ti_button_otplen').click(function(){
		$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="otpLen">\
			<select id=info_value name=info_value>\
			<option value=6>6 digits</option>\
			<option value=8>8 digits</option>\
			</select>');
		translate_dialog_ti_otplength();
        $dialog_tokeninfo_set.dialog('open');
	});

    $('#ti_button_sync').button({
		icons: { primary: 'ui-icon-pencil' },
		text: false
	});
	$('#ti_button_sync').click(function(){
        $dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="syncWindow">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_syncwindow();
        $dialog_tokeninfo_set.dialog('open');
	});


    $('#ti_button_countwindow').button({
		icons: { primary: 'ui-icon-pencil' },
		text: false
	});
	$('#ti_button_countwindow').click(function(){
	    $dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="counterWindow">\
					<input id=info_value name=info_value></input>\
					');
		translate_dialog_ti_counterwindow();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_maxfail').button({
		icons: { primary: 'ui-icon-pencil' },
		text: false
	});
	$('#ti_button_maxfail').click(function(){
        $dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="maxFailCount">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_maxfailcount();
        $dialog_tokeninfo_set.dialog('open');
	});

    $('#ti_button_failcount').button({
		icons: { primary: 'ui-icon-arrowrefresh-1-s' },
		text: false
		//label: "Reset Failcounter"
	});
	$('#ti_button_failcount').click(function(){
		serial = get_selected_tokens()[0];
        clientUrlFetchSync("/admin/reset", {"serial" : serial, "session" : getsession()});
    	tokeninfo_redisplay();
	});

	$('#ti_button_hashlib').button({
		icons: { primary: 'ui-icon-locked'},
		text : false,
		label: "hashlib"
	});
	$('#ti_button_hashlib').click(function(){
		$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="hashlib">\
			<select id=info_value name=info_value>\
			<option value=sha1>sha1</option>\
			<option value=sha256>sha256</option>\
			</select>');
		translate_dialog_ti_hashlib();
	    $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_count_auth_max').button({
		icons: { primary: 'ui-icon-arrowthickstop-1-n'},
		text : false,
		label: "auth max"
	});
	$('#ti_button_count_auth_max').click(function(){
        $dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="countAuthMax">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_countauthmax();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_count_auth_max_success').button({
		icons: { primary: 'ui-icon-arrowthick-1-n'},
		text : false,
		label: "auth max_success"
	});
	$('#ti_button_count_auth_max_success').click(function(){
        $dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="countAuthSuccessMax">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_countauthsuccessmax();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_valid_start').button({
		icons: { primary: 'ui-icon-seek-first'},
		text : false,
		label: "valid start"
	});
	$('#ti_button_valid_start').click(function(){
    	$dialog_tokeninfo_set.html('Format: %d/%m/%y %H:%M<br><input type="hidden" name="info_type" value="validityPeriodStart">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_validityPeriodStart();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_valid_end').button({
		icons: { primary: 'ui-icon-seek-end'},
		text : false,
		label: "valid end"
	});
	$('#ti_button_valid_end').click(function(){
    	$dialog_tokeninfo_set.html('Format: %d/%m/%y %H:%M<br><input type="hidden" name="info_type" value="validityPeriodEnd">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_validityPeriodStart();
        $dialog_tokeninfo_set.dialog('open');
	});
	$('#ti_button_mobile_phone').button({
		icons: { primary: 'ui-icon-signal'},
		text : false,
		label: "mobile phone"
	});
	$('#ti_button_mobile_phone').click(function(){
    	$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="phone">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_phone();
        $dialog_tokeninfo_set.dialog('open');
	});



	/*
	 * time buttons
	 */
	$('#ti_button_time_window').button({
		icons: { primary: 'ui-icon-newwin'},
		text : false,
		label: "time window"
	});
	$('#ti_button_time_window').click(function(){
    	$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="timeWindow">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_timewindow();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_time_shift').button({
		icons: { primary: 'ui-icon-seek-next'},
		text : false,
		label: "time shift"
	});
	$('#ti_button_time_shift').click(function(){
    	$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="timeShift">\
			<input id=info_value name=info_value></input>\
			');
		translate_dialog_ti_timeshift();
        $dialog_tokeninfo_set.dialog('open');
	});

	$('#ti_button_time_step').button({
		icons: { primary: 'ui-icon-clock'},
		text : false,
		label: "time step"
	});
	$('#ti_button_time_step').click(function(){
		$dialog_tokeninfo_set.html('<input type="hidden" name="info_type" value="timeStep">\
			<select id=info_value name=info_value>\
			<option value=30>30 seconds</option>\
			<option value=60>60 seconds</option>\
			</select>');
		translate_dialog_ti_timestep();
        $dialog_tokeninfo_set.dialog('open');
	});

}

function tokenbuttons(){
	/*
	 * This is the function to call handle the buttons, that will only work
	 * with tokens and not with users.
	 */
	$('#button_tokenrealm').button({
        icons: {
            primary: 'ui-icon-home'
        }
    });
    $('#button_getmulti').button({
        icons: {
            primary: 'ui-icon-question'
        }
    });
    $('#button_losttoken').button({
        icons: {
            primary: 'ui-icon-notice'
        }
    });
    $("#button_resync").button({
        icons: {
            primary: 'ui-icon-refresh'
        }
    });
    $('#button_tokeninfo').button({
        icons: {
            primary: 'ui-icon-info'
        }
    });

    var $dialog_losttoken = $('#dialog_lost_token').dialog({
        autoOpen: false,
        title: 'Lost Token',
        resizeable: false,
        width: 400,
        modal: true,
        buttons: {
            'Get temporary token': {click: function(){
                token_losttoken();
                $(this).dialog('close');
            	},
				id: "button_losttoken_ok",
				text: "Get temporary token"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_losttoken_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	tokens = get_selected_tokens();
        	token_string = tokens.join(" ");
        	$('#lost_token_serial').html(token_string);
        	translate_dialog_lost_token();
        	do_dialog_icons();
        }
    });
    $('#button_losttoken').click(function(){
        $dialog_losttoken.dialog('open');
    });

    var $dialog_resync_token = $('#dialog_resync_token').dialog({
        autoOpen: false,
        title: 'Resync Token',
        resizeable: false,
        width: 400,
        modal: true,
        buttons: {
            'Resync': {click: function(){
                token_resync();
                $(this).dialog('close');
            	},
				id: "button_resync_resync",
				text: "Resync"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_resync_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	tokens = get_selected_tokens();
        	token_string = tokens.join(", ");
        	$('#tokenid_resync').html(token_string);
        	translate_dialog_resync_token();
        	do_dialog_icons();
        }
    });
    $('#button_resync').click(function(){
        $dialog_resync_token.dialog('open');
        return false;
    });


    $('#button_tokeninfo').click(function () {
        var tokeninfo = token_info();
        if (false != tokeninfo) {
            $dialog_token_info.html(tokeninfo);
            set_tokeninfo_buttons();
            buttons = {
                Close: {click: function(){
                    $(this).dialog('close');
                	},
					id: "button_ti_close",
					text: "Close"
					}
            };
            $dialog_token_info.dialog('option', 'buttons', buttons);
            $dialog_token_info.dialog('open');
            set_tokeninfo_buttons();
        }
        /* event.preventDefault(); */
       return false;
	}
	);

    $dialog_edit_tokenrealm = $('#dialog_edit_tokenrealm').dialog({
        autoOpen: false,
        title: 'Edit Realms of Token',
        width: 600,
        modal: true,
        maxHeight: 400,
        buttons: {
            'Cancel': { click: function(){
								$(this).dialog('close');
							},
						id: "button_tokenrealm_cancel",
						text: "Cancel"
            },
            'Save': { click: function(){
							save_tokenrealm_config();
							$(this).dialog('close');
							},
					id: "button_tokenrealm_save",
					text: "Save"
            }
        },
        open: function() {
        	do_dialog_icons();
        	translate_dialog_token_realm();
        }
    });

    var $dialog_getmulti = $('#dialog_getmulti').dialog({
        autoOpen: false,
        title: 'Get OTP values',
        resizeable: false,
        width: 400,
        modal: true,
        buttons: {
            'Get OTP values': {click: function(){
				var serial = get_selected_tokens()[0];
				var count  = $('#otp_values_count').val();
				var session = getsession();
				window.open('/gettoken/getmultiotp?serial='+serial+'&session='+session+'&count='+count+'&view=1','getotp_window',"status=1,toolbar=1,menubar=1");
                $(this).dialog('close');
            	},
				id: "button_getmulti_ok",
				text: "Get OTP values"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_getmulti_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	do_dialog_icons();
        	token_string = get_selected_tokens()[0];
        	$('#tokenid_getmulti').html(token_string);
        	translate_dialog_getmulti();
        }
    });
    $('#button_getmulti').click(function(){
        $dialog_getmulti.dialog('open');
    });

    $('#button_tokenrealm').click(function(event){
        tokens = get_selected_tokens();
        token_string = tokens.join(", ");

        // get all realms the admin is allowed to view
        var realms = '';
        $.post('/system/getRealms', {'session':getsession()},
         function(data, textStatus, XMLHttpRequest){
            realms = '<ol id="tokenrealm_select" class="select_list" class="ui-selectable">';
            for (var key in data.result.value) {
                var klass = 'class="ui-widget-content"';
                realms += '<li ' + klass + '>' + key + '</li>';
            }
            realms += '</ol>';

            $('#tokenid_realm').html(token_string);
            $('#realm_name').val(token_string);
            $('#token_realm_list').html(realms);

            $('#tokenrealm_select').selectable({
                stop: function(){
                    g.realms_of_token = Array();
                    $(".ui-selected", this).each(function(){
                        // fill realms of token
                        var index = $("#tokenrealm_select li").index(this);
                        var realm = this.innerHTML;
                        g.realms_of_token.push(realm);

                    }); // end of stop function
                } // end stop function
            }); // end of selectable
        }); // end of $.post
        $dialog_edit_tokenrealm.dialog('open');
        return false;
    });
}

// =================================================================
// =================================================================
// Document ready
// =================================================================
// =================================================================

$(document).ready(function(){
	// right after document loading we need to get the session an reload the realm box!
	getsession();
	//fill_realms();

	$.ajaxSetup({
		error: function(xhr, status, error) {
			if (xhr.status == LOGIN_CODE) {
				alert("Your session has expired!");
				location.reload();
			}
		}
	}
	);

	// hide the javascrip message
	$('#javascript_error').hide();

    $('#do_waiting').overlay({
        top: 10,
        mask: {
            color: '#fff',
            loadSpeed: 100,
            opacity: 0.5
        },
        closeOnClick: true,
        load: true
    });
    hide_waiting();

    $("button").button();

    /*
     $('ul.sf-menu').superfish({
     delay: 0,
     animation: {
     opacity: 'show',
     //    height: 'show'
     },
     speed: 'fast',
     autoArrows: true,
     dropShadows: true
     });
     */
    $('ul.sf-menu').superfish();

    // Button functions
    $('#button_assign').click(function(event){
        token_assign();
        event.preventDefault();
    });

    $('#button_enable').click(function(event){
        token_enable();
        //event.preventDefault();
        return false;
    });

    $('#button_disable').click(function(event){
        token_disable();
        event.preventDefault();
    });

    $('#button_resetcounter').click(function(event){
        token_reset();
        event.preventDefault();
    });

    // Set icons for buttons
    $('#button_enroll').button({
        icons: {
            primary: 'ui-icon-plusthick'
        }
    });
    $('#button_assign').button({
        icons: {
            primary: 'ui-icon-arrowthick-2-e-w'
        }
    });
    $('#button_unassign').button({
        icons: {
            primary: 'ui-icon-arrowthick-1-w'
        }
    });

    $('#button_enable').button({
        icons: {
            primary: 'ui-icon-radio-on'
        }
    });
    $('#button_disable').button({
        icons: {
            primary: 'ui-icon-radio-off'
        }
    });
    $('#button_setpin').button({
        icons: {
            primary: 'ui-icon-pin-s'
        }
    });
    $('#button_delete').button({
        icons: {
            primary: 'ui-icon-trash'
        }
    });

    $('#button_resetcounter').button({
        icons: {
            primary: 'ui-icon-arrowthickstop-1-w'
        }
    });
    $('#button_policy_add').button({
        icons: {
            primary: 'ui-icon-plusthick'
        }
    });
    $('#button_policy_delete').button({
        icons: {
            primary: 'ui-icon-trash'
        }
    });

    disable_all_buttons();

    /*****************************************************************************************
     * Realms editing dialog
     */
    // there's the gallery and the trash
    var $gallery = $('#gallery'), $trash = $('#trash');

    // let the gallery items be draggable
    $('li', $gallery).draggable({
        cancel: 'a.ui-icon',// clicking an icon won't initiate dragging
        revert: 'invalid', // when not dropped, the item will revert back to its initial position
        containment: $('#demo-frame').length ? '#demo-frame' : 'document', // stick to demo-frame if present
        helper: 'clone',
        cursor: 'move'
    });

    // let the trash be droppable, accepting the gallery items
    $trash.droppable({
        accept: '#gallery > li',
        activeClass: 'ui-state-highlight',
        drop: function(ev, ui){
            deleteImage(ui.draggable);
        }
    });

    // let the gallery be droppable as well, accepting items from the trash
    $gallery.droppable({
        accept: '#trash li',
        activeClass: 'custom-state-active',
        drop: function(ev, ui){
            recycleImage(ui.draggable);
        }
    });



    $dialog_edit_realms = $('#dialog_edit_realms').dialog({
        autoOpen: false,
        title: 'Edit Realm',
        width: 600,
        modal: true,
        maxHeight: 400,
        buttons: {
            'Cancel': { click: function(){
							$(this).dialog('close');
						},
						id: "button_editrealms_cancel",
						text: "Cancel"
            },
            'Save': { click: function(){
	                if ($("#form_realmconfig").valid()) {
	                    save_realm_config();
	                    $(this).dialog('close');
	                }
	            },
				id: "button_editrealms_save",
				text: "Save"
			}
        },
        open: function() {
        	translate_dialog_realm_edit();
        	do_dialog_icons();
        }
    });
    jQuery.validator.addMethod("realmname", function(value, element, param){
        return value.match(/^[a-zA-z0-9_\-\.]+$/i);
    }, "Please enter a valid realm name. It may contain characters, numbers and '_-.'.");

	jQuery.validator.addMethod("resolvername", function(value, element, param){
        return value.match(/^[a-zA-z0-9_\-]+$/i);
    }, "Please enter a valid resolver name. It may contain characters, numbers and '_-'.");


    $("#form_realmconfig").validate({
        rules: {
            realm_name: {
                required: true,
                minlength: 4,
                number: false,
                realmname: true
            }
        }
    });

    /**********************************************************************
    * Temporary token dialog
    */
    $dialog_view_temporary_token = $('#dialog_view_temporary_token').dialog({
    	autoOpen: false,
    	resizeable: true,
    	width: 400,
    	modal: false,
    	buttons: {
    		Close: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_view_temporary_token_close",
				text: "Close"
				},
    	},
    	open: function() {
    		translate_dialog_view_temptoken();
    	}
    });
    /***********************************************
     * Special resolver dialogs.
     */
	$dialog_resolver_ask_delete = $('#dialog_resolver_ask_delete').dialog({
            autoOpen: false,
            title: 'Deleting resolver',
            width: 600,
            height: 500,
            modal: true,
            buttons: {
                'Delete': { click: function(){
								resolver_delete();
								$(this).dialog('close');
							},
							id: "button_resolver_ask_delete_delete",
							text: "Delete"
                },
                "Cancel": {
					click: function(){
						$(this).dialog('close');
					},
					id: "button_resolver_ask_delete_cancel",
					text: "Cancel"
				}
            },
            open: function() {
            	do_dialog_icons();
            	translate_dialog_resolver_ask_delete();
            }
        });
	
	$dialog_ask_new_resolvertype = $('#dialog_resolver_create').dialog({
        autoOpen: false,
        title: 'Creating a new UserIdResolver',
        width: 600,
        height: 500,
        modal: true,
        buttons: {
            'Cancel': { click: function(){
                $(this).dialog('close');
				},
				id: "button_new_resolver_type_cancel",
				text: "Cancel"
            },
            'LDAP': { click: function(){
						// calling with no parameter, creates a new resolver
						resolver_ldap("");
						$(this).dialog('close');
					},
					id: "button_new_resolver_type_ldap",
					text: "LDAP"

            },
            'SQL': { click: function(){
					// calling with no parameter, creates a new resolver
					resolver_sql("");
					$(this).dialog('close');
				},
				id: "button_new_resolver_type_sql",
				text: "SQL"
            },
            'SCIM': { click: function(){
					// calling with no parameter, creates a new resolver
					resolver_scim("");
					$(this).dialog('close');
				},
				id: "button_new_resolver_type_scim",
				text: "SCIM"
            },
            'Flatfile': { click: function(){
                // calling with no parameter, creates a new resolver
                resolver_file("");
                $(this).dialog('close');
            },
			id: "button_new_resolver_type_file",
			text: "Flatfile"
			}
        },
        open: function() {
        	translate_dialog_resolver_create();
        	do_dialog_icons();
        }
    });

	$dialog_import_policy = $('#dialog_import_policy').dialog({
        autoOpen: false,
        title: 'Import policy file',
        width: 600,
        modal: true,
        buttons: {
            'import policy file': { click: function(){
            	import_policy('vasco');
                $(this).dialog('close');
            	},
				id: "button_policy_load",
				text: "Import policy file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_policy_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_policy();
        	do_dialog_icons();
        }
    });


    $dialog_ldap_resolver = $('#dialog_ldap_resolver').dialog({
        autoOpen: false,
        title: 'LDAP Resolver',
        width: 600,
        modal: true,
        maxHeight: 500,
        buttons: {
            'Cancel': { click: function(){
                $(this).dialog('close');
            	},
				id: "button_ldap_resolver_cancel",
				text: "Cancel"
				},
            'Save': { click: function(){
	                // Save the LDAP configuration
	                if ($("#form_ldapconfig").valid()) {
	                    save_ldap_config();
	                    //$(this).dialog('close');
	                }
	            },
				id: "button_ldap_resolver_save",
				text: "Save"
			}
        },
        open: function() {
        	do_dialog_icons();
        	ldap_resolver_ldaps();
        }
    });

    $('#button_test_ldap').click(function(event){
        $('#progress_test_ldap').show();

        var url = '/admin/testresolver';
        var params = {"session" : getsession()};
        params['type'] 				= 'ldap';
        params['ldap_uri'] 			= $('#ldap_uri').val();
        params['ldap_basedn'] 		= $('#ldap_basedn').val();
        params['ldap_binddn'] 		= $('#ldap_binddn').val();
        params['ldap_password'] 	= $('#ldap_password').val();
        params['ldap_timeout'] 		= $('#ldap_timeout').val();
        params['ldap_loginattr'] 	= $('#ldap_loginattr').val();
        params['ldap_searchfilter'] = $('#ldap_searchfilter').val();
        params['ldap_userfilter'] 	= $('#ldap_userfilter').val();
        params['ldap_mapping'] 		= $('#ldap_mapping').val();
        params['ldap_sizelimit'] 	= $('#ldap_sizelimit').val();
        params['ldap_uidtype'] 		= $('#ldap_uidtype').val();
        params['ldap_certificate']  = $('#ldap_certificate').val();


        if ($('#ldap_noreferrals').attr('checked')) {
        	params["NOREFERRALS"] = "True";
        }

        clientUrlFetch(url, params, function(xhdr, textStatus) {
			        var resp = xhdr.responseText;
			        var obj = jQuery.parseJSON(resp);
			        $('#progress_test_ldap').hide();
			        if (obj.result.status == true) {
			            result = obj.result.value.result;
			            if (result == "success") {
			                // show number of found users
			                var userarray = obj.result.value.desc;
			                alert_box("LDAP Test", "text_ldap_config_success", userarray.length);
			            }
			            else {
			                alert_box("LDAP Test", obj.result.value.desc);
			            }
			        }
			        else {
			            alert_box("LDAP Test", obj.result.error.message);
			        }
			        return false;
			     });
		return false;
    });
    $('#button_preset_ad').click(function(event){
        $('#ldap_loginattr').val('sAMAccountName');
        $('#ldap_searchfilter').val('(sAMAccountName=*)(objectClass=user)');
        $('#ldap_userfilter').val('(&(sAMAccountName=%s)(objectClass=user))');
        $('#ldap_mapping').val('{ "username": "sAMAccountName", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }');
 		$('#ldap_uidtype').val('DN');
        return false;
    });
    $('#button_preset_ldap').click(function(event){
        $('#ldap_loginattr').val('uid');
        $('#ldap_searchfilter').val('(uid=*)(objectClass=inetOrgPerson)');
        $('#ldap_userfilter').val('(&(uid=%s)(objectClass=inetOrgPerson))');
        $('#ldap_mapping').val('{ "username": "uid", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }');
        $('#ldap_uidtype').val('entryUUID');
        // CKO: we need to return false, otherwise the page will be reloaded!
        return false;
    });
    
    // SCIM resolver
    $dialog_scim_resolver = $('#dialog_scim_resolver').dialog({
        autoOpen: false,
        title: 'SCIM Resolver',
        width: 650,
        heigh: 500,
        modal: true,
        buttons: {
            'Cancel': {click: function(){
                $(this).dialog('close');
            	},
				id: "button_resolver_scim_cancel",
				text: "Cancel"
			},
            'Save': {click: function(){
                // Save the SCIM configuration
                if ($("#form_scimconfig").valid()) {
                    save_scim_config();
                    //$(this).dialog('close');
                }
            	},
				id: "button_resolver_scim_save",
				text: "Save"
			}
        },
        open: do_dialog_icons
    });

    $('#button_test_scim').click(function(event){
        $('#progress_test_scim').show();
        var url = '/admin/testresolver';
        var params = {"session" : getsession()};
        params['type'] = 'scim';
        params['authserver']	= $('#scim_authserver').val();
        params['resourceserver'] = $('#scim_resourceserver').val();
        params['client']	= $('#scim_client').val();
        params['secret']	= $('#scim_secret').val();
        params['map']		= $('#scim_mapping').val();


        clientUrlFetch(url, params, function(xhdr, textStatus) {
			        var resp = xhdr.responseText;
			        var obj = jQuery.parseJSON(resp);
			        $('#progress_test_scim').hide();
			        if (obj.result.status == true) {
			            rows = obj.result.value.rows;
			            if (rows > -1) {
			            	// show number of found users
			            	alert_box("SCIM Test", "text_scim_config_success", rows);
			            } else {
			            	err_string = obj.result.value.err_string;
			            	alert_box("SCIM Test", "text_scim_config_fail", err_string);
			            }
			        } else {
			            alert_box("SCIM Test", obj.result.error.message);
			        }
			        return false;
			     });
		return false;
    });
    
    
    
    // SQL resolver
    $dialog_sql_resolver = $('#dialog_sql_resolver').dialog({
        autoOpen: false,
        title: 'SQL Resolver',
        width: 650,
        heigh: 500,
        modal: true,
        buttons: {
            'Cancel': {click: function(){
                $(this).dialog('close');
            	},
				id: "button_resolver_sql_cancel",
				text: "Cancel"
			},
            'Save': {click: function(){
                // Save the SQL configuration
                if ($("#form_sqlconfig").valid()) {
                    save_sql_config();
                    //$(this).dialog('close');
                }
            	},
				id: "button_resolver_sql_save",
				text: "Save"
			}
        },
        open: do_dialog_icons
    });

    $('#button_test_sql').click(function(event){
        $('#progress_test_sql').show();
        var url = '/admin/testresolver';
        var params = {"session" : getsession()};
        params['type'] = 'sql';
        params['sql_driver']	= $('#sql_driver').val();
        params['sql_user']		= $('#sql_user').val();
        params['sql_password']	= $('#sql_password').val();
        params['sql_server']	= $('#sql_server').val();
        params['sql_port']		= $('#sql_port').val();
        params['sql_database']	= $('#sql_database').val();
        params['sql_table']		= $('#sql_table').val();
        params['sql_where']		= $('#sql_where').val();
        params['sql_conparams']	= $('#sql_conparams').val();
        params['sql_encoding']	= $('#sql_encoding').val();

        clientUrlFetch(url, params, function(xhdr, textStatus) {
			        var resp = xhdr.responseText;
			        var obj = jQuery.parseJSON(resp);
			        $('#progress_test_sql').hide();
			        if (obj.result.status == true) {
			            rows = obj.result.value.rows;
			            if (rows > -1) {
			            	// show number of found users
			            	alert_box("SQL Test", "text_sql_config_success", rows);
			            } else {
			            	err_string = obj.result.value.err_string;
			            	alert_box("SQL Test", "text_sql_config_fail", err_string);
			            }
			        } else {
			            alert_box("SQL Test", obj.result.error.message);
			        }
			        return false;
			     });
		return false;
    });

    $('#button_preset_sql_wordpress').click(function(event){
        $('#sql_table').val('wp_users');
        $('#sql_mapping').val('{ "userid" : "ID", "username": "user_login", ' +
        '"email" : "user_email", "givenname" : "display_name", "password" : "user_pass" }');
        return false;
    });
    
    $('#button_preset_sql_otrs').click(function(event){
        $('#sql_table').val('users');
        $('#sql_mapping').val('{ "userid" : "id", "username": "login", ' +
        '"givenname" : "first_name", "surname" : "last_name", "password" : "pw" }');
        return false;
    });
    
    $('#button_preset_sql_owncloud').click(function(event){
        $('#sql_table').val('oc_users');
        $('#sql_mapping').val('{ "userid" : "uid", "username": "uid", ' +
        '"givenname" : "displayname", "password" : "password" }');
        return false;
    });
    
    $('#button_preset_sql_tine20').click(function(event){
    	//alert_info_text("text_preset_sql");
    	alert_box("title_preset_sql", "text_preset_sql");
        $('#sql_table').val('tine20_accounts');
        $('#sql_mapping').val('{ "userid" : "id", "username": "login_name", ' +
        '"email" : "email", ' +
        '"givenname" : "first_name", "surname" : "last_name", "password" : "password" }');
        return false;
    });

	// FILE resolver
    $dialog_file_resolver = $('#dialog_file_resolver').dialog({
        autoOpen: false,
        title: 'File Resolver',
        width: 600,
        modal: true,
        maxHeight: 500,
        buttons: {
            'Cancel': {click: function(){
                $(this).dialog('close');
            	},
				id: "button_resolver_file_cancel",
				text: "Cancel"
				},
            'Save': {click: function(){
                // Save the File configuration
                if ($("#form_fileconfig").valid()) {
                    save_file_config();
                    //$(this).dialog('close');
                }
            	},
				id: "button_resolver_file_save",
				text: "Save"
			}
        },
        open: do_dialog_icons
    });


    $dialog_resolvers = $('#dialog_resolvers').dialog({
        autoOpen: false,
        title: 'Resolvers',
        width: 600,
        height: 500,
        modal: true,
        buttons: {
            'New': { click:  function(){
		                resolver_new_type();
		                resolvers_load();
						},
					id: "button_resolver_new",
					text: "New"
            },
            'Edit': { click: function(){
                			resolver_edit_type();
                			resolvers_load();
							},
						id:"button_resolver_edit",
						text: "Edit"
            },
            'Delete': { click: function(){
                			resolver_ask_delete();
                			resolvers_load();
							},
						id: "button_resolver_delete",
						text:"Delete"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
                			var realms = get_realms();
            				if (realms.length == 0) {
            					$('#text_no_realm').dialog('open');
            				}
						},
						id: "button_resolver_close",
						text:"Close"
            }
        },
        open: function(){
        	translate_dialog_resolvers();
        	do_dialog_icons();
        }
    });
    $('#menu_edit_resolvers').click(function(){
        resolvers_load();
        $dialog_resolvers.dialog('open');
        $('#button_resolver_new').focus();
    });


    /**************************************************
     *  Tools
     */
    $dialog_tools_getserial = create_tools_getserial_dialog();
    $('#menu_tools_getserial').click(function(){
    	_fill_realms($('#tools_getserial_realm'),1);
        $dialog_tools_getserial.dialog('open');
    });

    $dialog_tools_copytokenpin = create_tools_copytokenpin_dialog();
    $('#menu_tools_copytokenpin').click(function(){
    	//_fill_realms($('#tools_getserial_realm'),1)
        $dialog_tools_copytokenpin.dialog('open');
    });

	$dialog_tools_checkpolicy = create_tools_checkpolicy_dialog();
	$('#menu_tools_checkpolicy').click(function(){
        $dialog_tools_checkpolicy.dialog('open');
        $('#cp_allowed').hide();
   		$('#cp_forbidden').hide();
   		$('#cp_policy').html("");
    });

    $dialog_tools_exporttoken = create_tools_exporttoken_dialog();
	$('#menu_tools_exporttoken').click(function(){
        $dialog_tools_exporttoken.dialog('open');
    });

    $dialog_tools_exportaudit = create_tools_exportaudit_dialog();
	$('#menu_tools_exportaudit').click(function(){
        $dialog_tools_exportaudit.dialog('open');
    });

    /************************************************************
     * Enrollment Dialog with response url
     *
     */

    $dialog_show_enroll_url = $('#dialog_show_enroll_url').dialog({
    	autoOpen: false,
    	title: 'token enrollment',
    	width: 750,
    	modal: false,
    	buttons: {
    		'OK': {click:function() {
    				$(this).dialog('close');
    				view_setpin_after_enrolling([$('#enroll_token_serial').val()]);
    			},
    			id: "button_show_enroll_ok",
    			text: "Ok"
    		}
    	},
    	open: function() {
    		translate_dialog_show_enroll_url();
    	}
    });
    /************************************************************
     * Realm Dialogs
     *
     */
	$dialog_realm_ask_delete = $('#dialog_realm_ask_delete').dialog({
        autoOpen: false,
        title: 'Deleting realm',
        width: 600,
        modal: true,
        buttons: {
            'Delete': {click: function(){
                $(this).dialog('close');
                show_waiting();
                realm_delete();
            	},
				id: "button_realm_ask_delete_delete",
				text: "Delete"
			},
            Cancel: {click:function(){
                $(this).dialog('close');
            	},
				id: "button_realm_ask_delete_cancel",
				text: "Cancel"
			}
        },
        open: function() {
        	do_dialog_icons();
        	translate_dialog_realm_ask_delete();
        }
    });

    $dialog_realms = $('#dialog_realms').dialog({
        autoOpen: false,
        title: 'Realms',
        width: 600,
        height: 500,
        modal: true,
        buttons: {
            'New': { click: function(){
                realm_edit('');
                realms_load();
                fill_realms();
            	},
				id: "button_realms_new",
				text: "New"
				},
            'Edit': { click: function(){
                realm_edit(g.realm_to_edit);
                realms_load();
                fill_realms();
            	},
				id: "button_realms_edit",
				text: "Edit"
				},
            'Delete': {click: function(){
                realm_ask_delete();
                realms_load();
                fill_realms();
            	},
				id: "button_realms_delete",
				text: "Delete"
				},
            'Close': { click: function(){
                $(this).dialog('close');
            	},
				id: "button_realms_close",
				text: "Close"
				},
            'Set Default': {click: function(){
                var realm = "";
                if (g.realm_to_edit.match(/^(\S+)\s\[(.+)\]/)) {
                    realm = g.realm_to_edit.replace(/^(\S+)\s+\[(.+)\]/, "$1");
                    $.post('/system/setDefaultRealm', {
                      'realm' : realm,
                      'session':getsession()},
                     function(){
                        realms_load();
                        fill_realms();
                    });
                }
                else if (g.realm_to_edit.match(/^\S+\s+\(Default\)\s+\[.+\]/)) {
                	alert_info_text("text_already_default_realm", "", ERROR);
                }
                else {
                    alert_info_text("text_realm_regexp_error", "", ERROR);
                }
            	},
				id: "button_realms_setdefault",
				text:"Set Default"
				},
            'Clear Default': {click: function(){
                $.post('/system/setDefaultRealm', {'session':getsession()},
                 function(){
                    realms_load();
                    fill_realms();
                });
            	},
				id: "button_realms_cleardefault",
				text: "Clear Default"
				}
        },
        open: function(){
        	translate_dialog_realms();
        	do_dialog_icons();
        }
    });
    $('#menu_edit_realms').click(function(){
        realms_load();
        $dialog_realms.dialog('open');
    });

    /*********************************************************************
     * Token config
     */

	var $tokenConfigCallbacks = {};
	var $tokenConfigInbacks = {};


    var $dialog_token_config = $('#dialog_token_settings').dialog({
        autoOpen: false,
        title: 'Token Config',
        width: 600,
        modal: true,
        buttons: {
            'Save config': {
                click: function(){
                    var validation_fails = "";
                    $('#dialog_token_settings').find('form').each(
                        function( index ) {
                            var valid = $(this).valid();
                            if (valid != true) {
                                formName = $(this).find('legend').text();
                                if (formName.length == 0) {
                                    formName = $(this).find('label').first().text();
                                }
                                validation_fails = validation_fails +
                                            "<li>" + formName.trim() +"</li>";
                            }
                        }
                    );
                    if (validation_fails.length > 0) {
                        alert_box("text_form_validation_error_title",
                            "text_form_validation_error1", validation_fails);
                    }
                    else
                    {
                        save_token_config();
                        $(this).dialog('close');
                    }
                },
				id: "button_token_save",
				text:"Save Token config"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_token_cancel",
				text: "Cancel"
				}
        },
        open: function(event, ui) {
        	do_dialog_icons();
        	translate_token_settings();
        }
    });
    $('#tab_token_settings').tabs();



    /*********************************************************************
     * System config
     */

    var $dialog_system_config = $('#dialog_system_settings').dialog({
        autoOpen: false,
        title: 'System config',
        width: 600,
        modal: true,
        buttons: {
            'Save config': {click: function(){
                if ($("#form_sysconfig").valid()) {
                    save_system_config();
                    $(this).dialog('close');
                } else {
                	alert_box("", "text_error_saving_system_config");
                }
            	},
				id: "button_system_save",
				text:"Save config"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_system_cancel",
				text: "Cancel"
				}
        },
        open: function(event, ui) {
        	do_dialog_icons();
        	translate_system_settings();
        }
    });
    $('#tab_system_settings').tabs();

    $("#form_sysconfig").validate({
        rules: {
            sys_maxFailCount: {
                required: true,
                minlength: 2,
                number: true
            },
            sys_countWindow: {
                required: true,
                minlength: 2,
                number: true
            },
            sys_syncWindow: {
                required: true,
                minlength: 3,
                number: true
            },
            sys_otpLen: {
                required: true,
                minlength: 1,
                maxlength: 1,
                number: true
            }
        }
    });

    $('#menu_system_config').click(function(){
        load_system_config();
        $dialog_system_config.dialog('open');
    });

    $('#menu_token_config').click(function(){
    try {
          load_token_config();
          $dialog_token_config.dialog('open');
        } catch (error) {
          alert_box('', "text_catching_generic_error", error);
        }
    });


    $('#menu_policies').click(function(){
        $('#tabs').tabs('select', 2);
    });

    
    /**********************************************************************
     * loading token file
     */

    var $dialog_load_tokens_pskc  = create_pskc_dialog();
    var $dialog_load_tokens_vasco = create_vasco_dialog();
    var $dialog_load_tokens_feitian = create_feitian_dialog();
    var $dialog_load_tokens_dpw = create_dpw_dialog();
    var $dialog_load_tokens_dat = create_dat_dialog();
    var $dialog_load_tokens_aladdin = create_aladdin_dialog();
    var $dialog_load_tokens_oathcsv = create_oathcsv_dialog();
    var $dialog_load_tokens_yubikeycsv = create_yubikeycsv_dialog();

    $('#menu_load_aladdin_xml_tokenfile').click(function(){
        $dialog_load_tokens_aladdin.dialog('open');
    });
    $('#menu_load_oath_csv_tokenfile').click(function(){
    	 $dialog_load_tokens_oathcsv.dialog('open');
    });
    $('#menu_load_yubikey_csv_tokenfile').click(function(){
    	 $dialog_load_tokens_yubikeycsv.dialog('open');
    });
    $('#menu_load_feitian').click(function(){
        $dialog_load_tokens_feitian.dialog('open');
    });
    $('#menu_load_pskc').click(function(){
        $dialog_load_tokens_pskc.dialog('open');
    });
	$('#menu_load_dpw').click(function(){
		$dialog_load_tokens_dpw.dialog('open');
	});
    $('#menu_load_dat').click(function(){
        $dialog_load_tokens_dat.dialog('open');
    });
	$('#menu_load_vasco').click(function(){
		$dialog_load_tokens_vasco.dialog('open');
	});


	/***********************************************************************
	 *  Alert dialog
	 */
	$('#dialog_alert').dialog({
		autoOpen: false,
		open: function(){

		},
		modal: true,
        buttons: {
            'OK': {click: function(){
                $(this).dialog('close');
            	},
				id: "button_alert_ok",
				text: "OK"
				}
        }
	});

    /*******************************************************
     * Enrolling tokens
     */
	function button_enroll(){

		init_$tokentypes();
        try {
            tokentype_changed();
        } catch (error) {
            alert_box('', "text_catching_generic_error", error);
            return false;
        }
	    // ajax call  w. callback//
	    get_enroll_infotext();
	    translate_token_enroll();
	  	$dialog_enroll_token.dialog('open');

	    return false;
	}
    var $dialog_enroll_token = $('#dialog_token_enroll').dialog({
        autoOpen: false,
        title: 'Enroll token',
        resizeable: false,
        width: 600,
        modal: true,
        buttons: {
            'Enroll': {click: function(){
                token_enroll();
                $(this).dialog('close');
            	},
				id: "button_enroll_enroll",
				text: "Enroll"
				},
            Cancel: { click: function(){
                $(this).dialog('close');
            	},
				id: "button_enroll_cancel",
				text: "Cancel"
				}
        },
        open: do_dialog_icons
    });

    $('#button_enroll').click(button_enroll);
   //jQuery(document).bind('keydown', 'Alt+e', button_enroll());



    $('#realms').change(function(){
        var new_realm = $('#realm').val();
        $('#user_table').flexOptions({
            params: [{
                name: 'realm',
                value: new_realm
            }]
        });
        $('#user_table').flexReload();
    });

    $dialog_setpin_token = $('#dialog_set_pin').dialog({
        autoOpen: false,
        title: 'Set PIN',
        resizeable: false,
        width: 400,
        modal: true,
        buttons: {
            'Set PIN': {click: function(){
                token_setpin();
                $(this).dialog('close');
            	},
				id: "button_setpin_setpin",
				text: "Set PIN"
				},
            Cancel: { click: function(){
                $(this).effect('puff');
                $(this).dialog('close');
            	},
				id: "button_setpin_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	translate_set_pin();
        	do_dialog_icons();
        }
    });

    $('#button_setpin').click(function(){
        tokens = get_selected_tokens();
        view_setpin_dialog(tokens);
        return false;
    });

    var $dialog_unassign_token = $('#dialog_unassign_token').dialog({
        autoOpen: false,
        title: 'Unassign selected tokens?',
        resizable: false,
        width: 400,
        modal: true,
        buttons: {
            'Unassign tokens': {click: function(){
                token_unassign();
                $(this).dialog('close');
            	},
				id: "button_unassign_unassign",
				text: "Unassign tokens"
				},
            Cancel: { click: function(){
                $(this).dialog('close');
            	},
				id: "button_unassign_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	do_dialog_icons();
        	translate_dialog_unassign();
        	tokens = get_selected_tokens();
       		token_string = tokens.join(", ");
       		$('#tokenid_unassign').html(token_string);
        }
    });
    $('#button_unassign').click(function(){
        $dialog_unassign_token.dialog('open');
        return false;
    });


    var $dialog_delete_token = $('#dialog_delete_token').dialog({
        autoOpen: false,
        title: 'Delete selected tokens?',
        resizable: false,
        width: 400,
        modal: true,
        buttons: {
            'Delete tokens': {click: function(){
                token_delete();
                $(this).dialog('close');
            	},
				id: "button_delete_delete",
				text: "Delete tokens"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_delete_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	tokens = get_selected_tokens();
        	$('#delete_info').html( tokens.join(", "));
        	translate_dialog_delete_token();
        	do_dialog_icons();
        }
    });
    $('#button_delete').click(function(){
        $dialog_delete_token.dialog('open');
        return false;
    });

    $( "#alert_box" ).dialog({
    	autoOpen: false,
        modal: true,
        buttons: {
                Ok: function() {
                    $( this ).dialog( "close" );
                }
            }
     });

     $('#text_no_realm').dialog({
     	autoOpen: false,
     	modal: true,
     	show: {
     		effect : "fade",
     		duration: 1000
     	},
     	hide: {
     		effect : "fade",
     		duration: 500
     	},
     	buttons: {
     		Ok: function() {
     			$(this).dialog("close");
     			$dialog_realms.dialog("open");
     		}
     	}
     });


    /******************************************************************+
     *
     * Tabs
     */
    $("#tabs").tabs({
        ajaxOptions: {
            error: function(xhr, status, index, anchor){
          		if (xhr.status == LOGIN_CODE) {
					alert("Your session has expired!");
					location.reload();
				} else {
					$(anchor.hash).html("Couldn't load this tab. Please respond to the administrator:" + xhr.statusText + " (" + xhr.status + ")");
				}
            }
        },
        collapsible: false,
        spinner: 'Retrieving data...',
        cache: true,
        //load: function(event, ui){
        //    get_selected();
        //}
    });

    /**********************************************************************
     * Token info dialog
     */
    $dialog_tokeninfo_set = $('#dialog_tokeninfo_set').dialog({
        autoOpen: false,
        title: "Setting Hashlib",
        resizeable: true,
        width: 400,
        modal: true,
        buttons: {
            OK: {click: function(){
                token_info_save();
                $(this).dialog('close');
            	},
				id: "button_tokeninfo_ok",
				text: "OK"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_tokeninfo_cancel",
				text: "Cancel"
				}
        }
    });
    $dialog_tokeninfo_set.html('<select id=hashlib name=hashlib>\
					<option value=sha1>sha1</option>\
					<option value=sha256>sha256</option>\
					</select>');

    $dialog_token_info = $('#dialog_token_info').dialog({
        autoOpen: false,
        title: 'Token info',
        resizeable: true,
        width: 720,
        modal: true,
        open: function(){
        	translate_dialog_token_info();
        	do_dialog_icons();
        }
    });


    fill_realms();

    //$("#token_table").flexigrid();
    //$("#user_table").flexigrid();
	//$("#audit_table").flexigrid();

    // Log Div
    $("#logAccordion").accordion({
        fillSpace: true
    });
    /*
     $("#logAccordionResizer").resizable({
     resize: function(){
     $("#accordion").accordion("resize");
     },
     minHeight: 60
     });
     */

	$('#do_waiting').click(reset_waiting());

});
//--------------------------------------------------------------------------------------
// End of document ready


/************************************************************************
 *
 *  Resolver edit funtions
 */
function resolver_file(name){

    var obj = {
        'result': {
            'value': {
                'data': {
                    'fileName': '/etc/passwd'
                }
            }
        }
    };
    if (name) {
        // load the config of the resolver "name".
        clientUrlFetch('/system/getResolver',{'resolver' : name, "session" : getsession()}, function(xhdr, textStatus) {

		    	var resp = xhdr.responseText;
		        obj = jQuery.parseJSON(resp);
		        //obj.result.value.data.fileName;

			    $('#file_resolvername').val(name);
			    $('#file_filename').val(obj.result.value.data.fileName);
    	});
	} else {
		$('#file_resolvername').val("");
		$('#file_filename').val(obj.result.value.data.fileName);
	}

	$dialog_file_resolver.dialog('open');

    $("#form_fileconfig").validate({
        rules: {
            file_filename: {
                required: true,
                minlength: 2,
                number: false
            },
            file_resolvername: {
                required: true,
                minlength: 4,
                number: false,
				resolvername: true
            }
        }
	});
}



function realm_edit(name){
    var realm = "";
    var html_intro;
    $('#realm_intro_edit').hide();
    $('#realm_intro_new').hide();
    if (name) {
        if (name.match(/^(\S+)\s(\[|\()(.+)\]/)) {
            realm = name.replace(/^(\S+)\s+(\[|\()(.+)\]/, "$1");
        }
        else {
            alert_info_text("text_realm_name_error", "", ERROR);
        }
        $('#realm_edit_realm_name').html(realm);
        $('#realm_name').val(realm);
        $('#realm_intro_edit').show();
    }
    else {
    	$('#realm_intro_new').show();
    }

    var uidresolvers = [];
    var default_realm = "";

    if (realm) {
    	// We are doing a realm edit, so we get the realm information.
    	// get the realm configuration
	    var resp = clientUrlFetchSync('/system/getRealms',{"session" : getsession()});
    	var realmObj = jQuery.parseJSON(resp);
        uidresolvers = realmObj.result.value[realm].useridresolver;
    }

    // get all resolvers - also for a new realm
    var resolvers = '';
    $.post('/system/getResolvers', {'session':getsession()},
     function(data, textStatus, XMLHttpRequest){
        resolvers = '<ol id="resolvers_in_realms_select" class="select_list" class="ui-selectable">';
        for (var key in data.result.value) {
            var klass = 'class="ui-widget-content"';
            for (var i_reso in uidresolvers) {
                // check if this resolver is contained in the realm
                var reso = uidresolvers[i_reso].split('.');
                if (reso[reso.length - 1] == key) {
                    klass = 'class="ui-selected" class="ui-widget-content" ';
                }
            }
			var id = "id=realm_edit_click_" + key;
            resolvers += '<li '+id+' '+ klass + '>' + key + ' [' + data.result.value[key].type + ']</li>';
        }
        resolvers += '</ol>';

        $('#realm_edit_resolver_list').html(resolvers);
        $('#resolvers_in_realms_select').selectable({
            stop: function(){
                g.resolvers_in_realm_to_edit = '';
                $(".ui-selected", this).each(function(){
                    // also nur den resolvers-string zusammenbauen...
                    if (g.resolvers_in_realm_to_edit) {
                        g.resolvers_in_realm_to_edit += ',';
                    }
                    var index = $("#resolvers_in_realms_select li").index(this);
                    var reso = this.innerHTML;
                    if (reso.match(/(\S+)\s\[(\S+)\]/)) {
                        var r = reso.replace(/(\S+)\s+\S+/, "$1");
                        var t = reso.replace(/\S+\s+\[(\S+)\]/, "$1");
                    }
                    else {
                        alert_info_text("text_regexp_error", reso, ERROR);
                    }
                    switch (t) {
                        case 'ldapresolver':
                            g.resolvers_in_realm_to_edit += 'privacyidea.lib.resolvers.LDAPIdResolver.IdResolver.' + r;
                            break;
                        case 'sqlresolver':
                            g.resolvers_in_realm_to_edit += 'privacyidea.lib.resolvers.SQLIdResolver.IdResolver.' + r;
                            break;
                        case 'passwdresolver':
                            g.resolvers_in_realm_to_edit += 'privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.' + r;
                            break;
                        case 'scimresolver':
                            g.resolvers_in_realm_to_edit += 'privacyidea.lib.resolvers.SCIMIdResolver.IdResolver.' + r;
                            break;
                    }
                }); // end of each
            } // end of stop function
        }); // end of selectable
    }); // end of $.post
    $dialog_edit_realms.dialog("option", "title", "Edit Realm " + realm);
    $dialog_edit_realms.dialog('open');

    jQuery.validator.addMethod("realmname", function(value, element, param){
        return value.match(/^[a-zA-Z0-9_\-\.]+$/i);
    }, "Please enter a valid realm name. It may contain characters, numbers and '_-.'.");


    $("#form_realmconfig").validate({
        rules: {
            realm_name: {
                required: true,
                minlength: 4,
                number: false,
                realmname: true
            }
        }
    });
}

function resolver_set_ldap(obj) {
	$('#ldap_uri').val(obj.result.value.data.LDAPURI);
    $('#ldap_basedn').val(obj.result.value.data.LDAPBASE);
    $('#ldap_binddn').val(obj.result.value.data.BINDDN);
    $('#ldap_password').val(obj.result.value.data.BINDPW);
    $('#ldap_timeout').val(obj.result.value.data.TIMEOUT);
	$('#ldap_sizelimit').val(obj.result.value.data.SIZELIMIT);
    $('#ldap_loginattr').val(obj.result.value.data.LOGINNAMEATTRIBUTE);
    $('#ldap_searchfilter').val(obj.result.value.data.LDAPSEARCHFILTER);
    $('#ldap_userfilter').val(obj.result.value.data.LDAPFILTER);
    $('#ldap_mapping').val(obj.result.value.data.USERINFO);
    $('#ldap_uidtype').val(obj.result.value.data.UIDTYPE);
    $('#ldap_certificate').val(obj.result.value.data.CACERTIFICATE);
    $('#ldap_noreferrals').val(obj.result.value.data.NOREFERRALS);
    ldap_resolver_ldaps();
}

function resolver_ldap(name){
    var obj = {
        'result': {
            'value': {
                'data': {
                    'BINDDN': 'cn=administrator,dc=yourdomain,dc=tld',
                    'LDAPURI': 'ldap://privacyideaserver1, ldap://privacyideaserver2',
                    'LDAPBASE': 'dc=yourdomain,dc=tld',
                    'TIMEOUT': '5',
					'SIZELIMIT' : '500',
                    'LOGINNAMEATTRIBUTE': 'sAMAccountName',
                    'LDAPSEARCHFILTER': '(sAMAccountName=*)(objectClass=user)',
                    'LDAPFILTER': '(&(sAMAccountName=%s)(objectClass=user))',
                    'USERINFO': '{ "username": "sAMAccountName", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }',
                    'CACERTIFICATE' : '',
                    'NOREFERRALS' : 'True',
                }
            }
        }
    };


    if (name) {
        // load the config of the resolver "name".
        clientUrlFetch('/system/getResolver', {'resolver' : name, "session" : getsession()}, function(xhdr, textStatus) {
	     	var resp = xhdr.responseText;
	        var obj = jQuery.parseJSON(resp);
			$('#ldap_resolvername').val(name);
			if (obj.result.status) {
				resolver_set_ldap(obj);
			} else {
				// error reading resolver
				alert_box("", "text_ldap_load_error", obj.result.error.message);
			}

		  });
	} // end if
	else {
		$('#ldap_resolvername').val("");
		resolver_set_ldap(obj);
	}
	$('#ldap_noreferrals').attr('checked', ("True" == obj.result.value.data.NOREFERRALS));

    $('#progress_test_ldap').hide();
    $dialog_ldap_resolver.dialog('open');

    jQuery.validator.addMethod("ldap_uri", function(value, element, param){
        return value.match(param);
    }, "Please enter a valid ldap uri. It needs to start with ldap:// or ldaps://");

    jQuery.validator.addMethod("resolvername", function(value, element, param){
        return value.match(/^[a-z0-9_\-]+$/i);
    }, "Please enter a valid resolver name. It may contain characters, numbers and '_-'.");

    // LDAPSEARCHFILTER: "(sAMAccountName=*)(objectClass=user)"
    jQuery.validator.addMethod("ldap_searchfilter", function(value, element, param){
        return value.match(/(\(\S+=\S+\))+/);
    }, "Please enter a valid searchfilter like this: (sAMAccountName=*)(objectClass=user)");

    // LDAPFILTER: "(&(sAMAccountName=%s)(objectClass=user))"
    jQuery.validator.addMethod("ldap_userfilter", function(value, element, param){
        return value.match(/\(\&(\(\S+=\S+\))+\)/);
    }, "Please enter a valid searchfilter like this: (&(sAMAccountName=%s)(objectClass=user))");

    jQuery.validator.addMethod("ldap_mapping", function(value, element, param){
        return value.match(/{.+}/);
    }, 'Please enter a valid searchfilter like this: \
		{ "username": "sAMAccountName", "phone" : "telephoneNumber", "mobile" \
		: "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }');
    jQuery.validator.addMethod("ldap_uidtype", function(value,element,param){
    	return value.match(/.*/);
    }, 'Please enter the UID of your LDAP server like DN, entryUUID, objectGUID or GUID'
    );
    $("#form_ldapconfig").validate({
        rules: {
            ldap_uri: {
                required: true,
                minlength: 8,
                number: false,
                ldap_uri: /^(ldap:\/\/|ldaps:\/\/)/i
            },
            ldap_timeout: {
                required: true,
                minlength: 1,
                number: true
            },
            ldap_resolvername: {
                required: true,
                minlength: 4,
                resolvername: true
            },
            ldap_searchfilter: {
                required: true,
                minlength: 5,
                ldap_searchfilter: true
            },
            ldap_userfilter: {
                required: true,
                minlength: 5,
                ldap_userfilter: true
            },
            ldap_mapping: {
                required: true,
                minlength: 5,
                ldap_mapping: true
            },
            ldap_uidtype: {
            	ldap_uidtype: true
            }
        }
    });

}

function resolver_set_scim(obj) {
    $('#scim_authserver').val(obj.result.value.data.authserver);
    $('#scim_resourceserver').val(obj.result.value.data.resourceserver);
    $('#scim_client').val(obj.result.value.data.client);
    $('#scim_secret').val(obj.result.value.data.secret);
    $('#scim_mapping').val(obj.result.value.data.mapping);
}

function resolver_scim(name){
	// the function that is called to fill the resolver dialog
	var obj = { 'result' : {
		'value' : {
			'data' : {
				"authserver" : 'http://osiam:8080/osiam-auth-server',
    			"resourceserver" : 'http://osiam:8080/osiam-resource-server',
    			"client" : "your.server.name",
				"secret" : '40e919e3-0834-447a-b39c-d14329c99941',
				'mapping' : '{ "username" : "userName" , "userid" : "id"}'
			}
		}	
	}
	};

    $('#progress_test_scim').hide();

    if (name) {
        // load the config of the resolver "name".
        clientUrlFetch('/system/getResolver', {'resolver' : name, "session" : getsession()}, function(xhdr, textStatus) {
		        var resp = xhdr.responseText;
		        var obj = jQuery.parseJSON(resp);
		        //obj.result.value.data.BINDDN;
    			$('#scim_resolvername').val(name);
    			if (obj.result.status) {
					resolver_set_scim(obj);
				} else {
					// error reading resolver
					alert_box("", "text_scim_load_error", obj.result.error.message);
				}
			});
		} // end if
	else {
		$('#scim_resolvername').val("");
		resolver_set_scim(obj);
	}

    $dialog_scim_resolver.dialog('open');

    jQuery.validator.addMethod("resolvername", function(value, element, param){
        return value.match(/^[a-zA-Z0-9_\-]+$/i);
    }, "Please enter a valid resolver name. It may contain characters, numbers and '_-'.");

    jQuery.validator.addMethod("scim_mapping", function(value, element, param){
        return value.match(/{.+}/);
    }, 'Please enter a valid SCIM Mapping like this: \
    	{ "username" : "userName" , "userid" : "id"}');

    $("#form_scimconfig").validate({
        rules: {
            scim_resolvername: {
                required: true,
                minlength: 4,
                resolvername: true
            },
            //scim_authserver: {
            //	url: true
            //},
            //scim_resourceserver: {
            //	url: true
            //},
            scim_mapping: {
                required: true,
                minlength: 5,
                scim_mapping: true
            }
        }
    });

}  // End of resolver_scim

function resolver_set_sql(obj) {

    $('#sql_driver').val(obj.result.value.data.Driver);
    $('#sql_server').val(obj.result.value.data.Server);
    $('#sql_port').val(obj.result.value.data.Port);
    $('#sql_limit').val(obj.result.value.data.Limit);
    $('#sql_database').val(obj.result.value.data.Database);
    $('#sql_table').val(obj.result.value.data.Table);
    $('#sql_user').val(obj.result.value.data.User);
    $('#sql_password').val(obj.result.value.data.Password);
    $('#sql_mapping').val(obj.result.value.data.Map);
    $('#sql_where').val(obj.result.value.data.Where);
    $('#sql_conparams').val(obj.result.value.data.conParams);
    $('#sql_encoding').val(obj.result.value.data.Encoding);
}

function resolver_sql(name){
    var obj = {
        'result': {
            'value': {
                'data': {
                    'Database': 'yourUserDB',
                    'Driver': 'mysql',
                    'Server': '127.0.0.1',
                    'Port': '3306',
                    'User': 'user',
                    'Password': 'secret',
                    'Table': 'usertable',
                    'Map': '{ "userid" : "id", "username": "user", "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" ,"password" : "password"}',
                    'Where' : '',
                    'conParams' : '',
                    'Encoding' : ''

                }
            }
        }
    };

    $('#progress_test_sql').hide();

    if (name) {
        // load the config of the resolver "name".
        clientUrlFetch('/system/getResolver', {'resolver' : name, "session" : getsession()}, function(xhdr, textStatus) {
		        var resp = xhdr.responseText;
		        var obj = jQuery.parseJSON(resp);
		        //obj.result.value.data.BINDDN;
    			$('#sql_resolvername').val(name);
    			if (obj.result.status) {
					resolver_set_sql(obj);
				} else {
					// error reading resolver
					alert_box("", "text_sql_load_error", obj.result.error.message);
				}
			});
		} // end if
	else {
		$('#sql_resolvername').val("");
		resolver_set_sql(obj);
	}

    $dialog_sql_resolver.dialog('open');

    jQuery.validator.addMethod("resolvername", function(value, element, param){
        return value.match(/^[a-zA-Z0-9_\-]+$/i);
    }, "Please enter a valid resolver name. It may contain characters, numbers and '_-'.");

    jQuery.validator.addMethod("sql_driver", function(value, element, param){
        return value.match(/(mysql)|(postgres)|(mssql)|(oracle)|(sqlite)|(ibm_db_sa\+pyodbc)/);
    }, "Please enter a valid driver specification like: mysql, postgres, mssql, oracle, sqlite or ibm_db_sa+pyodbc");

    jQuery.validator.addMethod("sql_mapping", function(value, element, param){
        return value.match(/{.+}/);
    }, 'Please enter a valid searchfilter like this: \
		{ "username": "usercolumn", "password":"pw", "salt": "salt", "phone" : "telephoneNumber", "mobile" \
		: "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }');

    $("#form_sqlconfig").validate({
        rules: {
            sql_resolvername: {
                required: true,
                minlength: 4,
                resolvername: true
            },
            sql_driver: {
                required: true,
                minlength: 3,
                number: false,
                sql_driver: true
            },
            sql_port: {
                minlength: 1,
                number: true
            },
            sql_limit: {
                minlength: 1,
                number: true
            },
            sql_mapping: {
                required: true,
                minlength: 5,
                sql_mapping: true
            }
        }
    });
}

function split( val ) {
		return val.split( /,\s*/ );
}
function extractLast( term ) {
		return split( term ).pop();
}

function renew_policy_actions(){
	/*
	 * This function needs to be called, whenever the scope is changed or loaded.
	 */
	var scope=$('#policy_scope_combo').val();
	var actionObjects=get_scope_action_objects(scope);
	define_policy_action_autocomplete( actionObjects );
}

function define_policy_action_autocomplete(availableActionObjects) {
	/*
	 * This sets the allowed actions in the policy action input
	 */
	var availableActions = get_scope_actions(availableActionObjects);
	$( "#policy_action" )
		// don't navigate away from the field on tab when selecting an item
		.bind( "keydown", function( event ) {
			if ( event.keyCode === $.ui.keyCode.TAB &&
					$( this ).data( "autocomplete" ).menu.active ) {
				event.preventDefault();
			}
		})
		.autocomplete({
			minLength: 0,
			source: function( request, response ) {
				// delegate back to autocomplete, but extract the last term
				response( $.ui.autocomplete.filter(
					availableActions, extractLast( request.term ) ) );
			},
			focus: function(event, data) {
				var focus_action = data.item.value.split("=")[0];
				var description = "?";
				if (availableActionObjects[focus_action].hasOwnProperty("desc")) {
					description = availableActionObjects[focus_action].desc;
				};
				$('#action_info').html(description);
				// prevent value inserted on focus
				return false;
			},
			select: function( event, ui ) {
				var terms = split( this.value );
				// remove the current input
				terms.pop();
				// add the selected item
				terms.push( ui.item.value );
				// add placeholder to get the comma-and-space at the end
				terms.push( "" );
				this.value = terms.join( ", " );
				return false;
			}
		});
}

function view_policy() {

    $("#policy_table").flexigrid({
    		url : '/system/policies_flexi?session='+getsession(),
    		method: 'POST',
			dataType : 'json',
    		colModel : [    {display: 'Active', name : 'active', width : 35, sortable : true},
    						{display: 'Name', name : 'name', width : 100, sortable : true},
							{display: 'User', name : 'user', width : 80, sortable : true},
							{display: 'Scope', name : 'scope', width : 80, sortable : true},
							{display: 'Action', name : 'action', width : 200, sortable : true},
							{display: 'Realm', name : 'realm', width : 100, sortable : true},
							{display: 'Client', name : 'client', width : 200, sortable : true},
							{display: 'Time', name : 'time', width : 50, sortable : true}
								],
			height: 200,
			searchitems : [
				{display: 'in all columns', name : 'all', isdefault: true}
				],
			rpOptions: [10,15,20,50,100],
			sortname: "name",
			sortorder: "asc",
			useRp: true,
			rp: 50,
			usepager: true,
			singleSelect: true,
			showTableToggleBtn: true,
            preProcess: pre_flexi,
			onError: error_flexi,
			addTitleToCell: true,
			dblClickResize: true,
			searchbutton: true
    });

    $('#policy_export').attr("href", '/system/getPolicy/policy.cfg?session=' + getsession());

    $('#policy_import').click(function(){
    	$dialog_import_policy.dialog("open");
    });

    $('#button_policy_add').click(function(){
    	var pol_name = $('#policy_name').val();
    	pol_name = $.trim(pol_name);
    	if (pol_name.length == 0) {
		alert_box('Policy Name',"text_policy_name_not_empty");
    		return;
    	}

    	var pol_active = $('#policy_active').attr("checked");
    	if (pol_active == "checked") {
    		pol_active = "True";
    	} else {
    		pol_active = "False";
    	}

		$.post('/system/setPolicy',
			{ 'name' : $('#policy_name').val(),
			  'user' : $('#policy_user').val(),
			  'action' : $('#policy_action').val(),
			  'scope' : $('#policy_scope_combo').val(),
			  'realm' : $('#policy_realm').val(),
			  'time' : $('#policy_time').val(),
			  'client' : $('#policy_client').val(),
			  'active' : pol_active,
			  'session':getsession() },
		 function(data, textStatus, XMLHttpRequest){
			if (data.result.status == true) {
				alert_info_text("text_policy_set");
				$('#policy_table').flexReload();
			}else {
				alert_info_text(data.result.error.message,"" , ERROR);
			}
		});
	});

    $('#button_policy_delete').click(function(){
		var policy = get_selected_policy().join(',');
		if (policy) {
			$.post('/system/delPolicy', {'name' : policy, 'session':getsession()},
			 function(data, textStatus, XMLHttpRequest){
				if (data.result.status == true) {
					alert_info_text("text_policy_deleted");
			        $('#policy_table').flexReload();
				} else {
					alert_info_text(data.result.error.message, "", ERROR);
				}
			});
		}
	});


	$('#policy_scope_combo').change(function(){
		renew_policy_actions();
	});

	$('#policy_table').click(function(event){
    	get_selected();
	});

}

function view_token() {
	    $("#token_table").flexigrid({
    		url : '/manage/tokenview_flexi?session='+getsession(),
    		method: 'POST',
			dataType : 'json',
    		colModel : [ {display: 'serial number', name : 'TokenSerialnumber', width : 100, sortable : true, align: 'center'},
							{display: 'active', name : 'Isactive', width : 30, sortable : true, align: 'center'},
							{display: 'username', name : 'Username', width : 100, sortable : false, align: 'center'},
							{display: 'realm', name : 'realm', width : 100, sortable : false, align: 'center'},
							{display: 'type', name : 'TokenType', width : 50, sortable : true, align: 'center'},
							{display: 'counter login', name : 'FailCount', width : 30, sortable : true, align: 'center'},
							{display: 'description', name : 'TokenDesc', width : 100, sortable : true, align: 'center'},
							{display: 'maxfailcount', name : 'maxfailcount', width : 50, sortable : false, align: 'center'},
							{display: 'otplen', name : 'otplen', width : 50, sortable : false, align: 'center'},
							{display: 'countwindow', name : 'countwindow', width : 50, sortable : false, align: 'center'},
							{display: 'syncwindow', name : 'syncwindow', width : 50, sortable : false, align: 'center'},
                            {display: 'userid', name : 'Userid', width : 100, sortable : true, align: 'center'},
							{display: 'resolver', name : 'IdResolver', width : 200, sortable : true, align: 'center'}
								],
			height: 400,
			searchitems : [
				{display: 'in loginname', name: 'loginname', isdefault: true },
				{display: 'in all other columns', name : 'all'},
				{display: 'realm', name: 'realm' }
				],
			rpOptions: [10,15,20,50,100],
			sortname: "TokenSerialnumber",
			sortorder: "asc",
			useRp: true,
			rp: 15,
			usepager: true,
			showTableToggleBtn: true,
            preProcess: pre_flexi,
			onError: error_flexi,
			addTitleToCell: true,
			dblClickResize: true,
			searchbutton: true
    });
	$('#token_table').click(function(event){
    	get_selected();
	});

}

function view_user() {
	    $("#user_table").flexigrid({
    		url : '/manage/userview_flexi?session='+getsession(),
    		method: 'POST',
			dataType : 'json',
    		colModel : [ {display: 'username', name : 'username', width : 90, sortable : true, align:"left"},
                        {display: 'useridresolver', name : 'useridresolver', width : 200, sortable : true, align:"left"},
			{display: 'surname', name : 'surname', width : 100, sortable : true, align:"left"},
			{display: 'givenname', name : 'givenname', width : 100, sortable : true, align:"left"},
			{display: 'email', name : 'email', width : 100, sortable : false, align:"left"},
                        {display: 'mobile', name : 'mobile', width : 50, sortable : true, align:"left"},
			{display: 'phone', name : 'phone', width : 50, sortable : false, align:"left"},
                        {display: 'userid', name : 'userid', width : 200, sortable : true, align:"left"}
			],
			height: 400,
			searchitems : [
				{display: 'in username			', name : 'username', isdefault: true},
				{display: 'surname			', name : 'surname'},
				{display: 'given name			', name : 'givenname'},
				{display: 'description			', name : 'description'},
				{display: 'userid			', name : 'userid'},
				{display: 'email			', name : 'email'},
				{display: 'mobile			', name : 'mobile'},
				{display: 'phone			', name : 'phone'}
				],
			rpOptions: [15,20,50,100],
			sortname: "username",
			sortorder: "asc",
			useRp: true,
			singleSelect: true,
			rp: 15,
			usepager: true,
			showTableToggleBtn: true,
            preProcess: pre_flexi,
			onError: error_flexi,
			onSubmit: load_flexi,
			addTitleToCell: true,
			dblClickResize: true,
			searchbutton: true
    });

    $('#user_table').click(function(event){
    	get_selected();
	});
}

function view_audit() {
	   $("#audit_table").flexigrid({
    		url : '/audit/search?session='+getsession(),
    		method: 'POST',
			dataType : 'json',
    		colModel : [ {display: 'number', name : 'number', width : 50, sortable : true},
                        {display: 'date', name : 'date', width : 160, sortable : true},
						{display: 'signature', name : 'signature', width : 40, sortable : false},
						{display: 'missing lines', name : 'missing_lines', width : 40, sortable : false},
						{display: 'action', name : 'action', width : 120, sortable : true},
                        {display: 'success', name : 'success', width : 40, sortable : true},
						{display: 'serial', name : 'serial', width : 100, sortable : true},
                        {display: 'tokentype', name : 'tokentype', width : 50, sortable : true},
                        {display: 'user', name : 'user', width : 100, sortable : true},
                        {display: 'realm', name : 'realm', width : 100, sortable : true},
                        {display: 'administrator', name : 'administrator', width : 100, sortable : true},
                        {display: 'action_detail', name : 'action_detail', width : 200, sortable : true},
                        {display: 'info', name : 'info', width : 200, sortable : true},
                        {display: 'privacyidea_server', name : 'privacyidea_server', width : 100, sortable : true},
                        {display: 'client', name : 'client', width : 100, sortable : true},
                        {display: 'log_level', name : 'log_level', width : 40, sortable : true},
                        {display: 'clearance_level', name : 'clearance_level', width : 20, sortable : true}
			],
			height: 400,
			searchitems : [
				{display: 'serial', name : 'serial', isdefault: true},
				{display: 'user', name : 'user', isdefault: false},
				{display: 'realm', name : 'realm', isdefault: false},
				{display: 'action', name: 'action' },
				{display: 'action detail', name: 'action_detail' },
				{display: 'tokentype', name: 'token_type' },
				{display: 'administrator', name: 'administrator' },
				{display: 'successful action', name: 'success' },
				{display: 'info', name: 'info' },
				{display: 'privacyIDEA server', name: 'privacyidea_server' },
				{display: 'Client', name: 'client' },
				{display: 'date', name: 'date' },
				{display: 'extended search', name: 'extsearch' }
			],
			rpOptions: [10,15,30,50],
			sortname: "number",
			sortorder: "desc",
			useRp: true,
			singleSelect: true,
			rp: 15,
			usepager: true,
			showTableToggleBtn: true,
            preProcess: pre_flexi,
			onError: error_flexi,
			onSubmit: load_flexi,
			addTitleToCell: true,
			searchbutton: true
    });
}

