# -*- coding: utf-8 -*-
<%inherit file="base.mako"/>


<p>The site <tt>${c.rely_party}</tt> has requested verification of your OpenID as <tt> ${c.identity}</tt>.
</p>
<p>
Verify your identity to the relying party?
</p>

<form action="checkid_submit" method="GET">
     <input type="hidden" name="redirect_token" value="${c.redirect_token}"></input>
     <p> <input type="checkbox" name="verify_always" value="always"> 
     Verify to this relying party always automatically. So, do not ask me again.</p>
     <button type="submit">Verify</button>
</form>
