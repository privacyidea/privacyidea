var $dialog_delete_machine_confirm;
var $dialog_delete_app_confirm;

function get_applications() {
	var applications = new Array();
	resp = clientUrlFetchSync("/machine/getapplications",
			{"session": getsession()});
	obj = jQuery.parseJSON(resp);
    if (obj.result.status) {
		applications = obj.result.value;
    }
	return applications;
}

function fill_applications() {
	var apps = get_applications();
	$('#machine_application').append(
	        $('<option></option>').val("").html(""));
	$.each(apps, function(ind, val) {
	    $('#machine_application').append(
		        $('<option></option>').val(val).html(val)
		    );
		});
}

function init_machine_dialogs() {
	$dialog_delete_machine_confirm = $('#dialog_delete_machine_confirm').dialog({
    autoOpen: false,
    title: 'Delete selected machine?',
    resizable: false,
    width: 400,
    modal: true,
    buttons: {
        'Delete machine': {click: function(){
        						do_delete_machine();
    							$(this).dialog('close');
    							},
							id: "button_delete_machine",
							text: "Delete machine"	
						},
		Cancel: {click: function(){
            			$(this).dialog('close');
        				},
    				id: "button_delete_machine_cancel",
    				text: "Cancel"
    	}
    },
    open: function(){
    	var machine = get_selected_machine("machine");
    	var ip = get_selected_machine("IP");
    	$('#delete_machine_info').html( machine + "(" + ip +")" );
    	translate_dialog_delete_machine_confirm();
    }
	});
	
	$dialog_delete_app_confirm = $('#dialog_delete_app_confirm').dialog({
	    autoOpen: false,
	    title: 'Remove selected App and Token from machine?',
	    resizable: false,
	    width: 400,
	    modal: true,
	    buttons: {
	        'Remove application': {click: function(){
	        						do_delete_application();
	    							$(this).dialog('close');
	    							},
								id: "button_delete_app",
								text: "Delete machine"	
							},
			Cancel: {click: function(){
	            			$(this).dialog('close');
	        				},
	    				id: "button_delete_app_cancel",
	    				text: "Cancel"
	    	}
	    },
	    open: function(){
	    	var machine = get_selected_machine("machine");
	    	var serial = get_selected_machine("serial");
	    	var app = get_selected_machine("application");
	    	$('#delete_app_info').html( machine + " / " + serial +" / " + app );
	    	translate_dialog_delete_app_confirm();
	    }
		});

}

function get_selected_machine(name){
    var selectedMachine = "";
    $('#machine_table .trSelected').each(function(){
    	rowid = $(this).attr("id").substr(3);
    	selectedMachine = $('td[abbr="'+name+'"] >div', this).html();
    	});
    return selectedMachine;
}

function _fix_space(value) {
	if (value == "&nbsp;") {
		value = "";
	}
	return value;
}

function view_selected_machine(){
	machine = get_selected_machine("machine");
	application = get_selected_machine("application");
	ip = get_selected_machine("IP");
	description = get_selected_machine("description");
	serial = get_selected_machine("serial");
	
	$('#machine_name').val(_fix_space(machine));
	$('#machine_ip').val(_fix_space(ip));
	$('#machine_application').val(_fix_space(application));
	$('#machine_serial').val(_fix_space(serial));
	$('#machine_desc').val(_fix_space(description));
	
}

function machine_delete(){
	$dialog_delete_machine_confirm.dialog('open');
    return false;
}

function machine_delete_app(){
	$dialog_delete_app_confirm.dialog('open');
    return false;
}

function machine_delete_callback(xhdr, textStatus) {
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	alert_info_text(obj.result.error.message);
    }else{
    	alert_info_text("text_delete_machine_success", "", "info");
    	$('#machine_table').flexReload();
    }
}

function machine_create_callback(xhdr, textStatus) {
	serial = $('#machine_serial').val();
	application = $('#machine_application').val();
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	if ((serial=="") || (application=="")) 
    		alert_info_text(obj.result.error.message);
    }else{
    	alert_info_text("text_create_machine_success", "", "info");
    	$('#machine_table').flexReload();
    } 
}

function app_delete_callback(xhdr, textStatus) {
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	alert_info_text(obj.result.error.message);
    }else{
    	alert_info_text("text_delete_app_success", "", "info");
    	$('#machine_table').flexReload();
    }
}

function do_machine_create(){
	machine = $('#machine_name').val();
	ip = $('#machine_ip').val();
	desc = $('#machine_desc').val();
	serial = $('#machine_serial').val();
	application = $('#machine_application').val();
	// Try to create machine
	clientUrlFetch("/machine/create",
			{"name": machine,
			"ip": ip,
			"desc": desc,
			"session": getsession()},
			machine_create_callback);
	if ((application!="") && (serial!="")) {
		// add the token
		clientUrlFetch("/machine/addtoken",
				{"name": machine,
				"serial": serial,
				"application": application,
				"session": getsession()},
				machine_create_callback);
	}
	return false;
}

function do_delete_machine(){
	machine = get_selected_machine("machine");
    clientUrlFetch("/machine/delete", 
    			{"name": machine, 
    			"session" : getsession()},
    			machine_delete_callback);
	$dialog_delete_machine_confirm.dialog('close');
}

function do_delete_application(){
	machine = get_selected_machine("machine");
	serial = get_selected_machine("serial");
	app = get_selected_machine("application");
	clientUrlFetch("/machine/deltoken", 
			{"name": machine,
			"serial": serial,
			"application": app,
			"session" : getsession()},
			app_delete_callback);
	$dialog_delete_app_confirm.dialog('close');
}

function view_machine() {
	$("#machine_table").flexigrid({
		url : '/machine/showtoken?flexi=1',
		params: [{name: "session",
				  value: getsession()}],
		method: 'POST',
		dataType : 'json',
		colModel : [{display: 'id', name: 'id', width: 40, sortable: false},
		            {display: 'machine_id', name : 'machine_id', width : 80, sortable : true},
					{display: 'machine', name : 'machine', width : 120, sortable : true},
					{display: 'IP', name : 'IP', width : 120, sortable : true},
					{display: 'description', name : 'description', width : 180, sortable : true},
					{display: 'serial', name : 'serial', width : 180, sortable : true},
                    {display: 'application', name : 'application', width : 120, sortable : true}
		],
		height: 400,
		searchitems : [
			{display: 'machine', name : 'machine', isdefault: true},
			{display: 'IP', name : 'IP', isdefault: false},
			{display: 'description', name : 'description', isdefault: false},
			{display: 'serial', name : 'serial', isdefault: false},
			{display: 'application', name: 'application' }
		],
		rpOptions: [10,15,30,50],
		sortname: "machine",
		sortorder: "desc",
		useRp: true,
		singleSelect: true,
		rp: 15,
		usepager: true,
		showTableToggleBtn: true,
        preProcess: pre_flexi,
		onError: error_flexi,
		//onSubmit: load_flexi,
		addTitleToCell: true,
		searchbutton: true
	});
	
	$('#machine_table').click(function(event){
    	view_selected_machine();
	});
	
	fill_applications();
}