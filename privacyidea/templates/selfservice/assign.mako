# -*- coding: utf-8 -*-

<h1>${_("Assign OTP Token")}</h1>
<div id='assignform'>
	<form class="cmxform" name='myForm'>
	<fieldset>
		%if 'getserial' in c.actions:
		${_("You may either assign the token by entering the serial number or you can enter an OTP value of the token and the system will try to identify the token for you.")}
		%endif
		<table>
		%if 'getserial' in c.actions:
		<tr>
		<td><label for=otp_serial>${_("The OTP value of the Token to assign")}</label></td>
		<td><input type='text' id='otp_serial' class='text ui-widget-content ui-corner-all' value='' size="20" maxlength="20"/>
			<button class='action-button' id='button_otp_serial' onclick="getserial(); return false">
				${_("determine serial number")}
			</button>
		</td>	
		</tr>
		
		%endif
		<tr>
		<td><label for=serial>${_("Serialnumber of new Token")}</label></td>
		<td><input type='text' id='assign_serial' class="text ui-widget-content ui-corner-all" value='' /></td>		
		</tr>
		</table>
		<button class='action-button' id='button_assign' onclick="assign(); return false">${_("assign Token")}</button>
	</fieldset>
	</form>
</div>

