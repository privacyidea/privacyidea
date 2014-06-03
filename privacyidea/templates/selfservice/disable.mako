# -*- coding: utf-8 -*-
<h1>${_("Disable OTP Token")}</h1>

<div id='disableform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		</table>
		<button class='action-button' id='button_disable' onclick="disable(); return false;">${_("disable Token")}</button>
		</fieldset>
	</form>
</div>
