# -*- coding: utf-8 -*-
<%inherit file="base.mako"/>


<h1>Login to privacyIDEA OpenID</h1>

  <p>
    <form action="/openid/check" method="GET">
      <table>
        <tr><td>Username:</td>
        %if "" != c.user:
        	<td><input type="hidden" name="user" value="${c.user}" />
        	${c.p["openid.claimed_id"]}
        	</td></tr>
        %else:
        	<td><input type="text" name="user" value="" /></td></tr>
        %endif
        <tr><td>One Time Password:</td>
        <td><input autocomplete="off" type="password" name="pass" value ="" /></td></tr>
        <tr><td></td>
        <td>   <input type="submit" value="Login" /></td></tr>

      %for k in c.p:
      <input type="hidden" name="${k}" value="${c.p[k]}" />
      %endfor
      </table>
    </form>
  </p>

<div id='errorDiv'></div>
<div id='successDiv'></div>

