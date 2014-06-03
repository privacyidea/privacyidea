function create_dpw_dialog() {	
	var $dialog_load_tokens_dpw = $('#dialog_import_dpw').dialog({
        autoOpen: false,
        title: 'Tagespasswort Token file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': { click: function(){
        	    $('#loadtokens_session_dpw').val(getsession());
                load_tokenfile('dpw');
                $(this).dialog('close');
            	},
				id: "button_dpw_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_dpw_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_dpw();
        	 do_dialog_icons();	
        }
    });
    return $dialog_load_tokens_dpw;
 } 