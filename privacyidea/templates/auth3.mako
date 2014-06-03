# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>privacyIDEA Auth testing</title>

<%inherit file="auth-base.mako"/>

<div id="sidebar">
<p>
${_("Here you may try to authenticate using your OTP token.")}
</p>
<p>
${_("Enter your username, the OTP PIN (Password) and the OTP value.")}
</p>
</div> <!-- sidebar -->


<div id="main">
<h1>${_("Login")}</h1>
<div id='register'>
        <form class="cmxform"  id="form_login3">
        	<frameset name=login>
                <table>
                <tr>
                <td>${_("username")}</td>
                <td><input type='text' id='user3' name="user" maxlength="200"  class="required"></td>
                </tr>
                <tr>
                <td>${_("password/PIN")}</td>
                <td><input type="password" autocomplete="off" name="pass" id="pass3" maxlength=200></td>
                </tr>
                <tr>
                <td>${_("OTP value")}</td>
                <td><input type="text" autocomplete="off" name="otp" id="otp3" maxlength=200></td>
                </tr>
                </table>
                </frameset>
                <input type="submit" value="${_('login')}" />
              	</form>

</div>
<div id='errorDiv'></div>
<div id='successDiv'></div>


</div>  <!-- end of main-->

