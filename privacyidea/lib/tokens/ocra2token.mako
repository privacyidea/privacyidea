# -*- coding: utf-8 -*-


%if c.scope == 'config.title' :
 ${_("OCRA2 settings")}
%endif


%if c.scope == 'config' :

<table>
	<tr><td><label for=ocra2_max_challenge>${_("maximum concurrent OCRA2 challenges")}</label></td>
		<td><input type="text" id="ocra2_max_challenge" maxlength="4" class=integer
			title='${_("This is the maximum concurrent challenges per OCRA2 Token.")}'/></td></tr>
	<tr><td><label for=ocra2_challenge_timeout>${_("OCRA2 challenge timeout")}</label></td>
		<td><input type="text" id="ocra2_challenge_timeout" maxlength="6"
			title='${_("After this time a challenge can not be used anymore. Valid entries are like 1D, 2H or 5M where D=day, H=hour, M=minute.")}'></td></tr>
</table>

%endif


%if c.scope == 'enroll.title' :
${_("OCRA2 - challenge/response Token")}
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

function ocra2_get_enroll_params(){
    var url = {};
    url['type'] = 'ocra2';
   	url['description'] = $('#enroll_ocra2_desc').val();
   	url['sharedsecret'] = 1;
	url['ocrasuite'] = $('#ocrasuite_algorithm').val();

    // If we got to generate the ocra2 key, we do it here:
    if  ( $('#ocra2_key_cb').attr('checked') ) {
    	url['genkey'] = 1;

    } else {
        // OTP Key
        url['otpkey'] = $('#ocra2_key').val();
    }

    jQuery.extend(url, add_user_data());

    return url;
}
</script>
<p><span id='ocra2_key_intro'>
	${_("Please enter or copy the OCRA2 key.")}</span></p>
<table>
<tr>
     <td><label for="ocra2_key" id='ocra2_key_label'>${_("OCRA2 key")}</label></td>
     <td><input type="text" name="ocra2_key" id="ocra2_key" value="" class="text ui-widget-content ui-corner-all" /></td>
</tr>
<tr>
	<td> </td>
	<td><input type='checkbox' id='ocra2_key_cb' onclick="cb_changed('ocra2_key_cb',['ocra2_key','ocra2_key_label','ocra2_key_intro']);">
	    <label for=ocra2_key_cb>${_("Generate OCRA2 key.")}</label></td>
</tr>
<tr>
	<td><label for="ocrasuite_algorithm">${_("Ocra suite")}</label></td>
	<td><select name="algorithm" id='ocrasuite_algorithm' >
	        <option selected value="OCRA-1:HOTP-SHA256-8:C-QN08">SHA256 - otplen 8 digits - numeric challenge 8 digits</option>
	        <option value="OCRA-1:HOTP-SHA256-8:C-QN08">SHA256 - otplen 8 digits - numeric challenge 8 digits</option>
	        <option value="OCRA-1:HOTP-SHA256-8:C-QA64">SHA256 - otplen 8 digits - numeric challenge 64 chars</option>
    </select></td>
</tr>
<tr>
    <td><label for="enroll_ocra2_desc" id='enroll_ocra2_desc_label'>${_("Description")}</label></td>
    <td><input type="text" name="enroll_ocra2_desc" id="enroll_ocra2_desc" value="webGUI_generated" class="text" /></td>
</tr>

</table>

% endif




%if c.scope == 'selfservice.title.enroll':
${_("Enroll your OCRA2 Token")}
%endif


%if c.scope == 'selfservice.enroll':
<script>
	jQuery.extend(jQuery.validator.messages, {
		required: "${_('required input field')}",
		minlength: "${_('minimum length must be greater than {0}')}",
		maxlength: "${_('maximum length must be lower than {0}')}",

	});

jQuery.validator.addMethod("ocra2_secret", function(value, element, param){
	var res1 = value.match(/^[a-fA-F0-9]+$/i);
	var res2 = !value;
    return  res1 || res2 ;
}, '${_("Please enter a valid init secret. It may only contain numbers and the letters A-F.")}'  );

