# -*- coding: utf-8 -*-


%if c.scope == 'config.title' :
 ${_("Remote Token")}
%endif


%if c.scope == 'config' :
<script>

/*
 * 'typ'_get_config_val()
 *
 * this method is called, when the token config dialog is opened
 * - it contains the mapping of config entries to the form id
 * - according to the Config entries, the form entries will be filled
 *
 */


function remote_get_config_val(){
	var id_map = {};

    id_map['remote.server'] 		= 'sys_remote_server';
    id_map['remote.local_checkpin'] = 'sys_remote_local_checkpin';
    id_map['remote.realm'] 			= 'sys_remote_realm';
    id_map['remote.resConf'] 		= 'sys_remote_resConf';

    // FIXME: We need to set the checkpin select box. Do not know how!

	return id_map;

}

/*
 * 'typ'_get_config_params()
 *
 * this method is called, when the token config is submitted
 * - it will return a hash of parameters for system/setConfig call
 *
 */
function remote_get_config_params(){
	var url_params ={};

    url_params['remote.server'] 	= $('#sys_remote_server').val();
    url_params['remote.realm'] 	= $('#sys_remote_realm').val();
    url_params['remote.resConf'] 	= $('#sys_remote_resConf').val();
    url_params['remote.remote_checkpin'] 	= $('#sys_remote_local_checkpin').val();

	return url_params;
}


jQuery.validator.addMethod("sys_remote_server", function(value, element, param){
      return value.match(param);
}, "${_('Please enter a valid remote server specification. It needs to be of the form http://server or https://server')}");


$("#form_config_remote").validate({
         rules: {
            sys_remote_server: {
                required: true,
                number: false,
                	sys_remote_server: /^(http:\/\/|https:\/\/)/i
             }
         }
     });

</script>

<form class="cmxform" id='form_config_remote'>
	<table>
	<tr>
	<td><label for="sys_remote_server" title='${_("You need to enter the remote privacyIDEA server like https://remoteprivacyidea")}'>
		${_("REMOTE server")}</label></td>
	<td><input class="required" type="text" name="sys_remote_server" id="sys_remote_server"
		class="text ui-widget-content ui-corner-all" value="https://localhost"/></td>
	</tr>

	<tr><td><label for="sys_remote_local_checkpin" title='${_("The PIN can either be verified on this local privacyIDEA server or forwarded to the remote server")}'>
		${_("check PIN")}</label></td>
	<td><select name="sys_remote_local_checkpin" id="sys_remote_local_checkpin"
		title='${_("The PIN can either be verified on this local privacyIDEA server or on the remote server")}'>
			<option value=0>${_("on REMOTE server")}</option>
			<option value=1>${_("locally")}</option>
		</select></td>
	</tr>

	<tr>
	<td><label for="sys_remote_realm">${_("Remote Realm")}</label></td>
	<td><input type="text" name="sys_remote_realm" id="sys_remote_realm"
		class="text ui-widget-content ui-corner-all" /></td>
	</tr>

	<tr>
	<td><label for="sys_remote_resConf">${_("Remote Resolver")}</label></td>
	<td><input type="text" name="sys_remote_resConf" id="sys_remote_resConf"
		class="text ui-widget-content ui-corner-all" /></td>
	</tr>
	</table>

</form>
%endif


%if c.scope == 'enroll.title' :
${_("REMOTE token")}
%endif

%if c.scope == 'enroll' :
<script>

/*
 * 'typ'_get_enroll_params()
 *
 * this method is called, when the token  is submitted
 * - it will return a hash of parameters for admin/init call
 *
 */

function remote_get_enroll_params(){
	var params ={};

    //params['serial'] =  create_serial('LSRE');
    params['remote.server'] 		= $('#remote_server').val();
    params['remote.local_checkpin'] = $('#remote_local_checkpin').val();
    params['remote.serial'] 		= $('#remote_serial').val();
    params['remote.user'] 			= $('#remote_user').val();
    params['remote.realm'] 			= $('#remote_realm').val();
    params['remote.resConf'] 		= $('#remote_resconf').val();
    params['description'] 			= "remote:" + $('#remote_server').val();

    jQuery.extend(params, add_user_data());

	return params;
}


jQuery.validator.addMethod("remote_server", function(value, element, param){
    return value.match(param);
}, "${_('Please enter a valid URL for the privacyIDEA server. It needs to start with http:// or https://')}");



$("#form_enroll_token").validate({
         rules: {
            remote_server: {
                required: true,
                number: false,
                remote_server: /^(http:\/\/|https:\/\/)/i
             }
         }
     });

<%
	from privacyidea.lib.config import getFromConfig
	sys_remote_server = ""
	sys_remote_realm = ""
	sys_remote_resConf = ""
	sys_checkpin_local = "selected"
	sys_checkpin_remote = ""

	try:
		sys_remote_server = getFromConfig("remote.server")
		sys_remote_realm = getFromConfig("remote.realm")
		sys_remote_resConf = getFromConfig("remote.resConf")
		sys_remote_local_checkpin = getFromConfig("remote.local_checkpin")

		if sys_remote_local_checkpin == 0:
			sys_checkpin_local = ""
			sys_checkpin_remote = "selected"
	except Exception:
		pass

%>
</script>

<p>${_("Here you can define to which privacyIDEA Server the authentication request should be forwarded.")}</p>
<p>${_("You can either forward the OTP to a remote serial number or to a remote user.")}</p>
<p>${_("If you do not enter a remote serial or a remote user, the request will be forwarded to the remote user with the same username")}</p>
<table><tr>
	<td><label for="remote_server" title='${_("You need to enter the server like \'https://privacyidea.my.domain\'")}'>
		${_("remote server")}</label></td>
	<td><input class="required" type="text" name="remote_server" id="remote_server"
		value="${sys_remote_server}" class="text ui-widget-content ui-corner-all"/></td>
	</tr><tr>
	<td><label for="remote_local_checkpin" title='{_("The PIN can either be verified on this local privacyIDEA server or on the remote privacyIDEA server")}'>
		${_("check PIN")}</label></td>
	<td><select name="remote_local_checkpin" id="remote_local_checkpin"
		title='${_("The PIN can either be verified on this local privacyIDEA server or on the remote privacyIDEA server")}'>
		<option ${sys_checkpin_remote} value=0>${_("remotely")}</option>
		<option ${sys_checkpin_local} value=1>${_("locally")}</option>
	</select></td>
	</tr><tr>
	<td><label for="remote_serial">${_("remote serial")}</label></td>
	<td><input type="text" name="remote_serial" id="remote_serial" value="" class="text ui-widget-content ui-corner-all" /></td>
	</tr><tr>
	<td><label for="remote_user">${_("remote user")}</label></td>
	<td><input type="text" name="remote_user" id="remote_user" value="" class="text ui-widget-content ui-corner-all" /></td>
	</tr><tr>
	<td><label for="remote_realm">${_("remote user realm")}</label></td>
	<td><input type="text" name="remote_realm" id="remote_realm"
		value="${sys_remote_realm}" class="text ui-widget-content ui-corner-all" /></td>
	</tr><tr>
	<td><label for="remote_resconf">${_("remote user useridresolver")}</label></td>
	<td><input type="text" name="remote_resconf" id="remote_resconf"
		value="${sys_remote_resConf}" class="text ui-widget-content ui-corner-all" /></td>
	</tr></table>


%endif