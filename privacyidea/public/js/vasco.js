

function create_vasco_dialog() {
	 var $dialog = $('#dialog_import_vasco').dialog({
        autoOpen: false,
        title: 'Vasco dpx file',
        width: 600,
        modal: true,
        buttons: {
            'load dpx file': { click: function(){
            	$('#loadtokens_session_vasco').val(getsession());
                load_tokenfile('vasco');
                $(this).dialog('close');
            	},
				id: "button_vasco_load",
				text: "load dpx file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_vasco_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_vasco();
        	do_dialog_icons();
        }
       });
       return $dialog;
};