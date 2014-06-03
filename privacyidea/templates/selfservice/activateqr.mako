# -*- coding: utf-8 -*-

<h1>${_("Activate your OCRA Token")}</h1>


<div id='activateqrform'>
	<form class="cmxform" name='myForm'>

		<fieldset>
		<table>
		<p id=oath_info>
		<tr><td>${_("Your OCRA Token :")}      </td>
		    <td> <input type='text' class='selectedToken' class="text ui-widget-content ui-corner-all" disabled
		    	value='' id='serial' onchange="resetOcraForm()"/></td></tr>
		<tr><td><label for=activationcode>${_("1. Enter the activation code :")}</label> </td>
		    <td><input type='text' class="text ui-widget-content ui-corner-all" value='' id='activationcode'/></td>
		        <input type='hidden' value='${_("Failed to enroll token!")}' id='ocra_activate_fail'/>
		    <td><div id='qr_activate'>
			    <button class='action-button' id='button_provisionOcra' onclick="provisionOcra(); return false;">
				${_("activate your OCRA Token")}
				</button>
				</div>
			</td>
			</tr>
		<tr><td><div id='ocra_qr_code'></div></td></tr>
		</table>
	</form>
	<form class="cmxform" name='myForm2'>
		<table>
		<tr><td><div id='qr_confirm1'><label for=ocra_check>${_("2. Enter your confirmation code:")}
				</label></div> </td>
		    <td><div id='qr_confirm2'>
		        <input type='hidden' class="text ui-widget-content ui-corner-all" id='transactionid' value='' />
		        <input type='hidden' value='${_("OCRA rollout for token %s completed!")}' 			id='ocra_finish_ok'  />
		        <input type='hidden' value='${_("OCRA token rollout failed! Please retry")}' 		id='ocra_finish_fail'/>
		    	<input type='text' class="text ui-widget-content ui-corner-all"              		id='ocra_check' value='' />
		    	</div>
		    </td>
			<td>
				<div id=qr_finish >
			    <button class='action-button' id='button_finishOcra' onclick="finishOcra(); return false;">
				${_("finish your OCRA Token")}
				</button>
				</div>
			</td>
			</tr>
		</div>
		<tr><td><div id='qr_completed'></div></td></tr>
		</p>
		</table>
		</fieldset>
	</form>
</div>


<script>
	$('#qr_finish').hide();
	$('#qr_completed').hide();
	$('#qr_confirm1').hide();
	$('#qr_confirm2').hide();
	$('#ocra_check').removeAttr("disabled");
	$('#activationcode').removeAttr("disabled");
</script>
