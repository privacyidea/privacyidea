# -*- coding: utf-8 -*-
<h1>${_("Enable OTP Token")}</h1>

<div id='enableform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		</table>
		<button class='action-button' id='button_enable' onclick="enable(); return false;">${_("enable Token")}</button>
		</fieldset>
	</form>
</div>
