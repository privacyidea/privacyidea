window.onerror = error_handling;

/* The HTTP status code, that determines that
 * the Login to the selfservice portal is required.
 * Is also defined in controllers/account.py
 */
LOGIN_CODE = 576;

function alert_box(p_title, s, param1) {
	/*
	 * If the parameter is the ID of an element, we pass the text of this very element
	 */
	var str = s;
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

    $('#allert_box_text').html(s);

	$( "#allert_box" ).dialog({
		title : p_title,
		width: 450,
	    modal: true,
	    buttons: {
	            Ok: function() {
	                $( this ).dialog( "close" );
	            }
	        }
	 });


}



function sprintf() {
	if (sprintf.arguments.length < 2) {
		return;
	}

	var data = sprintf.arguments[0];

	for (var k = 1; k < sprintf.arguments.length; ++k) {

		switch( typeof( sprintf.arguments[ k ] ) ) {
			case 'string':
				data = data.replace(/%s/, sprintf.arguments[k]);
				break;
			case 'number':
				data = data.replace(/%d/, sprintf.arguments[k]);
				break;
			case 'boolean':
				data = data.replace(/%b/, sprintf.arguments[k] ? 'true' : 'false');
				break;
			default:
				/// function | object | undefined
				break;
		}
	}
	return (data );
}

if (!String.sprintf) {
	String.sprintf = sprintf;
}

function error_handling(message, file, line) {
	Fehler = "We are sorry. An internal error occurred:\n" + message + "\nin file:" + file + "\nin line:" + line;
	alert(Fehler);
	return true;
}

/*
 * Retrieve session cookie if it does not exist
 */

function get_selfservice_session() {
	var session = "";
	if (document.cookie) {
		session = getcookie("privacyidea_session");
		if (session == "") {
			alert("there is no privacyidea_session cookie");
		}
	}
	return session;
}

function log(text) {
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

// Old functions from the tokenhandling and prototype

function resync() {
	show_waiting();
	var otp1 = $('#otp1').val();
	var otp2 = $('#otp2').val();
	var serial = $('.selectedToken').val();

	if (otp1 == "" || otp2 == "" || serial == "") {
		alert("You need to select a Token and enter two OTP values.");
		hide_waiting();
	} else {
		$.post('/selfservice/userresync', {
			'otp1' : otp1,
			'otp2' : otp2,
			'serial' : serial,
			'session' : get_selfservice_session()
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert("Error resyncing Token: " + data.result.error.message);
			};
			if (data.result.status == true) {
				if (data.result.value['resync Token']) {
					alert("Token resynced successfully");
				} else {
					alert("Failed to resync Token");
				}
			};
		});
	}
	return false;
}

function assign() {
	show_waiting();
	var serial = $('#assign_serial').val();
	if (serial == "") {
		alert("You need to enter a serial number");
		hide_waiting();
	} else {
		Check = confirm("You are going to assign a new token to you. Is this the correct serial: " + serial + "?");
		if (Check == false) {
			hide_waiting();
			return false;
		} else {
			$.post('/selfservice/userassign', {
				'serial' : serial,
				'description' : 'self assigned',
				'session' : get_selfservice_session()
			}, function(data, textStatus, XMLHttpRequest) {
				hide_waiting();
				if (data.result.status == false) {
					alert("Error assigning Token: " + data.result.error.message);
				};
				if (data.result.status == true) {
					alert("Token assigned successfully");
					showTokenlist();
					$('#assign_serial').val('');
				};
			});
		} // end of else
	}
	showTokenlist();
	return false;
}

function getserial() {
	/*
	 * Get the serial number for a given OTP value and fill the corresponding input
	 */
	show_waiting();
	var otp = $('#otp_serial').val();
	if (otp == "") {
		alert("You need to enter an OTP value");
		hide_waiting();
	} else {
		$.post('/selfservice/usergetSerialByOtp', {
			'otp' : otp,
			'session' : get_selfservice_session()
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert("Error getting Serial: " + data.result.error.message);
			};
			if (data.result.status == true) {
				var serial = data.result.value.serial;
				if (serial != "") {
					$('#assign_serial').val(serial);
				} else {
					alert("No Token with this OTP value found!");
				}
			};
		});

	}
	return false;
}

