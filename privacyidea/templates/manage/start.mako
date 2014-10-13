# -*- coding: utf-8 -*-
<%inherit file="manage-base.mako"/>



<%def name="sidebar()">
    <div id="realms">
    ${_("Realms")}: <select id=realm></select>
    </div>
    
    <fieldset>
    <legend id="selected_tokens_header">${_("selected tokens")}</legend>
    <div id="selected_tokens"></div>
    <button class='action-button' id='button_unselect'>
    ${_("clear token selection")}
    </button>
    </fieldset>
    
    <span id="selected_users_header">${_("selected users")}</span>
    <div id="selected_users"></div>
    
    <span id="selected_machine_header">${_("selected machine")}</span>
    <div id="selected_machine"></div>
    
	<div class=button_bar_token id=button_bar_token>
    <button class='action-button' id='button_enroll'>${_("enroll")}</button>
   
    <button class='action-button' id='button_assign'>${_("assign")}</button>

    <button class='action-button' id='button_unassign'>${_("unassign")}</button>

    <button class='action-button' id='button_enable'>${_("enable")}</button>

    <button class='action-button' id='button_disable'>${_("disable")}</button>

    <button class='action-button' id='button_setpin'>${_("set PIN")}</button>

    <button class='action-button' id='button_resetcounter'>${_("Reset failcounter")}</button>

    <button class='action-button' id='button_delete'>${_("delete")}</button>
	</div>
	
</%def>


<div id="main">

<div class=info_box id=info_box>
<span id=info_text>
</span>
<button id=button_info_text>OK</button>
</div>
<script>
	$('#info_box').hide();
	$("#button_info_text").button("enable");
	$('#button_info_text').click(function(){
		$('#info_box').hide('blind',{},500);
	});
</script>

<div id="tabs">
	<ul>
		<li><a href="/manage/tokenview" onclick="view_clicked('tokenview');"><span>${_("Token View")}</span></a></li>
		<li><a href="/manage/userview" onclick="view_clicked('userview');"><span>${_("User View")}</span></a></li>
		<li><a href="/manage/policies" onclick="view_clicked('policies');"><span>${_("Policies")}</span></a></li>
		<li><a href="/manage/machines" onclick="view_clicked('machines');"><span>${_("Machines")}</span></a></li>
		<li><a href="/manage/audittrail" onclick="view_clicked('audit');"><span>${_("Audit Trail")}</span></a></li>
	</ul>
</div>

<!--

<div id="logAccordionResizer" style="padding:10px; width:97%; height:120px;" class="ui-widget-content">
<div id="logAccordion" class="ui-accordion">
<h3 class=""ui-accordion-header"><a href="#">Log</a></h3>
	<div id="logText">
	</div>
</div>
<span class="ui-icon ui-icon-grip-dotted-horizontal" style="margin:2px auto;"></span>
</div>
-->

<div id='errorDiv'></div>
<div id='successDiv'></div>

</div>  <!-- end of main-->
