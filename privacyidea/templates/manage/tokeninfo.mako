# -*- coding: utf-8 -*-

<%
	ttype = c.tokeninfo.get("privacyIDEA.TokenType").lower()
%>

<div style="float:right">
<a href='${c.help_url}/tokenview/index.html#token-info' target="_blank">
	<img alt="(?)" width=24
	src="/images/help32.png"  
	title='${_("help on tokeninfo")}'>
</a>
</div>

<table class=tokeninfoOuterTable>
    % for value in c.tokeninfo:
    <tr>
    	<!-- left column -->
    <td class=tokeninfoOuterTable>${value}</td>
    	<!-- middle column -->
    <td class=tokeninfoOuterTable>
    %if "privacyIDEA.TokenInfo" == value:
    	<table class=tokeninfoInnerTable>
    	%for k in c.tokeninfo[value]:
    	<tr>  		
    	<td class=tokeninfoInnerTable>${k}</td>
    	<td class=tokeninfoInnerTable>${c.tokeninfo[value][k]}</td>
    	</tr>
    	%endfor
    	</table>
    	<div id="toolbar" class="ui-widget-header ui-corner-all">
    		<button id="ti_button_hashlib">${_("hashlib")}</button>
			<button id="ti_button_count_auth_max">${_("count auth")}</button>
			<button id="ti_button_count_auth_max_success">${_("count auth max")}</button>
			<button id="ti_button_valid_start">${_("count auth max")}</button>
			<button id="ti_button_valid_end">${_("count auth max")}</button>
			%if ttype in [ "totp", "ocra" ]:
			<button id="ti_button_time_window">${_("time window")}</button>
			<button id="ti_button_time_step">${_("time step")}</button>
			<button id="ti_button_time_shift">${_("time shift")}</button>
			%endif
			%if ttype in [ "sms" ]:
			<button id="ti_button_mobile_phone">${_("mobile phone number")}</button>
			%endif
			
			
		</div>
    %elif "privacyIDEA.RealmNames" == value:
    	<table class=tokeninfoInnerTable>
    	% for r in c.tokeninfo[value]:
    	<tr>
    		<td class=tokeninfoInnerTable>${r}</td>
    	</tr>
    	% endfor
    	</table>
    %else:
    	${c.tokeninfo[value]}
    %endif
    </td>
        	<!-- right column -->
    <td>
    	%if value == "privacyIDEA.TokenDesc":
    		<button id="ti_button_desc"></button>
    	%elif value == "privacyIDEA.OtpLen":
    		<button id="ti_button_otplen"></button>
    	%elif value == "privacyIDEA.SyncWindow":
    		<button id="ti_button_sync"></button>
    	%elif value == "privacyIDEA.CountWindow":
    		<button id="ti_button_countwindow"></button>
    	%elif value == "privacyIDEA.MaxFail":
    		<button id="ti_button_maxfail"></button>
    	%elif value == "privacyIDEA.FailCount":
    		<button id="ti_button_failcount"></button>
    	%endif
    	
    </td>
    </tr>        
    % endfor
</table>
