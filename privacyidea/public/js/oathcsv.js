function create_oathcsv_dialog() {
 var $dialog_load_tokens_oathcsv = $('#dialog_import_oath').dialog({
        autoOpen: false,
        title: 'OATH csv Token file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': {click: function(){
            	$('#loadtokens_session_oathcsv').val(getsession());
                load_tokenfile('oathcsv');
                $(this).dialog('close');
            	},
				id: "button_oathcsv_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_oathcsv_cancel",
				text: "Cancel"
				}
        },
        open: do_dialog_icons
    });
	return $dialog_load_tokens_oathcsv ;
}
