# -*- coding: utf-8 -*-
<h1>${_("Provision your OATH Token")}</h1>

<div id='oathtokenform'>
	<form class="cmxform" name='myForm'> 
		<fieldset>
		<p id=oath_info>
		${_("1. You first need to install the oathtoken to your iPhone.")}
		<ul>
		<li><a href='http://itunes.apple.com/us/app/oath-token/id364017137?mt=8' target='extern'>${_("link for iPhone")}</a><br>
			${_("Using the QR Code you can directly go to install the oath token on your iPhone.")}     
		     <span id=qr_code_iphone_download_oath></span>
			</li>
		</ul>
		<p>${_("2. Then you may create a profile.")}<br>
		<button class='action-button' id='button_provisionOath' onclick="provisionOath(); return false;">
			${_("enroll OATH Token")}
		</button>
		</p>
		<div id="provisionresultDiv">
			<p>${_("3.")} <b>oathtoken</b> ${_("successfully created!")}</p>
			<p>${_("Click on this link to install the oathtoken profile to your iPhone:")}
				<a id=oath_link>${_("install profile")}</a>
			</p>
			<p>${_("Or you can scan the QR code below with your iPhone to import the secret.")}</p>
			<p><span id=oath_qr_code></span></p>
		</div>
		</fieldset>
	</form>
</div>

<script>
	    $('#provisionresultDiv').hide();
	    $('#qr_code_iphone_download_oath').show();
	   	$('#qr_code_iphone_download_oath').html(generate_qrcode(10,"http://itunes.apple.com/us/app/oath-token/id364017137?mt=8"));
</script>