function token_call(formid, params) {

	var typ = params['type'];
	params['session'] = get_selfservice_session();

	if ($('#' + formid).valid()) {
		show_waiting();
		$.post('/selfservice/token_call', params, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert("Error calling token:" + data.result.error.message);
			};
			if (data.result.status == true) {
				showTokenlist();
			};
		});
		// end of get
	} else {
		alert("Form data not valid.");
	}
	showTokenlist();
	return false;

}

function enroll_token(params) {
	/*
	 * call the userinit to enroll a token
	 *
	 */
	var token_enroll_ok = $('#token_enroll_ok').val();
	var token_enroll_fail = $('#token_enroll_fail').val();

	var typ = params['type'];

	if (params['description'] === undefined) {
		params['description'] = "self enrolled";
	}
	params['session'] = get_selfservice_session();

	show_waiting();
	try {
		$.ajax({
			url : '/selfservice/userinit',
			data : params,
			dataType : "json",
			cache : false,
			async : false,
			type: 'POST',
			success : function(data) {
				//console_log(data.result)
				if (data.result.status == false) {
					alert(String.sprintf(token_enroll_fail, data.result.error.message));
				};
				if (data.result.status == true) {
					var details = '<ul>';
					if (data.hasOwnProperty('detail')) {
						var detail = data.detail;
						if (detail.hasOwnProperty('serial')) {
							details = details + '<li> serial: ' + detail.serial + '</li>';
						}
						if (detail.hasOwnProperty('otpkey')) {
							try {
								if (detail.hasOwnProperty('googleurl')) {
									details = details + '<li>Google QR Code</li>';
									details = details + '<p>' + detail.googleurl.img + '</p>';
									details = details + '<li>' + detail.googleurl.value + '</li>';
								}
							}
							catch (e){
								details = details + '<li> otpkey: ' + detail.otpkey + '</li>';
							}
						}
						if (detail.hasOwnProperty('ocraurl')) {
							details = details + '<li>OCRA QR Code</li>';
							if (detail.ocraurl.hasOwnProperty('img')) {
							   details = details + '<p>' + detail.ocraurl.img + '</p>';
							}
						}

					}
					details = details + '</ul>';
					alert_box('', String.sprintf(token_enroll_ok, details));
					/*
				    * the dynamic tokens must provide a function to gather all data from the form
					*/
					var functionString = "self_" + typ + '_enroll_details';
					var funct = window[functionString];
					var exi = typeof funct;
					if (exi == 'function') {
						var res = window[functionString](data);
					}
				};
			},
			error : function(data) {

				if (data.status == LOGIN_CODE) {
					alert("Your session has expired!");
					location.reload();
				} else {
					alert(JSON.stringify(data));
				}
				//console_log(JSON.stringify(data));
			}
		});

	} finally {
		hide_waiting();
		showTokenlist();
	}

	return false;

}

function enroll_hotp() {
	/*
	 * enroll the HOTP token with a given seed
	 */
	var seed = $('#hotp_secret').val();
	var type = "hmac";
	var hashlib = $('#hotp_hashlib').val();

	if ($('#form_enrollhotp').valid()) {
		show_waiting();
		$.post('/selfservice/userinit', {
			otpkey : seed,
			type : type,
			desciption : "self enrolled",
			session : get_selfservice_session(),
			hashlib : hashlib
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert("Error enrolling token:" + data.result.error.message);
			};
			if (data.result.status == true) {
				alert("Token enrolled successfully");
				showTokenlist();
			};
		});
		// end of get
	} else {
		alert("Form data not valid.");
	}
	return false;
}

function enroll_totp() {
	/*
	 * enroll the TOTP token with a given seed
	 */
	var seed = $('#totp_secret').val();
	var type = "totp";
	var hashlib = $('#totp_hashlib').val();
	var timeStep = $('#totp_timestep').val();
	if ($('#form_enrolltotp').valid()) {
		show_waiting();
		$.post('/selfservice/userinit', {
			otpkey : seed,
			type : type,
			desciption : "self enrolled",
			session : get_selfservice_session(),
			hashlib : hashlib,
			timeStep : timeStep
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert("Error enrolling token: " + data.result.error.message);
			};
			if (data.result.status == true) {
				alert("Token enrolled successfully");
				showTokenlist();
			};
		});
		// end of get
	} else {
		alert("Form data not valid.");
	}
	return false;
}

