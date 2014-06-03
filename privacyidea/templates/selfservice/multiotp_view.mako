# -*- coding: utf-8 -*-
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<title>${_("OTP values")}</title>

<link type="text/css" rel="stylesheet" href="/selfservice/style.css" />
<link type="text/css" rel="stylesheet" href="/selfservice/custom-style.css" />

<%
type=c.ret.get('type',"")
otps=c.ret.get('otp',{})
serial=c.ret.get('serial',"")
%>

</head>

<body>
<p>
${_("Your token")} ${serial} ${_("is of type")} ${type}.
</p> 
<p>
%if c.ret.get("result") == False:
${_("Failed to retrieve the OTP values of your token:")}
${c.ret.get("error")}
%endif
</p>
<table class=getotp>
%for k in sorted(otps.iterkeys()):
<tr class=getotp>
%if type.lower()=="totp":
<td class="getotp key">${otps[k]["time"]}</td>
<td class="getotp key">${otps[k]["otpval"]}</td>
%else:
<td class="getotp key">${k}</td>
<td class="getotp value">${otps[k]}</td>
%endif
</tr>
%endfor
</table>

<button onclick="window.print();">Print Page</button>
</body>
</html>
