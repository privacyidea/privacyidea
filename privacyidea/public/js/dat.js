function create_dat_dialog() {	
	var $dialog_load_tokens_dat = $('#dialog_import_dat').dialog({
        autoOpen: false,
        title: 'eToken dat file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': { click: function(){
        	    $('#loadtokens_session_dat').val(getsession());
                load_tokenfile('dat');
                $(this).dialog('close');
            	},
				id: "button_dat_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_dat_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_dat();
        	 do_dialog_icons();	
        }
    });
    return $dialog_load_tokens_dat;
 }
