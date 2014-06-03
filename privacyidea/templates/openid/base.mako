# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>privacyIDEA OpenID Service</title>
<meta name="author" content="Cornelius Kölbel">
<meta name="date" content="2011-06-09T23:23:25+0200">
<meta name="copyright" content="LSE Leading Security Experts GmbH">
<meta name="keywords" content="privacyIDEA, openid service">
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta http-equiv="content-type" content="application/xhtml+xml; charset=UTF-8">
<meta http-equiv="content-style-type" content="text/css">

<link type="text/css" rel="stylesheet" href="/openid/style.css" />
<link type="text/css" rel="stylesheet" href="/openid/custom-style.css" />

</head>

<body>

<div id="wrap">

<div id="header">

	<img src="/images/privacyIDEA-logo-klein.png" border="0" alt="privacyIDEA "/>

	<div class="float_right">
	<span class=portalname>OpenID Service</span>
	</div>
</div>


<div id="sidebar">


%if hasattr(c,"message"):
	<p>${c.message}</p>
%endif
<P>
%if c.logged_in:
	You are logged in as: <tt>${c.login}</tt><br>
	<form action="/openid/logout" method="GET">
	% if hasattr(c,'p'):
	%for k in c.p:
      <input type="hidden" name="${k}" value="${c.p[k]}" />
    %endfor
    <p>If you log out, you have to restart your openid access request!</p>
    %endif
	<input type="submit" value="Logout" />
	</form>
%else:
	You are not logged in. You may <a href=/openid/login>login</a>
%endif
</P>


</div> <!-- sidebar -->

<div id="main">

${self.body()}


</div>  <!-- end of main-->

<div id="footer">
${c.version} | ${c.licenseinfo}
</div>
</div>  <!-- end of wrap -->
</body>
</html>





