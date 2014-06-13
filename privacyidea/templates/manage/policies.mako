# -*- coding: utf-8 -*-
    

<a id=policy_export>${_("Export policies")}</a>

<button id=policy_import>${_("Import policies")}</button>

<a href='${c.help_url}/policies/index.html' target="_blank">
	<img alt="(?)" width=24
	src="/images/help32.png"  
	title='${_("Open help on policies")}'>
</a>

<table id="policy_table" class="flexme2" style="display:none"></table>
   
   
<table>
  <tr>
  	<td><label for=policy_active>${_("Active")}</label></td>
  	<td><input type="checkbox" name="policy_active" id="policy_active" value="True"></td>
  </tr>	
  <tr>
  	<td><label for=policy_name>${_("Policy name")}</label></td>
  	<td><input type="text" class="required"  id="policy_name" size="40" maxlength="80" 
  		title='${_("The name of the policy")}'></td>
  </tr>
  <tr>
	<td><label for=policy_scope_combo>${_("Scope")}</label></td>
	<td>
	<select id='policy_scope_combo'>
	<option value="_">${_("__undefined__")}</option>
	%for scope in c.polDefs.keys():
	<option value="${scope}">${scope}</option>
	%endfor
	</select>
	</td>
  </tr>
    <tr>
  	<td><label for="policy_action">${_("Action")}</label></td>
  	<td><input type="text" class="required"  id="policy_action" size="40" maxlength="200" 
  		title='${_("The action that should be allowed. These are actions like: enrollSMS, enrollMOTP...The actions may be comma separated.")}'>
  	</td><td>
  		<span id="action_info" class="help_text"> </span>
  		</td>
  </tr>
  <tr>
  	<td><label for="policy_user">${_("User")}</label></td>
  	<td><input type="text"  id="policy_user" size="40" maxlength="80" 
  		title='${_("The user or usergroup the policy should apply to")}'></td>
  </tr>
    <tr>
  	<td><label for="policy_realm">${_("Realm")}</label></td>
  	<td><input type="text" class="required"  id="policy_realm" size="40" maxlength="80" 
  		title='${_("The realm the policy applies to")}'></td>
  </tr>
   <tr>
  	<td><label for="policy_client">${_("Client")}</label></td>
  	<td><input type="text"  id="policy_client" size="40" maxlength="120" 
  		title='${_("Comma separated list of client IPs and Subnets.")}'></td>
  </tr>
  <tr>
  	<td><label for=policy_time>${_("Time")}</label></td>
  	<td><input type="text"  id="policy_time" size="40" maxlength="80" 
  		title='${_("The time on which the policy should be applied")}'></td>
  </tr>
  <tr>
  	<td></td><td>
  	<button  id=button_policy_add>${_("set policy")}</button>
  	<button  id=button_policy_delete>${_("delete policy")}</button>
  	</td>
  </tr>
</table> 
<script type="text/javascript"> 
	view_policy();
</script>


