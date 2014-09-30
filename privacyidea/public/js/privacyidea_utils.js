
function checkpins(otp_pin1,otp_pin2){
/*
 *  check pins: verifies, that the pins in both
 *  referenced entries are equal
 */
    var pin1 = $('#'+otp_pin1).val();
    var pin2 = $('#'+otp_pin2).val();
    if (pin1 == pin2) {
        $('#'+otp_pin1).removeClass('ui-state-error');
        $('#'+otp_pin2).removeClass('ui-state-error');
    }
    else {
        $('#'+otp_pin1).addClass('ui-state-error');
        $('#'+otp_pin2).addClass('ui-state-error');
    }
    return false;
}

function cb_changed(checkbox_id,arry){
/*
 * cb_changed - dependent on the checkbox state,
 * show all entries (identified by their id), which are listed in the array
 */
 	var checked = $('#'+checkbox_id).attr('checked');

	for (i=0; i<arry.length; i++) {
		var sid = arry[i];
		if  ( checked )
			$('#'+sid).hide();
		else
			$('#'+sid).show();
	}
}

function show_waiting() {
	$('#do_waiting').show();
	//$('#statusline').show();
	//var milliseconds = (new Date()).getTime();
	//console.log("show: " +milliseconds);
}

function hide_waiting() {
	$("#do_waiting").hide();
	//$('#statusline').hide();
	//var milliseconds = (new Date()).getTime();
	//console.log("hide: " +milliseconds);
}

function getcookie(search_key) {
	var searched_cookie="";
	if (document.cookie) {
		cookieArray = document.cookie.split(';');
		//alert(document.cookie);
		var arLen=cookieArray.length;
		for ( var i=0; i<arLen; ++i ) {
			var cookie = cookieArray[i];
			var key_1 = 0;
			var key_2 = cookie.indexOf("=");
      		var val_1 = cookie.indexOf("=") + 1;
      		var val_2 = cookie.indexOf(";");
      		if(val_2 == -1) val_2 = document.cookie.length;

      		var key = cookie.substring(key_1,key_2);
			key=key.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
			key=key.replace(/^\""*/, '').replace(/\""*$/, '');

  			if (search_key == key) {
  				searched_cookie = cookie.substring(val_1,val_2);
  				searched_cookie = searched_cookie.replace(/^\""*/, '').replace(/\""*$/, '');
  			}
		}
	}
	return searched_cookie;
}

function console_log(msg) {
    if (window.console && window.console.log) {
        window.console.log(msg);
    }
    else if (window.opera && window.opera.postError) {
        window.opera.postError(msg);
    }
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


function save_realm_config_action(params) {
	/* Save the realm configuration with
	 * params: realm, resolvers
	 */
	params['session'] = getsession();
	show_waiting();
    $.post('/system/setRealm', params,
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


function save_file_config_action(params) {
	/* Save the file resolver with params
	 * name, type, filename
	 */
    show_waiting();
	params['session'] = getsession();
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

function create_initial_realm() {
    show_waiting();
    params = {"type": "passwdresolver",
            "name": "deflocal",
            "fileName": "/etc/passwd"};
	params['session'] = getsession();
	$.post('/system/setResolver', params,
	     function(data, textStatus, XMLHttpRequest){
	        hide_waiting();
	        if (data.result.status == false) {
	            alert_info_text("text_error_save_file", data.result.error.message, ERROR);
	        } else {
	            show_waiting();
	        	params = {"realm": "defrealm",
	        	         "resolvers": "privacyidea.lib.resolvers.PasswdIdResolver.IdResolver.deflocal"}
	        	params['session'] = getsession();
	        	$.post('/system/setRealm', params,
        		     function(data, textStatus, XMLHttpRequest){
        		        hide_waiting();
        		        if (data.result.status == false) {
        		        	alert_info_text("text_error_realm", data.result.error.message, ERROR);
        		        } else {
        		        	alert_info_text("text_realm_created", "defrealm");
        		        	fill_realms();
        		        }
        		    });
	        }
	    });
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

function ask_autocreate_realm() {
	var realms = get_realms();
	var cook = get_cookie("privacyidea_autocreate");
	if ((realms.length == 0) && (cook == "")) {
		$dialog_autocreate_realm.dialog('open');
	}
}

function get_cookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) != -1) return c.substring(name.length,c.length);
    }
    return "";
}

function autocreate_realm(answer) {
	var remember = $('#cb_autocreate_realm').is(':checked');
	if (remember == true) {
		document.cookie="privacyidea_autocreate=done";
	}
	if (answer == "yes") {
		create_initial_realm();
	}
}
