# -*- coding: utf-8 -*-

<h1>${_("Reset mOTP PIN")}</h1>

${_("This resets the mOTP PIN, which is the PIN that is entered in the motp application on your phone.")}
<div id='passwordform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
	
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken' class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		<tr>
		<td><label for=mpin1>mOTP PIN</label></td>
		<td><input type='password' autocomplete=off onkeyup="checkpins('mpin1', 'mpin2');" id='mpin1' class="text ui-widget-content ui-corner-all" value='' /></td>		
		</tr>
		<tr>
		<td><label for=mpin2>${_("repeat mOTP PIN")}</label></td>
		<td><input type='password' autocomplete=off onkeyup="checkpins('mpin1', 'mpin2');" id='mpin2' class="text ui-widget-content ui-corner-all" value=''/></td>
  		</tr>
		</table>
		<button class='action-button' id='button_setmpin' onclick="setmpin(); return false;">${_("set mOTP PIN")}</button>
		<input type='hidden' value='${_("The passwords do not match!")}' 	id='setpin_fail'/>
		<input type='hidden' value='${_("Error setting mOTP PIN: ")}'		id='setpin_error'/>
		<input type='hidden' value='${_("mOTP PIN set successfully")}'		id='setpin_ok'/>		
		</fieldset>	
	</form>
</div>
