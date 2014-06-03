# -*- coding: utf-8 -*-
<h1>${_("Delete OTP Token")}</h1>

<div id='deleteform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		</table>
		<button class='action-button' id='button_delete' onclick="token_delete(); return false;">${_("delete Token")}</button>
		</fieldset>
	</form>
</div>
