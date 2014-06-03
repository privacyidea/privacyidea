# -*- coding: utf-8 -*-

<script>
	jQuery.validator.addMethod("phone", function(value, element, param){
        return value.match(/^[+0-9\/\ ]+$/i);
    }, "Please enter a valid phone number. It may only contain numbers and + or /.");
	
	$('#form_registersms').validate({
        rules: {
            mobilephone: {
                required: true,
                minlength: 6,
                number: false,
                phone: true
            }
        }
	});

</script>

<h1>${_("Register your SMS OTP Token / mobileTAN")}</h1>
<div id='registersmsform'>
	<form class="cmxform" id='form_registersms'>
	<fieldset>
		<table>
		<tr>
		<td><label for=mobilephone>${_("Your mobile phone number")}</label></td>
		<td><input id='mobilephone' 
					name='mobilephone' 
					class="required ui-widget-content ui-corner-all" 
					value='${c.phonenumber}'/>
		</td>		
		</tr>
        <tr>
        </table>
        <button class='action-button' id='button_register_sms' onclick="register_sms(); return false;">${_("register SMS Token")}</button>
    </fieldset>
    </form>
</div>

