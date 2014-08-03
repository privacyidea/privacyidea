# -*- coding: utf-8 -*-
<table id="machine_table" class="flexme2" style="display:none"></table>
 
<script type="text/javascript"> 
	view_machine();
	$('#button_add_option').button({
        icons: {
            primary: 'ui-icon-plusthick'
        }
    });
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
<div style="float:left">
<table>
<tr><td><label for=machine_name>${_("Machine name")}</label></td>
<td><input type="text" class="required"  id="machine_name" size="40" maxlength="80" 
          title='${_("The name of the machine")}'>
</td></tr>

<tr>
<td><label for=machine_ip>${_("Machine IP")}</label></td>
<td>
<input type="text" class="required"  id="machine_ip" size="40" maxlength="80" 
          title='${_("The IP of the machine")}'>
</td>
</tr>

<tr>
<td><label for=machine_desc>${_("Description")}</label></td>
<td>
<input type="text" id="machine_desc" size="40" maxlength="80" 
          title='${_("The description for the machine")}'>
</td>
</tr>

<tr>
<td><label for=machine_serial>${_("Token serial number (optional)")}</label></td>
<td>
<input type="text" id="machine_serial" size="40" maxlength="80" 
          title='${_("The serial number of the token")}'>
</td>
</tr>

<tr>
<td><label for=machine_application>${_("Application (optional)")}</label></td>
<td>
<select id="machine_application" 
          title='${_("The application for this token on the machine")}'>
<span id="machine_mtid"
	title='$_{"This is the identifier in the machine-application-token mapping"}'> 
</span>
</td>
</tr>

</table>
<button onclick="do_machine_create();">${_("Create machine")}</button>

<button id="button_client_token" 
	  	title='${_("Create applications with selected tokens.")}'>
  ${_("create with all selected tokens")}
</button>

</div>

<!--=========== Options ================-->
<div style="float:right">
<fieldset>
<legend>${_("Application options")}</legend>
<table id="options_table">
<tr><th>
${_("Option keys")}
</th><th>
${_("Option values")}
</th><th>
</th></tr>
<tr><td>
<input type="text" id="new_option_key" size="10" maxlenght=40 
	title='${_("A option key starting with option_")}'>
</td><td>
<input type="text" id="new_option_value" size="10" maxlenght=40 
	title='${_("The option value")}'>
</td><td>
<button id="button_add_option" onclick="machine_add_option();"
   title='${_("Add application option")}'>
</button>
</td></tr>
</table>
</fieldset>
</div>
</fieldset>
</div>