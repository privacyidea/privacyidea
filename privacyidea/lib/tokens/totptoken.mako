# -*- coding: utf-8 -*-


%if c.scope == 'config.title' :
 ${_("TOTP Token Settings")}
%endif


%if c.scope == 'config' :
<script>

/*
 * 'typ'_get_config_val()
 *
 * this method is called, when the token config dialog is opened
 * - it contains the mapping of config entries to the form id
 * - according to the Config entries, the form entries will be filled
 *
 */


function totp_get_config_val(){
	var id_map = {};

    id_map['totp.timeStep']   = 'totp_timeStep';
    id_map['totp.timeShift']  = 'totp_timeShift';
    id_map['totp.timeWindow'] = 'totp_timeWindow';

	return id_map;

}

/*
 * 'typ'_get_config_params()
 *
 * this method is called, when the token config is submitted
 * - it will return a hash of parameters for system/setConfig call
 *
 */
function totp_get_config_params(){

	var url_params ={};

    url_params['totp.timeShift'] 	= $('#totp_timeShift').val();
    url_params['totp.timeStep'] 	= $('#totp_timeStep').val();
    url_params['totp.timeWindow'] 	= $('#totp_timeWindow').val();

	return url_params;
}

</script>

<fieldset>
	<legend>${_("TOTP settings")}</legend>
	<table>
		<tr><td><label for='totp_timeStep'> ${_("TOTP time Step")}: </label></td>
		<td><input type="text" name="tot_timeStep" class="required"  id="totp_timeStep" size="2" maxlength="2"
			title='${_("This is the time step for time based tokens. Usually this is 30 or 60.")}'> sec</td></tr>
		<tr><td><label for='totp_timeShift'> ${_("TOTP time Shift")}: </label></td>
		<td><input type="text" name="totp_timeShift" class="required"  id="totp_timeShift" size="5" maxlength="5"
			title='${_("This is the default time shift of the server. This should be 0.")}'> sec</td></tr>
		<tr><td><label for='totp_timeWindow'> ${_("TOTP time window")}: </label></td>
		<td><input type="text" name="totp_timeWindow" class="required"  id="totp_timeWindow" size="5" maxlength="5"
			title='${_("This is the time privacyIDEA will calculate before and after the current time. A reasonable value is 300.")}'> sec</td></tr>
	</table>
</fieldset>

%endif


%if c.scope == 'enroll.title' :
${_("HMAC time based")}
%endif

%if c.scope == 'enroll' :
<script>

/*
 * 'typ'_enroll_setup_defaults()
 *
 * this method is called when the gui becomes visible,
 * and gets the privacyidea config as a parameter, so that the
 * gui could be prepared with the server defaults
 *
 *
 */
function totp_enroll_setup_defaults(config){
	for (var key in config) {
		if (key == "totp.timeStep")
		{
			$totp_timeStep = config["totp.timeStep"];
			$('#totp_timestep').val($totp_timeStep);
		}
	}
	$('#totp_key').val('');
}
/*
 * 'typ'_get_enroll_params()
 *
 * this method is called, when the token  is submitted
 * - it will return a hash of parameters for admin/init call
 *
 */
function totp_get_enroll_params(){
    var params = {};
    params['type'] = 'totp';
   	params['description'] = $('#enroll_totp_desc').val();

    if  ( $('#totp_key_cb').attr('checked') ) {
		params['genkey']	= 1;
		params['hashlib']	= 'sha1';
		params['otplen']	= 6;
    } else {
        // OTP Key
    	params['otpkey'] 	= $('#totp_key').val();
    }
    params['timeStep'] 	= $('#totp_timestep').val();

	jQuery.extend(params, add_user_data());

    return params;
}
</script>
<p>${_("Please enter or copy the HMAC key.")}</p>
<table><tr>
<td><label for="totp_key" id='totp_key_label'>${_("HMAC key")}</label></td>
<td><input type="text" name="totp_key" id="totp_key" value="" class="text ui-widget-content ui-corner-all" /></td>
</tr>
<tr><td> </td><td><input type='checkbox' id='totp_key_cb' onclick="cb_changed('totp_key_cb',['totp_key','totp_key_label','totp_key_intro']);">
<label for=totp_key_cb>${_("Generate HMAC key.")}</label></td>
</tr>

<tr>
<td><label for='totp_timestep'>${_("timeStep")}</label></td>
<td>
	<select id='totp_timestep'>
	<option value='60' >60 ${_("seconds")}</option>
	<option value='30' >30 ${_("seconds")}</option>
	</select></td>
