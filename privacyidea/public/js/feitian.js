function create_feitian_dialog() {
    var $dialog_load_tokens_feitian = $('#dialog_import_feitian').dialog({
        autoOpen: false,
        title: 'Feitian XML Token file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': {click: function(){
            	$('#loadtokens_session_feit').val(getsession());
                load_tokenfile('feitian');
                $(this).dialog('close');
            	},
				id: "button_feitian_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_feitian_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_feitian();
        	do_dialog_icons();
        }
    });
    return $dialog_load_tokens_feitian;
}