function reset_failcounter() {
	show_waiting();
	var serial = $('.selectedToken').val();
	$.post("/selfservice/userreset", {
		serial : serial,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == false) {
			alert("Error resetting Failcounter");
		};
		if (data.result.status == true) {
			alert("Failcounter resetted successfully");
			showTokenlist();
			$('.selectedToken').val("");
		};
	});
	return false;
}

function disable() {
	show_waiting();
	var serial = $('.selectedToken').val();
	$.post("/selfservice/userdisable", {
		serial : serial,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == false) {
			alert("Error disabling Token");
		};
		if (data.result.status == true) {
			alert("Token disabled successfully");
			showTokenlist();
			$('.selectedToken').val("");
		};
	});
	return false;
}

function enable() {
	show_waiting();
	var serial = $('.selectedToken').val();
	$.post("/selfservice/userenable", {
		serial : serial,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == false) {
			alert("Error enabling Token");
		};
		if (data.result.status == true) {
			alert("Token enabled successfully");
			showTokenlist();
			$('.selectedToken').val("");
		};
	});
	return false;
}

function getotp() {
	show_waiting();
	var serial = $('.selectedToken').val();
	var count = $('#otp_count').val();
	var session = get_selfservice_session();
	if (check_active_session()) {
		window.open('/selfservice/usergetmultiotp?serial=' + serial + '&session=' + session + '&count=' + count + '&view=1', 'getotp_window', "status=1,toolbar=1,menubar=1");
	}
	hide_waiting();
	return false;
}

function unassign() {
	show_waiting();
	var serial = $('.selectedToken').val();
	$.post("/selfservice/userunassign", {
		serial : serial,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == false) {
			alert("Error unassigning Token");
		};
		if (data.result.status == true) {
			alert("Token unassigned successfully");
			showTokenlist();
			$('.selectedToken').val("");
		};
	});
	return false;
}

function token_delete() {
	show_waiting();
	var serial = $('.selectedToken').val();
	$.post("/selfservice/userdelete", {
		serial : serial,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == false) {
			alert("Error deleting Token");
		};
		if (data.result.status == true) {
			alert("Token deleted successfully");
			showTokenlist();
			$('.selectedToken').val("");
		};
	});
	return false;
}

function provisionOath() {
	show_waiting();
	$.post("/selfservice/userwebprovision", {
		'type' : 'oathtoken',
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == true) {
			if (data.result.value.init == true) {
				// The token was successfully initialized and we will display the url
				showTokenlist();
				//$('#oath_info').hide();
				var url = data.result.value.oathtoken.url;
				var img = data.result.value.oathtoken.img;
				$('#oath_link').attr("href", url);
				$('#oath_qr_code').html(img);
				$('#provisionresultDiv').show();
				$('#qr_code_iphone_download_oath').hide();
			}
		} else {
			alert("Failed to enroll token!\n" + data.result.error.message);
		}
	});
}

function provisionOcra() {
	show_waiting();
	var acode = $('#activationcode').val();
	var serial = $('#serial').val();
	var activation_fail = $('#ocra_activate_fail').val();
	var genkey = 1;

	params = {
		'type' : 'ocra',
		'serial' : serial,
		'genkey' : 1,
		'activationcode' : acode,
		'session' : get_selfservice_session()
	};

	$.post("/selfservice/useractivateocratoken", params, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();

		if (data.result.status == true) {
			if (data.result.value.activate == true) {
				// The token was successfully initialized and we will display the url
				showTokenlist();
				// console_log(data.result.value)
				var img = data.result.value.ocratoken.img;
				var url = data.result.value.ocratoken.url;
				var trans = data.result.value.ocratoken.transaction;
				$('#ocra_link').attr("href", url);
				$('#ocra_qr_code').html(img);
				$('#qr_activate').hide();
				//$('#activationcode').attr("disabled","disabled");
				$('#transactionid').attr("value", trans);
				$('#qr_finish').show();
				$('#qr_confirm1').show();
				$('#qr_confirm2').show();
			}
		} else {
			alert(activation_fail + " \n" + data.result.error.message);
		}
	});
}

