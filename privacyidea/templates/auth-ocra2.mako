# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>privacyIDEA OCRA2 Auth testing</title>
</head>

<%inherit file="auth-base.mako"/>

<div id="sidebar">
<p>
${_("Here you may try to authenticate using your OCRA OTP token.")}
</p>
<p>
${_('Enter your username, the OCRA2 Token PIN and the input for the challenge.')}
${_('By submit this will generate an QR image, that could be scaned with your OCRA2 Token reader.')}
${_('Enter for verification the OTP value in the lower form.')}
</p>
</div> <!-- sidebar -->


<div id="main">
<h1>${_('OCRA2 Login')}</h1>
<div id='register'>
		<table>
		<tr><td>
        <form class="cmxform"  id="form_challenge_ocra2">
        	<frameset name=login>
                <table><tr>
                	<td><h2>${_('Submit a challenge:')}</h2></td>
                </tr><tr>
                <td>${_('username')}</td>
                <td><input type='text' id='user' name="user" maxlength="200"  class="required"></td>
                </tr><tr>
                <td>${_('Pin')}</td>
                <td><input type='text' id='pin' name="pass" maxlength="200"  class="required"></td>
                </tr><tr>
	                <td>${_('challenge')}</td>
	                <td><textarea cols="40" rows="6" id='challenge' class="required"> </textarea></td>
                </tr><tr>
				<td> </td>
				        <td>
				        <input type="submit" value="${_('get challenge')}"/>


                </tr></table>
                </frameset>
              	</form>

		</td><td rowspan="3">
		<div id='display'> </div>
        </td>
        </tr><tr>
        	<td>
        		<h2>${_('Scan your challenge and get your OTP:')}</h2>
        	</td>
		</tr><tr>
        <td>
        <form class="cmxform"  id="form_login_ocra2">
        	<frameset name=login>
                <table><tr>
				    <td><h2>${_('Login:')}</h2></td>
                </tr><tr>
	                <td>${_('username')}</td>
	                <td><input type='text' id='user2' name="user" maxlength="200"  class="required"></td>
                </tr><tr>
	                <td>${_('password')}</td>
	                <td><input type="password" autocomplete="off" name="pass" id="pass" maxlength=200 class=required></td>
                </tr></table>
                </frameset>
                <input type="submit"  value="${_('login')}" />
              	</form>
		</td></tr>
        </table>

</div>
<div id='errorDiv'> </div>
<div id='successDiv'> </div>


</div>  <!-- end of main-->

