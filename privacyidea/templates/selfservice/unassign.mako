# -*- coding: utf-8 -*-
<h1>${_("Unassign OTP Token")}</h1>

<div id='unassignform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		</table>
		<button class='action-button' id='button_unassign' onclick="unassign(); return false;">${_("unassign Token")}</button>
		</fieldset>
	</form>
</div>