function finishOcra() {
	show_waiting();
	var trans = $('#transactionid').val();
	var serial = $('#serial').val();
	var ocra_check = $('#ocra_check').val();
	var ocra_finish_ok = $('#ocra_finish_ok').val();
	var ocra_finish_fail = $('#ocra_finish_fail').val();

	$.post("/selfservice/userfinshocratoken", {
		'type' : 'ocra',
		'serial' : serial,
		'transactionid' : trans,
		'pass' : ocra_check,
		'from' : 'finishOcra',
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();

		//console_log(data.result)

		if (data.result.status == true) {
			// The token was successfully initialized and we will display the url
			// if not (false) display an ocra_finish_fail message for retry
			showTokenlist();
			if (data.result.value.result == false) {
				alert(ocra_finish_fail);
			} else {
				alert(String.sprintf(ocra_finish_ok, serial));
				$('#qr_completed').show();
				$('#qr_finish').hide();
				//$('#ocra_check').attr("disabled","disabled");
				$('#ocra_qr_code').html('<div/>');
				$('#qr_completed').html(String.sprintf(ocra_finish_ok, serial));
			}
		} else {
			alert("Failed to enroll token!\n" + data.result.error.message);
		}
	});

}






function provisionGoogle() {
	show_waiting();
	var type = "googleauthenticator";
	if ($('#google_type').val() == "totp") {
		type = "googleauthenticator_time";
	}
	$.post("/selfservice/userwebprovision", {
		"type" : type,
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();
		if (data.result.status == true) {
			if (data.result.value.init == true) {
				showTokenlist();
				// The token was successfully initialized and we will display the url
				//var qr_code = generate_qrcode(10, data.result.value.oathtoken.url);
				var url = data.result.value.oathtoken.url;
				var img = data.result.value.oathtoken.img;
				$('#google_link').attr("href", url);
				$('#google_qr_code').html(img);
				$('#provisionGoogleResultDiv').show();
				$('#qr_code_iphone_download').hide();
			}
		} else {
			alert("Failed to enroll token!\n" + data.result.error.message);
		}
	});
}

function setpin() {
	show_waiting();
	var pin1 = $('#pin1').val();
	var pin2 = $('#pin2').val();
	var serial = $('.selectedToken').val();
	var setpin_failed = $('#setpin_fail').val();
	var setpin_error = $('#setpin_error').val();
	var setpin_ok = $('#setpin_ok').val();

	if (pin1 != pin2) {
		alert(setpin_failed);
		hide_waiting();
	} else {
		$.post('/selfservice/usersetpin', {
			userpin : pin1,
			serial : serial,
			session : get_selfservice_session()
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert(setpin_error + data.result.error.message);
			};
			if (data.result.status == true) {
				alert(setpin_ok);
				$('#pin1').val("");
				$('#pin2').val("");
			};
		});
	}
	return false;
}

function setmpin() {
	show_waiting();
	var pin1 = $('#mpin1').val();
	var pin2 = $('#mpin2').val();
	var serial = $('.selectedToken').val();
	var setpin_failed = $('#setpin_fail').val();
	var setpin_error = $('#setpin_error').val();
	var setpin_ok = $('#setpin_ok').val();

	if (pin1 != pin2) {
		alert(setpin_failed);
		hide_waiting();
	} else {
		$.post('/selfservice/usersetmpin', {
			pin : pin1,
			serial : serial,
			session : get_selfservice_session()
		}, function(data, textStatus, XMLHttpRequest) {
			hide_waiting();
			if (data.result.status == false) {
				alert(setpin_error + data.result.error.message);
			};
			if (data.result.status == true) {
				alert(setpin_ok);
				$('#mpin1').val("");
				$('#mpin2').val("");
			};
		});
	}
	return false;
}

function selectToken(serial) {
	$('.selectedToken').val(serial);
	$('#errorDiv').val("");
	$('#successDiv').val("");
}

