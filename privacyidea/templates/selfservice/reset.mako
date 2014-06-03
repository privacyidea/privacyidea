# -*- coding: utf-8 -*-
<h1>${_("Reset Failcounter")}</h1>

<div id='resetform'>
	<form class="cmxform" name='myForm'>
		<fieldset>
		<table>
		<tr>
		<td>${_("selected Token")}</td>
		<td><input type='text' class='selectedToken'  class="text ui-widget-content ui-corner-all" disabled value='' /></td>
		</tr>
		</table>
		<button class='action-button' id='button_reset' onclick="reset_failcounter(); return false;">${_("reset Failcounter")}</button>
		</fieldset>
	</form>
</div>
