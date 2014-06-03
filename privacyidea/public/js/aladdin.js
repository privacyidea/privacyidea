function create_aladdin_dialog() {
 var $dialog_load_tokens_aladdin = $('#dialog_import_safenet').dialog({
        autoOpen: false,
        title: 'Aladdin XML Token file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': {click: function(){
            	$('#loadtokens_session_aladdin').val(getsession());
                load_tokenfile('aladdin-xml');
                $(this).dialog('close');
            	},
				id: "button_aladdin_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_aladdin_cancel",
				text: "Cancel"
				}
        },
        open: function() {
        	translate_import_safenet();
        	do_dialog_icons();
        }
    });
	return $dialog_load_tokens_aladdin ;
}