function showTokenlist() {
	$.get('/selfservice/usertokenlist', {
		session : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		$('#tokenDiv').html(data);
	});
}

function check_active_session() {
	var active_session = true;
	$.ajax({
		url : '/selfservice/usertokenlist',
		dataType : "json",
		data : { 'session' : get_selfservice_session() },
		cache : false,
		async : false,
		error : function(data) {
				if (data.status == LOGIN_CODE) {
					alert("Your session has expired!");
					active_session = false;
					location.reload();
				}
		}});
	return active_session;
}

// =================================================================
// =================================================================
// Document ready
// =================================================================
// =================================================================

$(document).ready(function() {

	showTokenlist();

	$('ul.sf-menu').superfish();

	$.ajaxSetup({
		error: function(xhr, status, error) {
			if (xhr.status == LOGIN_CODE) {
				alert("Your session has expired!");
				location.reload();
			}
		}
	}
	);

	$('#do_waiting').overlay({
		top : 10,
		mask : {
			color : '#fff',
			loadSpeed : 100,
			opacity : 0.5
		},
		closeOnClick : false,
		load : true
	});
	$('#do_waiting').hide();

	$("#tabs").tabs({
		ajaxOptions : {
			error : function(xhr, status, index, anchor) {
				if (xhr.status == LOGIN_CODE) {
					alert("Your session has expired!");
					location.reload();
				} else {
					$(anchor.hash).html("Couldn't load this tab. Please respond to the administrator:" + xhr.statusText + " (" + xhr.status + ")");
				}
			}
		},
		collapsible : true,
		spinner : 'Retrieving data...',
		cache : true
	});

	// Log Div
	$("#logAccordion").accordion({
		fillSpace : true
	});

});

function deselect() {
	$(".pop").slideFadeToggle(function() {
		$("#contact").removeClass("selected");
	});
}

$(function() {
	$("#contact").live('click', function() {
		if ($(this).hasClass("selected")) {
			deselect();
		} else {
			$(this).addClass("selected");
			$(".pop").slideFadeToggle(function() {
				$("#email").focus();
			});
		}
		return false;
	});

	$(".close").live('click', function() {
		deselect();
		return false;
	});
});

$.fn.slideFadeToggle = function(easing, callback) {
	return this.animate({
		opacity : 'toggle',
		height : 'toggle'
	}, "fast", easing, callback);
};


//--------------------------------------------------------------------------------------
// End of document ready

function error_flexi(data){
    // we might do some mods here...
    if (data.status == LOGIN_CODE) {
		alert("Your session has expired!");
		location.reload();
	} else {
    	alert("Error loading history:" + data.status);
	}
}

function pre_flexi(data){
    // we might do some mods here...
    if (data.result) {
        if (data.result.status == false) {
            alert(data.result.error.message);
        }
    }
    else {
        return data;
    }
}

function load_flexi(){
    return true;
}

function view_audit_selfservice() {
	   $("#audit_selfservice_table").flexigrid({
    		url : '/selfservice/userhistory?session='+ get_selfservice_session(),
    		method: 'GET',
			dataType : 'json',
    		colModel : [{display: 'date', name : 'date', width : 160, sortable : true},
						{display: 'action', name : 'action', width : 120, sortable : true},
                        {display: 'success', name : 'success', width : 40, sortable : true},
						{display: 'serial', name : 'serial', width : 100, sortable : true},
                        {display: 'tokentype', name : 'tokentype', width : 50, sortable : true},
                        {display: 'administrator', name : 'administrator', width : 100, sortable : true},
                        {display: 'action_detail', name : 'action_detail', width : 200, sortable : true},
                        {display: 'info', name : 'info', width : 200, sortable : true}
			],
			height: 400,
			searchitems : [
				{display: 'serial', name : 'serial', isdefault: true},
				{display: 'date', name: 'date' },
				{display: 'action', name: 'action' },
				{display: 'action detail', name: 'action_detail' },
				{display: 'tokentype', name: 'token_type' },
				{display: 'administrator', name: 'administrator' },
				{display: 'successful action', name: 'success' },
				{display: 'info', name: 'info' },
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
			dblClickResize: true,
			searchbutton: true
    });
}
