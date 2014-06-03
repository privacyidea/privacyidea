# -*- coding: utf-8 -*-
<h1>${_("get OTP values from Token")}</h1>

<div id='getotpform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		<tr>
		<td><label for=otp_count>${_("Number of OTP values to retrieve")}:</label> </td>
		<td><input type='text' id='otp_count' class="text ui-widget-content ui-corner-all" value='' /></td>		
		</tr>
		</table>
		<button class='action-button' id='button_getotp' onclick="getotp(); return false;">${_("get OTP values")}</button>
		</fieldset>
	</form>
</div>
