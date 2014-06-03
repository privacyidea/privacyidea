# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>privacyIDEA SMS Requester Form</title>

<%inherit file="auth-base.mako"/>

<div id="sidebar">
<p>
${_("Here you authenticate with your username and your OTP PIN to retrieve an SMS containing your current OTP value.")}
</p>
<p>
${_("Enter your username and the OTP PIN.")}
</p>
</div> <!-- sidebar -->


<div id="main">
<h1>${_("Login")}</h1>
<div id='register'>
    <p>${_("This form is deprecated since the same functionality was implemented in the regular /auth/index and /auth/index3 forms.")}</p>
    <a href="/auth/index">/auth/index</a>
</div>
<div id='errorDiv'></div>
<div id='successDiv'></div>


</div>  <!-- end of main-->
