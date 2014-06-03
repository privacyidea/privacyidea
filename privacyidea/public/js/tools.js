function create_tools_getserial_dialog() {
	 var $dialog = $('#dialog_get_serial').dialog({
        autoOpen: false,
        title: 'Get Serial by OTP value',
        width: 600,
        modal: true,
        buttons: {
            'Get Serial': { click:  function(){
		                getSerialByOtp($('#tools_getserial_otp').val(),
		                		$('#tools_getserial_type').val(),
		                		$('#tools_getserial_assigned').val(),
		                		$('#tools_getserial_realm').val()
		                	);
						},
					id: "button_tools_getserial_ok",
					text: "Get Serial"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
						},
						id: "button_tools_getserial_close",
						text:"Close"
            }
        },
        open: function() {
        	translate_get_serial();
        	do_dialog_icons();
        }
    });
    return $dialog;
  }


function copyTokenPin(from_token, to_token) {
	var param = {};
	param["from"] = from_token;
	param["to"]   = to_token;

    var resp = clientUrlFetchSync('/admin/copyTokenPin', param, true);
    var obj = jQuery.parseJSON(resp);
     	if (obj.result.status==true) {
    		if (obj.result.value==true) {
    			alert("Token PIN copied successfully.");
    		}
    		else
    			alert("Could not copy token PIN.");
	}
}

function create_tools_copytokenpin_dialog() {
	 var $dialog = $('#dialog_copy_token').dialog({
        autoOpen: false,
        title: 'Copy Token PIN',
        width: 600,
        modal: true,
        buttons: {
            'Copy PIN': { click:  function(){
		                copyTokenPin($('#copy_from_token').val(),
		                		$('#copy_to_token').val()
		                	);
						},
					id: "button_tools_copytokenpin_ok",
					text: "Copy PIN"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
						},
						id: "button_tools_copytokenpin_close",
						text:"Close"
            }
        },
        open: function(){
        	translate_copy_token();
        	do_dialog_icons();
        }
    });
    return $dialog;
  }

function checkPolicy(scope, realm, user, action, client) {
	if ($("#form_check_policy").valid()) {
		var param = {};
		param["scope"]   = scope;
		param["realm"]  = realm;
		param["user"]   = user;
		param["action"] = action;
		param["client"] = client;
		var resp = clientUrlFetchSync('/system/checkPolicy', param, true);
	    var obj = jQuery.parseJSON(resp);
	   	if (obj.result.status==true) {
	   		if (obj.result.value.allowed) {
	   			$('#cp_allowed').show();
	   			$('#cp_forbidden').hide();
	   			$('#cp_policy').html(  JSON.stringify(obj.result.value.policy).replace(/,/g,",\n").replace(/:\{/g,":\{\n"));
	   		}else{
	   			$('#cp_allowed').hide();
	   			$('#cp_forbidden').show();
	   			$('#cp_policy').html("" );
	   		}
	   	}else{

	   	}
   }
}

function create_tools_checkpolicy_dialog() {
	 var $dialog = $('#dialog_check_policy').dialog({
        autoOpen: false,
        title: 'Check Policy',
        width: 600,
        modal: true,
        buttons: {
            'Check Policy': { click:  function(){
		                checkPolicy($('#cp_scope').val(),
									$('#cp_realm').val(),
									$('#cp_user').val(),
									$('#cp_action').val(),
									$('#cp_client').val()
		                	);
						},
					id: "button_tools_checkpolicy_ok",
					text: "Copy PIN"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
						},
						id: "button_tools_checkpolicy_close",
						text:"Close"
            }
        },
        open: function(){
        	translate_check_policy();
        	do_dialog_icons();
        }
    });
    $("#form_check_policy").validate({
    	rules: {
            cp_user: {
                required: true
            },
            cp_realm: {
            	required: true
            },
            cp_action: {
            	required: true
            }
        }
    });

    return $dialog;
  }


function exportToken(attributes) {
	/*
	 * We can not do an AJAX call to the /admin/show, since then
	 * the result would not be downloadable by the browser.
	 * So we add temporarily this form to the body, submit the
	 * form and delete it afterwards.
	 */
	$("<form action='/admin/show?outform=csv&session="+getsession()+"&user_fields="+attributes+"' method='post'></form>").appendTo("body").submit().remove();
}

function create_tools_exporttoken_dialog() {
	 var $dialog = $('#dialog_export_token').dialog({
        autoOpen: false,
        title: 'Export token information',
        width: 600,
        modal: true,
        buttons: {
            'Export': { click:  function(){
            			exportToken($('#exporttoken_attributes').val());
						},
					id: "button_export_token",
					text: "Export token"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
						},
						id: "button_export_token_close",
						text:"Close"
            }
        },
        open: function(){
        	translate_export_token();
        	do_dialog_icons();
        }
    });

    return $dialog;
}

function exportAudit(audit_num, audit_page) {
	/*
	 * We can not do an AJAX call to the /audit/search, since then
	 * the result would not be downloadable by the browser.
	 * So we add temporarily this form to the body, submit the
	 * form and delete it afterwards.
	 */
	if ( $.isNumeric(audit_num) == false ) {
		audit_num = 1000;
	}
	if ( $.isNumeric(audit_page) == false) {
		audit_page = 1;
	}

	$("<form action='/audit/search?outform=csv&rp="+audit_num+
		"&page="+audit_page+"&headers=true"+
		"&session="+getsession()+"' method='post'></form>").appendTo("body").submit().remove();
}

function create_tools_exportaudit_dialog() {
	 var $dialog = $('#dialog_export_audit').dialog({
        autoOpen: false,
        title: 'Export audit information',
        width: 600,
        modal: true,
        buttons: {
            'Export': { click:  function(){
            			exportAudit($('#export_audit_number').val(),
            						$('#exüprt_audit_page').val());
            			$(this).dialog('close');
						},
					id: "button_export_audit",
					text: "Export audit"
            },
            'Close': { click: function(){
                			$(this).dialog('close');
						},
						id: "button_export_audit_close",
						text:"Close"
            }
        },
        open: function(){
        	translate_export_audit();
        	do_dialog_icons();
        }
    });

    return $dialog;
}

function add_user_data() {
	/*
	 * This function returns an object with the user data as needed by the /admin/init controller
	 */
	var param = new Object();
	var users = get_selected_users();
	if (users[0]) {
		param['user'] = users[0].login;
		param['resConf'] = users[0].resolver;
		param['realm'] = $('#realm').val();
	}
	return param;
}
