# -*- coding: utf-8 -*-
<table id="machine_table" class="flexme2" style="display:none"></table>
 
<script type="text/javascript"> 
	view_machine();
</script>

<div style="float:right">
<a href='${c.help_url}/machines/index.html' target="_blank">
    <img alt="(?)" width=24
    src="/images/help32.png"  
    title='${_("Open help on machines")}'>
</a>
</div>

<button onclick="machine_delete();">${_("Delete machine")}</button>
<button onclick="machine_delete_app();">${_("Delete application")}</button>

<div>
<fieldset>
<legend>${_("Client machine")}</legend>
<table>
<tr><td><label for=machine_name>${_("Machine name")}</label></td>
<td><input type="text" class="required"  id="machine_name" size="40" maxlength="80" 
          title='${_("The name of the machine")}'
</td></tr>

<tr>
<td><label for=machine_ip>${_("Machine IP")}</label></td>
<td>
<input type="text" class="required"  id="machine_ip" size="40" maxlength="80" 
          title='${_("The IP of the machine")}'
</td>
</tr>

<tr>
<td><label for=machine_desc>${_("Description")}</label></td>
<td>
<input type="text" id="machine_desc" size="40" maxlength="80" 
          title='${_("The description for the machine")}'
</td>
</tr>

<tr>
<td><label for=machine_serial>${_("Token serial number (optional)")}</label></td>
<td>
<input type="text" id="machine_serial" size="40" maxlength="80" 
          title='${_("The serial number of the token")}'
</td>
</tr>

<tr>
<td><label for=machine_application>${_("Application (optional)")}</label></td>
<td>
<input type="text" id="machine_application" size="40" maxlength="80" 
          title='${_("The application for this token on the machine")}'
</td>
</tr>

</table>
<button onclick="do_machine_create();">${_("Create machine")}</button>
</fieldset>
</div>