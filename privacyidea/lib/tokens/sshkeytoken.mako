# -*- coding: utf-8 -*-

%if c.scope == 'enroll.title' :
${_("SSH Token")}
%endif

%if c.scope == 'enroll' :

<script>
/*
 * 'typ'_get_enroll_params()
 *
 * this method is called, when the token  is submitted
 * - it will return a hash of parameters for admin/init call
 *
 */

function sshkey_get_enroll_params(){
    var params = {};
    params['type'] = 'sshkey';
    //params['serial'] = create_serial('SSHK');
    params['otpkey'] 	= $('#ssh_key').val();
	params['description'] =  $('#enroll_ssh_desc').val();

	jQuery.extend(params, add_user_data());

    return params;
}

function sshkey_changed() {
    // Change the ssh key description
    var pubkey = $('#ssh_key').val();
    var re = new RegExp("==\\s*(.*)");
    var m = re.exec(pubkey);
    var s = "";
  	if ( m ) {
  		s=m[1];
  		$('#enroll_ssh_desc').val(s);
	}
}

</script>

<p>${_("Here you can upload your public ssh key.")}</p>
<table>
<tr>
	<td><label for="ssh_key">${_("SSH public key")}</label></td>
	<td><textarea name="ssh_key" id="ssh_key" value="" class="text ui-widget-content ui-corner-all"
		cols="40" rows="8" onChange="sshkey_changed();"
		onKeyUp="sshkey_changed();"></textarea></td>
</tr>
<tr>
    <td><label for="enroll_ssh_desc" id='enroll_ssh_desc_label'>${_("Description")}</label></td>
    <!-- we read the description from the ssh key --> 
    <td><input type="text" name="enroll_ssh_desc" id="enroll_ssh_desc" 
    	value="webGUI imported" class="text"
    	size=40 /></td>
</tr>
</table>


%endif
