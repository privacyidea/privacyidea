# -*- coding: utf-8 -*-
<h1>${_("Provision your Google Authenticator")}</h1>

<div id='googletokenform'>
	<form class="cmxform" name='myForm'> 
		<fieldset>
		<p>
		${_("1. You first need to install the google authenticator to your Android or iPhone.")}
		<ul>
		<li><a href='https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2' target='extern'>${_("link for Android")}</a></li>
		<li><a href='http://itunes.apple.com/de/app/google-authenticator/id388497605?mt=8' target='extern'>${_("link for iPhone")}</a><br>
			${_("Using the QR code you can directly go to install the google authenticator on your iPhone.")}     
		     <span id=qr_code_iphone_download></span>
			</li>
		</ul>
		<p>${_("2. Then you may create a profile.")}<br>
			<label for=google_type>Choose a profile type:</label> 
			<select id=google_type>
				% if 'webprovisionGOOGLE' in c.actions:
				<option value=hotp>${_("event based")}</option>
				%endif
				% if 'webprovisionGOOGLEtime' in c.actions:
				<option value=totp>${_("time based")}</option>
				%endif
			</select>
		<button class='action-button' id='button_provisionGoogle' onclick="provisionGoogle(); return false;">
			${_("enroll Google Authenticator")}
		</button>
		</p>
		<div id="provisionGoogleResultDiv">
			<p>${_("3.")} <b>${_("Google Authenticator")}</b> ${_("successfully created!")}</p>
			<p>${_("Click on this link to install the profile to your Android or iPhone:")}
				 <a id=google_link>${_("install profile")}</a>
			</p>
			<p>${_("Or you can scan the QR code below with your Android phone to import the secret.")}</p>
			<p><span id=google_qr_code></span></p>
		</div>
		</fieldset>
	</form>
</div>

<script>
	   	$('#provisionGoogleResultDiv').hide();
	   	$('#qr_code_iphone_download').show();
	   	$('#qr_code_iphone_download').html(generate_qrcode(10,"http://itunes.apple.com/de/app/google-authenticator/id388497605?mt=8"));
</script>
