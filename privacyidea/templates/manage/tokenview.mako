# -*- coding: utf-8 -*-    

 <button class='ui-button' id='button_losttoken'>${_("Lost token")}</button>
 <button class='ui-button' id='button_tokeninfo'>${_("Token info")}</button>
 <button class='ui-button' id='button_resync'>${_("Resync Token")}</button>
 <button class='ui-button' id='button_tokenrealm'>${_("set token realm")}</button>
 <button class='ui-button' id='button_getmulti'>${_("get OTP")}</button>
 
 <a href='${c.help_url}/tokenview/index.html' target="_blank">
	<img alt="(?)" width=24
	src="/images/help32.png"  
	title='${_("help on tokenview")}'>
</a>
 
<table id="token_table" class="flexme2" style="display:none"></table>
   
<script type="text/javascript"> 
view_token();
tokenbuttons();
</script>


