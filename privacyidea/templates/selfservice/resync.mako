# -*- coding: utf-8 -*-

	<h1>${_("Resync OTP Token")}</h1>
	<div id='resyncform'>
	<form class="cmxform" name='myForm'>
		<fieldset>

		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken' class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		<tr>
		<td><label for=otp1>OTP 1</label></td>
		<td><input type='text' id='otp1' class="text ui-widget-content ui-corner-all" value='' /></td>		
		</tr>
		<tr>
		<td><label for=otp2>OTP 2</label></td>
		<td><input type='text' id='otp2'  class="text ui-widget-content ui-corner-all" value=''/></td>
  		</tr>
		</table>
		<button class='action-button' id='button_resync' onclick="resync(); return false;">${_("resync OTP")}</button>
		</fieldset>
	</form>
	</div> <!--resync form-->