$('#form_enroll_ocra2').validate({
	debug: true,
    rules: {
        ocra2_secret: {
            minlength: 40,
            maxlength: 64,
            number: false,
            ocra2_secret: true,
			required: function() {
            	var res = $('#ocra2_key_cb2').attr('checked') === 'undefined';
            return res;
        }
        }
    }
});

function self_ocra2_get_param()
{
	var urlparam = {};
	var typ = 'ocra2';

    if  ( $('#ocra2_key_cb2').attr('checked') ) {
    	urlparam['genkey'] = 1;
    } else {
        // OTP Key
        urlparam['otpkey'] = $('#ocra2_secret').val();
    }

	urlparam['type'] 	= typ;
	urlparam['description'] = $('#ocra2_desc').val();
	urlparam['sharedsecret'] = '1';
	return urlparam;
}

function self_ocra2_clear()
{
	$('#ocra2_secret').val('');

}
function self_ocra2_submit(){

	var ret = false;
	var params =  self_ocra2_get_param();

	if  ( $('#ocra2_key_cb2').attr('checked') === undefined && $('#form_enroll_ocra2').valid() === false) {
		alert('${_("Form data not valid.")}');
	} else {
		enroll_token( params );
		$("#ocra2_key_cb2").prop("checked", false);
		cb_changed('ocra2_key_cb2',['ocra2_secret','ocra2_key_label2']);
		ret = true;
	}
	return ret;

};

function self_ocra2_enroll_details(data) {
	return;
};

</script>
<h1>${_("Enroll your OCRA2 Token")}</h1>
<div id='enroll_ocra2_form'>
	<form class="cmxform" id='form_enroll_ocra2'>
	<fieldset>
		<table><tr>
			<td><label id='ocra2_key_label2' for='ocra2_secret'>${_("Enter seed for the new OCRA2 token:")}</label></td>
			<td><input id='ocra2_secret' name='ocra2_secret' class="required ui-widget-content ui-corner-all" min="40" maxlength='64'/></td>
		</tr><tr>
			<td><label for='ocra2_key_cb'>${_("Generate OCRA2 seed")+':'}</label></td>
			<td><input type='checkbox' name='ocra2_key_cb2' id='ocra2_key_cb2' onclick="cb_changed('ocra2_key_cb2',['ocra2_secret','ocra2_key_label2']);"></td>
		</tr><tr>
			<td><label id='ocra2_desc_label2' for='ocra2_desc'>${_("Token description")}</label></td>
			<td><input id='ocra2_desc' name='ocra2_desc' class="ui-widget-content ui-corner-all" value='self enrolled'/></td>
		</tr>
        </table>
	    <button class='action-button' id='button_enroll_ocra2'
	    	    onclick="self_ocra2_submit();">${_("enroll ocra2 token")}</button>
    </fieldset>
    </form>
</div>

%endif
<!-- -->

%if c.scope == 'selfservice.title.activate':
${_("Activate your OCRA2 Token")}
%endif


%if c.scope == 'selfservice.activate':
<h1>${_("Activate your OCRA2 Token")}</h1>

