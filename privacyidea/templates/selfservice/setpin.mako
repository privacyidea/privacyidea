# -*- coding: utf-8 -*-

<h1>${_("Reset OTP PIN")}</h1>

<div id='passwordform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
	
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken' class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		<tr>
		<td><label for=pin1>PIN</label></td>
		<td><input autocomplete="off" type='password' onkeyup="checkpins('pin1', 'pin2');" id='pin1' class="text ui-widget-content ui-corner-all" value='' /></td>
		</tr>
		<tr>
		<td><label for=pin2>${_("repeat PIN")}</label></td>
		<td><input autocomplete="off" type='password' onkeyup="checkpins('pin1', 'pin2');" id='pin2' class="text ui-widget-content ui-corner-all" value=''/></td>
  		</tr>
		</table>
		<button class='action-button' id='button_setpin' onclick="setpin(); return false;">${_("set PIN")}</button>
	<input type='hidden' value='${_("The passwords do not match!")}' 		id='setpin_fail'/>
		<input type='hidden' value='${_("Error setting PIN: ")}' 			id='setpin_error'/>
		<input type='hidden' value='${_("PIN set successfully")}'			id='setpin_ok'/>
		</fieldset>
	</form>
</div>
