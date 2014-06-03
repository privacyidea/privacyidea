function pskc_type_changed(){
    var $tokentype = $("#pskc_type").val();
    switch ($tokentype) {
        case "plain":
            $('#pskc_password').hide()
            $('#pskc_preshared').hide()
            break;
        case "password":
            $('#pskc_preshared').hide()
            $('#pskc_password').show()
            break;
        case "key":
            $('#pskc_preshared').show()
            $('#pskc_password').hide()
            break;
    }
}


function create_pskc_dialog() {
    var $dialog_load_tokens_pskc = $('#dialog_import_pskc').dialog({
        autoOpen: false,
        title: 'PSKC Key file',
        width: 600,
        modal: true,
        buttons: {
            'load token file': { click: function(){
            	$('#loadtokens_session_pskc').val(getsession());
                load_tokenfile('pskc');
                $(this).dialog('close');
            	},
				id: "button_pskc_load",
				text: "load token file"
				},
            Cancel: {click: function(){
                $(this).dialog('close');
            	},
				id: "button_pskc_cancel",
				text: "Cancel"
				}
        },
        open: function(){
        	translate_import_pskc();
        	do_dialog_icons();
        }
    });
 	return $dialog_load_tokens_pskc;
}

$(document).ready(function(){
    $('#pskc_password').hide()
    $('#pskc_preshared').hide()
});