<div id='oathtokenform2'>
	<form class="cmxform" name='myForm'>
		<table>
		<p id=oath_info>
		<tr><td>${_("Your OCRA2 Token :")}      </td>
		    <td> <input type='text' class='selectedToken' class="text ui-widget-content ui-corner-all" disabled
		    	value='' id='serial2' onchange="resetOcraForm()"/></td></tr>
		<tr><td><label for=activationcode2>${_("1. Enter the activation code :")}</label> </td>
		    <td><input type='text' class="text ui-widget-content ui-corner-all" value='' id='activationcode2'/></td>
		        <input type='hidden' value='${_("Failed to enroll token!")}' id='ocra2_activate_fail'/>
		    <td><div id='qr2_activate'>
			    <button class='action-button' id='button_provisionOcra2' onclick="provisionOcra2(); return false;">
				${_("activate your OCRA2 Token")}
				</button>
				</div>
			</td>
			</tr>
		<tr><td><div id='ocra2_qr_code'></div></td></tr>
		</table>
	</form>
	<form class="cmxform" name='myForm2'>
		<table>
		<tr><td><div id='qr2_confirm1'><label for=ocra2_check>${_("2. Enter your confirmation code:")}
				</label></div> </td>
		    <td><div id='qr2_confirm2'>
		        <input type='hidden' class="text ui-widget-content ui-corner-all" id='transactionid2' value='' />
		        <input type='hidden' value='${_("OCRA rollout for token %s completed!")}' 			id='ocra2_finish_ok'  />
		        <input type='hidden' value='${_("OCRA token rollout failed! Please retry")}' 		id='ocra2_finish_fail'/>
		    	<input type='text' class="text ui-widget-content ui-corner-all"              		id='ocra2_check' value='' />
		    	</div>
		    </td>
			<td>
				<div id='qr2_finish' >
			    <button class='action-button' id='button_finishOcra2' onclick="finishOcra2(); return false;">
				${_("finish your OCRA2 Token")}
				</button>
				</div>
			</td>
			</tr>
		</div>
		<tr><td><div id='qr2_completed'></div></td></tr>
		</table>
	</form>
</div>


<script>


function provisionOcra2() {
	show_waiting();
	var acode = $('#activationcode2').val();
	var serial = $('#serial2').val();
	var activation_fail = $('#ocra2_activate_fail').val();
	var genkey = 1;

	var params = {
		'type' : 'ocra2',
		'serial' : serial,
		'genkey' : 1,
		'activationcode' : acode,
		'session' : get_selfservice_session()
	};

	$.post("/selfservice/useractivateocratoken", params, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();

		if (data.result.status == true) {
			if (data.result.value.activate == true) {
				// The token was successfully initialized and we will display the url
				showTokenlist();
				// console_log(data.result.value)
				var img = data.result.value.ocratoken.img;
				var url = data.result.value.ocratoken.url;
				var trans = data.result.value.ocratoken.transaction;
				$('#ocra2_link').attr("href", url);
				$('#ocra2_qr_code').html(img);
				$('#qr2_activate').hide();
				//$('#activationcode').attr("disabled","disabled");
				$('#transactionid2').attr("value", trans);
				$('#qr2_finish').show();
				$('#qr2_confirm1').show();
				$('#qr2_confirm2').show();
			}
		} else {
			alert(activation_fail + " \n" + data.result.error.message);
		}
	});
}


function finishOcra2() {
	show_waiting();
	var trans = $('#transactionid2').val();
	var serial = $('#serial2').val();
	var ocra_check = $('#ocra2_check').val();
	var ocra_finish_ok = $('#ocra2_finish_ok').val();
	var ocra_finish_fail = $('#ocra2_finish_fail').val();

	$.post("/selfservice/userfinshocra2token", {
		'type' : 'ocra2',
		'serial' : serial,
		'transactionid' : trans,
		'pass' : ocra_check,
		'from' : 'finishOcra2',
		'session' : get_selfservice_session()
	}, function(data, textStatus, XMLHttpRequest) {
		hide_waiting();

		//console_log(data.result)

		if (data.result.status == true) {
			// The token was successfully initialized and we will display the url
			// if not (false) display an ocra_finish_fail message for retry
			showTokenlist();
			if (data.result.value.result == false) {
				alert(ocra_finish_fail);
			} else {
				alert(String.sprintf(ocra_finish_ok, serial));
				$('#qr2_completed').show();
				$('#qr2_finish').hide();
				//$('#ocra_check').attr("disabled","disabled");
				$('#ocra2_qr_code').html('<div/>');
				$('#qr2_completed').html(String.sprintf(ocra_finish_ok, serial));
			}
		} else {
			alert("Failed to enroll token!\n" + data.result.error.message);
		}
	});

}



	$('#qr2_finish').hide();
	$('#qr2_completed').hide();
	$('#qr2_confirm1').hide();
	$('#qr2_confirm2').hide();
	$('#ocra2_check').removeAttr("disabled");
	$('#activationcode2').removeAttr("disabled");
</script>



% endif
