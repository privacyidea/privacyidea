# -*- coding: utf-8 -*-

%if c.scope == 'config.title' :
${_("E-mail OTP token")}
%endif


%if c.scope == 'config' :
<!-- #################### E-mail provider ################### -->
<script>
/*
 * 'typ'_get_config_val()
 *
 * this method is called, when the token config dialog is opened
 * - it contains the mapping of config entries to the form id
 * - according to the Config entries, the form entries will be filled
 *
 */
function email_get_config_val(){
	var ret = {};
	ret['EmailProvider'] = 'c_email_provider';
	ret['EmailProviderConfig'] = 'c_email_provider_config';
	ret['EmailChallengeValidityTime'] = 'c_email_challenge_validity';
	ret['EmailBlockingTimeout'] = 'c_email_blocking';
	return ret;
}
/*
 * 'typ'_get_config_params()
 *
 * this method is called, when the token config is submitted
 * - it will return a hash of parameters for system/setConfig call
 *
 */
function email_get_config_params(){
	var ret = {};
	ret['EmailProvider'] = $('#c_email_provider').val();
	ret['EmailProviderConfig'] = $('#c_email_provider_config').val();
	ret['EmailProviderConfig.type'] = 'password';
	ret['EmailChallengeValidityTime'] = $('#c_email_challenge_validity').val();
	ret['EmailBlockingTimeout'] = $('#c_email_blocking').val();
	return ret;
}

$(document).ready(function () {
    $("#form_emailconfig").validate();
});
</script>

<form class="cmxform" id="form_emailconfig">
<fieldset>
    <legend>${_("E-mail provider config")}</legend>
    <table>
        <tr>
	        <td><label for="c_email_provider">${_("E-mail provider")}</label>: </td>
	        <td><input type="text" name="email_provider" class="required"  id="c_email_provider" size="37" maxlength="80"></td>
        </tr>
        <tr>
	        <td><label for="c_email_provider_config">${_("E-mail provider config")}</label>: </td>
	        <td><textarea name="email_provider_config" class="required"  id="c_email_provider_config" cols='35' rows='6' maxlength="400">{}	        	
	        </textarea></td>
        </tr>
        <tr>
	        <td><label for="c_email_challenge_validity">${_("E-mail challenge validity (sec)")}</label>: </td>
	        <td><input type="text" name="email_challenge_validity" class="required"  id="c_email_challenge_validity" size="5" maxlength="5"></td>
        </tr>
        <tr>
	        <td><label for="c_email_blocking">${_("Time between e-mails (sec)")}</label>: </td>
	        <td><input type="text" name="email_blocking" class="required"  id="c_email_blocking" size="5" maxlength="5" value"30"></td>
	    </tr>
    </table>
</fieldset>
</form>

%endif

%if c.scope == 'enroll.title' :
${_("E-mail token")}
%endif

%if c.scope == 'enroll' :
<script>
function email_enroll_setup_defaults(config){
	// in case we enroll e-mail otp, we get the e-mail address of the user
	email_addresses = get_selected_email();
	$('#email_address').val($.trim(email_addresses[0]));
}

/*
 * 'typ'_get_enroll_params()
 *
 * this method is called, when the token  is submitted
 * - it will return a hash of parameters for admin/init call
 *
 */
function email_get_enroll_params(){
    var params = {};
    // phone number
    params['email_address']	= $('#email_address').val();
    params['description'] = $('#email_address').val() + " " + $('#enroll_email_desc').val();
    jQuery.extend(params, add_user_data());
    return params;
}
</script>

<table><tr>
	<td><label for="email_address">${_("E-mail address")}</label></td>
	<td><input type="text" name="email_address" id="email_address" value="" class="text ui-widget-content ui-corner-all"></td>
</tr><tr>
    <td><label for="enroll_email_desc" id='enroll_email_desc_label'>${_("Description")}</label></td>
    <td><input type="text" name="enroll_email_desc" id="enroll_email_desc" value="webGUI_generated" class="text" /></td>
</tr>
</table>

%endif

