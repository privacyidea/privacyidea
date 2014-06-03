# -*- coding: utf-8 -*-


%if c.scope == 'config.title' :
 ${_("HMAC Token Settings")}
%endif


%if c.scope == 'config' :
%endif


%if c.scope == 'enroll.title' :
${_("HMAC eventbased")}
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

function hmac_get_enroll_params(){
    var url = {};
    url['type'] = 'hmac';
   	url['description'] = $('#enroll_hmac_desc').val();

    // If we got to generate the hmac key, we do it here:
    if  ( $('#hmac_key_cb').attr('checked') ) {
    	url['genkey'] = 1;

    } else {
        // OTP Key
        url['otpkey'] = $('#hmac_key').val();
    }

    jQuery.extend(url, add_user_data());

    url['hashlib']	= $('#hmac_algorithm').val();
	url['otplen']	= $('#hmac_otplen').val();


    return url;
}
</script>

<p><span id='hmac_key_intro'>
	${_("Please enter or copy the HMAC key.")}</span></p>
<table><tr>
	<td><label for="hmac_key" id='hmac_key_label'>${_("HMAC key")}</label></td>
	<td><input type="text" name="hmac_key" id="hmac_key" value="" class="text ui-widget-content ui-corner-all" /></td>
</tr><tr>
	<td> </td><td><input type='checkbox' id='hmac_key_cb' onclick="cb_changed('hmac_key_cb',['hmac_key','hmac_key_label','hmac_key_intro']);">
	<label for=hmac_key_cb>${_("Generate HMAC key.")}</label></td>
</tr><tr>
	<td><label for="hmac_otplen">${_("OTP Length")}</label></td>
	<td><select name="pintype" id="hmac_otplen">
			<option  value="4">4</option>
			<option  selected value="6">6</option>
			<option  value="8">8</option>
			<option  value="10">10</option>
			<option  value="12">12</option>
	</select></td>

</tr><tr>
	<td><label for="hmac_algorithm">${_("Hash algorithm")}</label></td>
	<td><select name="algorithm" id='hmac_algorithm' >
	        <option selected value="sha1">sha1</option>
	        <option value="sha256">sha256</option>
	        <option value="sha512">sha512</option>
    </select></td>
</tr>
<tr>
    <td><label for="enroll_hmac_desc" id='enroll_hmac_desc_label'>${_("Description")}</label></td>
    <td><input type="text" name="enroll_hmac_desc" id="enroll_hmac_desc" value="webGUI_generated" class="text" /></td>
</tr>

</table>

% endif




%if c.scope == 'selfservice.title.enroll':
${_("Enroll your HOTP Token")}
%endif


%if c.scope == 'selfservice.enroll':
<script>
	jQuery.extend(jQuery.validator.messages, {
		required: "${_('required input field')}",
		minlength: "${_('minimum length must be greater than {0}')}",
		maxlength: "${_('maximum length must be lower than {0}')}",

	});

jQuery.validator.addMethod("hmac_secret", function(value, element, param){
	var res1 = value.match(/^[a-fA-F0-9]+$/i);
	var res2 = !value;
    return  res1 || res2 ;
}, '${_("Please enter a valid init secret. It may only contain numbers and the letters A-F.")}'  );

$('#form_enroll_hmac').validate({
	debug: true,
    rules: {
        hmac_secret: {
            minlength: 40,
            maxlength: 64,
            number: false,
            hmac_secret: true,
			required: function() {
            	var res = $('#hmac_key_cb2').attr('checked') === 'undefined';
            return res;
        }
        }
    }
});

function self_hmac_get_param()
{
	var urlparam = {};
	var typ = 'hmac';

    if  ( $('#hmac_key_cb2').attr('checked') ) {
    	urlparam['genkey'] = 1;
    } else {
        // OTP Key
        urlparam['otpkey'] = $('#hmac_secret').val();
    }

	urlparam['type'] 	= typ;
	urlparam['hashlib'] = $('#hmac_hashlib').val();
	urlparam['otplen'] 	= 6;
	urlparam['description'] = $("#hmac_self_desc").val();

	return urlparam;
}

function self_hmac_clear()
{
	$('#hmac_secret').val('');

}
function self_hmac_submit(){

	var ret = false;
	var params =  self_hmac_get_param();

	if  ( $('#hmac_key_cb2').attr('checked') === undefined && $('#form_enroll_hmac').valid() === false) {
		alert('${_("Form data not valid.")}');
	} else {
		enroll_token( params );
		$("#hmac_key_cb2").prop("checked", false);
		cb_changed('hmac_key_cb2',['hmac_secret','hmac_key_label2']);
		ret = true;
	}
	return ret;

}
</script>
<h1>${_("Enroll your HOTP Token")}</h1>
<div id='enroll_hmac_form'>
	<form class="cmxform" id='form_enroll_hmac'>
	<fieldset>
		<table><tr>
			<td><label for='hmac_key_cb'>${_("Generate HMAC key.")+':'}</label></td>
			<td><input type='checkbox' name='hmac_key_cb2' id='hmac_key_cb2' onclick="cb_changed('hmac_key_cb2',['hmac_secret','hmac_key_label2']);"></td>
		</tr><tr>
			<td><label id='hmac_key_label2' for='hmac_secret'>${_("Seed for HOTP token")}</label></td>
			<td><input id='hmac_secret' name='hmac_secret' class="required ui-widget-content ui-corner-all" min="40" maxlength='64'/></td>
		</tr>
		%if c.hmac_hashlib == 1:
			<input type=hidden id='hmac_hashlib' name='hmac_hashlib' value='sha1'>
		%endif
		%if c.hmac_hashlib == 2:
			<input type=hidden id='hmac_hashlib' name='hmac_hashlib' value='sha256'>
		%endif
		%if c.hmac_hashlib == -1:
		<tr>
		<td><label for='hmac_hashlib'>${_("hashlib")}</label></td>
		<td><select id='hmac_hashlib' name='hmac_hashlib'>
			<option value='sha1' selected>sha1</option>
			<option value='sha256'>sha256</option>
			</select></td>
		</tr>
		%endif
		<tr>
		    <td><label for="hmac_self_desc" id='hmac_self_desc_label'>${_("Description")}</label></td>
		    <td><input type="text" name="hmac_self_desc" id="hmac_self_desc" value="self enrolled" class="text" /></td>
		</tr>

        </table>
	    <button class='action-button' id='button_enroll_hmac'
	    	    onclick="self_hmac_submit();">${_("enroll hmac token")}</button>

    </fieldset>
    </form>
</div>

% endif
