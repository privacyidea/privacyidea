function create_yubikeycsv_dialog() {
 var $dialog_load_tokens_yubikeycsv = $('#dialog_import_yubikey').dialog({
        autoOpen: false,
        title: 'Yubikey csv Token file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': {click: function(){
            	$('#loadtokens_session_yubikeycsv').val(getsession());
                load_tokenfile('yubikeycsv');
                $(this).dialog('close');
            	},
				id: "button_yubikeycsv_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_yubikeycsv_cancel",
				text: "Cancel"
				}
        },
        open: do_dialog_icons
    });
	return $dialog_load_tokens_yubikeycsv ;
}
