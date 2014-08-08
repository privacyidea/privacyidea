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
    	obj = $('td[abbr="'+name+'"] >div', this);
    	selectedMachine = obj.html();
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
	/*
	 * This function is called, when a machine entry
	 * in the flexigrid is selected
	 */
	machine = _fix_space(get_selected_machine("machine"));
	application = _fix_space(get_selected_machine("application"));
	ip = _fix_space(get_selected_machine("IP"));
	description = _fix_space(get_selected_machine("description"));
	serial = _fix_space(get_selected_machine("serial"));
	
	$('#machine_name').val(machine);
	$('#machine_ip').val(ip);
	$('#machine_application').val(application);
	$('#machine_serial').val(serial);
	$('#machine_desc').val(description);
	// if we also contain application and serial, we
	// call all the options...
	if ((application != "") && (serial != "")) {
		clientUrlFetch("/machine/showtoken",
				{"name": machine,
				"serial": serial,
				"application": application,
				"session": getsession()},
				options_callback);
	} 
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

function options_callback(xhdr, textStatus) {
	/* This function is called, when the options for a
	 * selected machinetoken is fetched
	 */
	resp = xhdr.responseText;
	obj = jQuery.parseJSON(resp);
    if (obj.result.status == false) {
    	alert_info_text(obj.result.error.message);
    }else{
    	// remove old table rows
    	$('#options_table tr.dynamic').remove();
    	if (obj.result.value.machines) {
    		machines = obj.result.value.machines;
    		id = Object.keys(obj.result.value.machines)[0];
    		machine = obj.result.value.machines[id];
    		options = machine.options;
    		// This machine token has options
    		for (var key in options) {
    			new_row = "<tr class=dynamic><td>"+key+"</td><td>"+ options[key] +"</td>";
    			new_row += "<td><button id='" +key+ "' class='button_delete_option' title='Remove application option' ";
    			new_row += "onclick='machine_delete_option(this.id);'> </button></td>";
    			new_row += "</tr>";
    			$('#options_table tr:last').before(new_row);
    			$('.button_delete_option').button({
    		        icons: {
    		            primary: 'ui-icon-minusthick'
    		        }
    		    });
    		}
    	}
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

function machine_add_option(){
	/*
	 * This adds a new option to an existing machine
	 */
	var machine = $('#machine_name').val();
	var serial = $('#machine_serial').val();
	var application = $('#machine_application').val();
	var new_option_key = $('#new_option_key').val();
	// If the key does not start with "option_", we add it!
	if (new_option_key.indexOf("option_") != 0) {
		new_option_key = "option_" + new_option_key;
	}
	var new_option_value = $('#new_option_value').val();
	if ((machine == "") ||
		(serial == "") ||
		(application == "")) {
    	alert_info_text("text_add_option_missing_entry", "", "error");		
	} else {
		var params = {"session": getsession(),
				 "name": machine,
				 "serial": serial,
				 "application": application};
		params[new_option_key] = new_option_value;
		resp = clientUrlFetchSync("/machine/addoption",
				params);
		obj = jQuery.parseJSON(resp);
	    if (obj.result.status) {
	    	// reload the selected machine.
			view_selected_machine();
			// clear the entries
			$('#new_option_key').val("");
			$('#new_option_value').val("");
	    }
	}
}

function machine_delete_option(key){
	/* 
	 * Deletes this option from a selected machinetoken
	 */	
	var machine = $('#machine_name').val();
	var serial = $('#machine_serial').val();
	var application = $('#machine_application').val();
	if ((machine == "") ||
		(serial == "") ||
		(application == "")) {
	    	alert_info_text("text_add_option_missing_entry", "", "error");		
		} else {
			var params = {"session": getsession(),
					 "name": machine,
					 "serial": serial,
					 "application": application,
					 "key": key};
			resp = clientUrlFetchSync("/machine/deloption",
					params);
			obj = jQuery.parseJSON(resp);
		    if (obj.result.status) {
		    	// reload the selected machine.
				view_selected_machine();
		    }
		}
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
					{display: 'active', name : 'is_active', width : 90, sortable : false},
                    {display: 'application', name : 'application', width : 120, sortable : true}
		],
		height: 400,
		searchitems : [
			{display: 'machine', name : 'machine', isdefault: true},
			{display: 'IP', name : 'IP', isdefault: false},
			{display: 'description', name : 'description', isdefault: false},
			{display: 'serial', name : 'serial', isdefault: false},
			{display: 'application', name: 'application', isdefault: false}
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
    	get_selected();
	});
	
	// Button functions
	$('#button_client_token').click(function(event){
	    token_assign_machine();
	    return false;
	});
	
	fill_applications();
}

function get_selected_machines(){
	/*
	 * This function returns the list of selected machines
	 * Each list element is an object with
	 *  - machine_id
	 *  - name
	 *  - id
	 */
    var selectedMachineItems = new Array();
    var tt = $("#machine_table");
    var selected = $('.trSelected', tt);
    selected.each(function(){
    	var machine = new Object();
    	machine = { machine_id: "" , name: "", id: "" };
    	column = $('td', $(this));
    	column.each(function(){
    		var attr = $(this).attr("abbr");
    		if (attr == "machine") {
    			var name = $('div', $(this)).html();
    			machine.name = name;
    		}
    		else if (attr == "machine_id") {
    			var machine_id = $('div', $(this)).html();
    			machine.machine_id = machine_id;
    		}
    	});

        var id = $(this).attr('id');
        machine.id = id.replace(/row/, "");
        selectedMachineItems.push(machine);
    });
    return selectedMachineItems;
}



function token_assign_machine() {
	/*
	 * Create the applications with the selected tokens
	 */
    tokens = get_selected_tokens();  
	machine = $('#machine_name').val();
	ip = $('#machine_ip').val();
	desc = $('#machine_desc').val();
	application = $('#machine_application').val();
	// Try to create machine
	clientUrlFetch("/machine/create",
					{"name": machine,
					 "ip": ip,
					 "desc": desc,
					 "session": getsession()},
					 machine_create_callback);
	if ((application!="") && (tokens.length > 0)) {
		// add the token
		count = tokens.length;
	    for (i = 0; i < count; i++) {
	        serial = tokens[i];
	        clientUrlFetch("/machine/addtoken",
	        		{"name": machine,
					"serial": serial,
					"application": application,
					"session": getsession()},
					machine_create_callback);
	    }
	}
	return false;
};