</tr>
<tr>
    <td><label for="enroll_totp_desc" id='enroll_totp_desc_label'>${_("Description")}</label></td>
    <td><input type="text" name="enroll_totp_desc" id="enroll_totp_desc" value="webGUI_generated" class="text" /></td>
</tr>
</table>

% endif


%if c.scope == 'selfservice.title.enroll':
${_("Register totp")}
%endif


%if c.scope == 'selfservice.enroll':
<script>
	jQuery.extend(jQuery.validator.messages, {
		required:  "${_('required input field')}",
		minlength: "${_('minimum length must be greater than {0}')}",
		maxlength: "${_('maximum length must be lower than {0}')}",
		range: '${_("Please enter a valid init secret. It may only contain numbers and the letters A-F.")}',
	});

jQuery.validator.addMethod("totp_secret", function(value, element, param){
	var res1 = value.match(/^[a-fA-F0-9]+$/i);
	var res2 = !value;
    return  res1 || res2 ;
}, '${_("Please enter a valid init secret. It may only contain numbers and the letters A-F.")}' );

$('#form_enroll_totp').validate({
	debug: true,
    rules: {
        totp_secret: {
            minlength: 40,
            maxlength: 64,
            number: false,
            totp_secret: true,
			required: function() {
            	var res = $('#totp_key_cb2').attr('checked') === 'undefined';
            return res;
        }
        }
    }
});

function self_totp_get_param()
{
	var urlparam = {};
	var typ = 'totp';

    if  ( $('#totp_key_cb2').attr('checked') ) {
    	urlparam['genkey'] = 1;
    } else {
        // OTP Key
        urlparam['otpkey'] = $('#totp_secret').val();
    }

	urlparam['type'] 	= typ;
	urlparam['hashlib'] = $('#totp_hashlib').val();
	urlparam['otplen'] 	= 6;
	urlparam['timestep'] 	= $('#totp_timestep').val();
	urlparam['description'] = $("#totp_self_desc").val();

	return urlparam;
}

function self_totp_clear()
{
	$('#totp_secret').val('');

}
function self_totp_submit(){

	var ret = false;
	var params =  self_totp_get_param();

	if  ( $('#totp_key_cb2').attr('checked') === undefined && $('#form_enroll_totp').valid() === false) {
		alert('${_("Form data not valid.")}');
	} else {
		enroll_token( params );
		$("#totp_key_cb2").prop("checked", false);
		cb_changed('totp_key_cb2',['totp_secret','totp_key_label2']);
		ret = true;
	}
	return ret;

}
</script>
<h1>${_("Enroll your TOTP Token")}</h1>
<div id='enroll_totp_form'>
	<form class="cmxform" id='form_enroll_totp'>
	<fieldset>
		<table><tr>
			<td><label for='totp_key_cb'>${_("Generate HMAC key")}</label></td>
			<td><input type='checkbox' name='totp_key_cb2' id='totp_key_cb2' onclick="cb_changed('totp_key_cb2',['totp_secret','totp_key_label2']);"></td>
		</tr><tr>
			<td><label id='totp_key_label2' for='totp_secret'>${_("Seed for HOTP token")}</label></td>
			<td><input id='totp_secret' name='totp_secret' class="required ui-widget-content ui-corner-all" min="40" maxlength='64'/></td>
		</tr>
		%if c.totp_hashlib == 1:
			<input type=hidden id='totp_hashlib' value='sha1'>
		%endif
		%if c.totp_hashlib == 2:
			<input type=hidden id='totp_hashlib' value='sha256'>
		%endif
		%if c.totp_hashlib == -1:
		<tr>
		<td><label for='totp_hashlib'>${_("hashlib")}</label></td>
		<td><select id='totp_hashlib'>
			<option value='sha1' selected>sha1</option>
			<option value='sha256'>sha256</option>
			</select></td>
		</tr>
		%endif

		%if c.totp_timestep == -1:
			<tr>
			<td><label for='totp_timestep'>${_("timeStep")}</label></td>
			<td><select id='totp_timestep'>
				<option value='30' selected>30 ${_("seconds")}</option>
				<option value='60'>60 ${_("seconds")}</option>
				</select></td>
			</tr>
		%else:
			<input type='hidden' id='totp_timestep' value='${c.totp_timestep}'>
		%endif
		<tr>
		    <td><label for="totp_self_desc" id='totp_self_desc_label'>${_("Description")}</label></td>
		    <td><input type="text" name="totp_self_desc" id="totp_self_desc" value="self enrolled" class="text" /></td>
		</tr>
        </table>
	    <button class='action-button' id='button_enroll_totp'
	    	    onclick="self_totp_submit();">${_("enroll TOTP Token")}</button>

    </fieldset>
    </form>
</div>

% endif
