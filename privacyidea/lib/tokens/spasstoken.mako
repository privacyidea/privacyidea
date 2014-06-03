# -*- coding: utf-8 -*-

%if c.scope == 'enroll.title' :
${_("Simple Pass Token")}
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

function spass_get_enroll_params(){
    var params = {};
    params['type'] = 'spass';
    params['otpkey'] = "1234";
	params['description'] =  $('#enroll_spass_desc').val();

	jQuery.extend(params, add_user_data());

    return params;
}
</script>

<p>${_("The Simple Pass token will not require any one time password component.")}
${_("Anyway, you can set an OTP PIN, so that using this token the user can "+
"authenticate always and only with this fixed PIN.")}</p>

<table>
<tr>
    <td><label for="enroll_spass_desc" id='enroll_spass_desc_label'>${_("Description")}</label></td>
    <td><input type="text" name="enroll_spass_desc" id="enroll_spass_desc" value="webGUI_generated" class="text" /></td>
</tr>
</table>

%endif
