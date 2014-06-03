# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>privacyIDEA</title>
<meta name="author" content="Cornelius Kölbel">
<meta name="date" content="2010-07-05T23:23:25+0200">
<meta name="keywords" content="privacyIDEA login">
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta http-equiv="content-type" content="application/xhtml+xml; charset=UTF-8">
<meta http-equiv="content-style-type" content="text/css">

<link type="text/css" rel="stylesheet" href="/selfservice/style.css" />
<link type="text/css" rel="stylesheet" href="/selfservice/custom-style.css" />
<script type="text/javascript" src="/js/jquery-1.7.2.min.js"></script>

</head>

<body>

<script>
$(document).ready(function() {
    $('form:first *:input[type!=hidden]:first').focus();
});
</script>

<div id="wrap">

<div id="header-login">
	<div id="logo">
	</div>
	
	<div class="float_right">
	<span class=portalname>${_("privacyIDEA")}</span>
	</div>
</div>



<div id="main-login">
<h1>${_("Login to privacyIDEA")}</h1>

  <p>
    <form action="/account/dologin" method="POST">
      <table>
        <tr><td><label for=login>${_("Username")}:</label></td>
        <td><input type="text" id="login" name="login" value="" /></td></tr>
		%if c.realmbox:
        	<tr>
        %else:
			<tr style="display:none;">
		%endif
		<td>${_("Realm")}:</td>
        <td>
	    <select name="realm">
	        % for realm in c.realmArray:
	        %if c.defaultRealm == realm:
	        <option value="${realm}" selected>${realm}</option>
	        %else:
	        <option value="${realm}">${realm}</option>
	        %endif
	        %endfor
        </select>
        </td></tr>
        <tr><td><label for=password>${_("Password")}:</label></td>
        <td><input autocomplete="off" type="password" id="password" name="password" value ="" /></td></tr>
        <tr><td></td>
        <td>   <input type="submit" value="Login" /></td></tr>
      </table>
    </form>
  </p>

<div id='errorDiv'></div>
<div id='successDiv'></div>


</div>  <!-- end of main-->

<!--
<div id="footer">
	${c.version} | ${c.licenseinfo}
</div>
-->
</div>  <!-- end of wrap -->
</body>
</html>





