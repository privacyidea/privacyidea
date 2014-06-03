
function checkpins(otp_pin1,otp_pin2){
/*
 *  check pins: verifies, that the pins in both
 *  referenced entries are equal
 */
    var pin1 = $('#'+otp_pin1).val();
    var pin2 = $('#'+otp_pin2).val();
    if (pin1 == pin2) {
        $('#'+otp_pin1).removeClass('ui-state-error');
        $('#'+otp_pin2).removeClass('ui-state-error');
    }
    else {
        $('#'+otp_pin1).addClass('ui-state-error');
        $('#'+otp_pin2).addClass('ui-state-error');
    }
    return false;
}

function cb_changed(checkbox_id,arry){
/*
 * cb_changed - dependent on the checkbox state,
 * show all entries (identified by their id), which are listed in the array
 */
 	var checked = $('#'+checkbox_id).attr('checked');

	for (i=0; i<arry.length; i++) {
		var sid = arry[i];
		if  ( checked )
			$('#'+sid).hide();
		else
			$('#'+sid).show();
	}
}

function show_waiting() {
	$('#do_waiting').show();
	//$('#statusline').show();
	//var milliseconds = (new Date()).getTime();
	//console.log("show: " +milliseconds);
}

function hide_waiting() {
	$("#do_waiting").hide();
	//$('#statusline').hide();
	//var milliseconds = (new Date()).getTime();
	//console.log("hide: " +milliseconds);
}

function getcookie(search_key) {
	var searched_cookie="";
	if (document.cookie) {
		cookieArray = document.cookie.split(';');
		//alert(document.cookie);
		var arLen=cookieArray.length;
		for ( var i=0; i<arLen; ++i ) {
			var cookie = cookieArray[i];
			var key_1 = 0;
			var key_2 = cookie.indexOf("=");
      		var val_1 = cookie.indexOf("=") + 1;
      		var val_2 = cookie.indexOf(";");
      		if(val_2 == -1) val_2 = document.cookie.length;

      		var key = cookie.substring(key_1,key_2);
			key=key.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
			key=key.replace(/^\""*/, '').replace(/\""*$/, '');

  			if (search_key == key) {
  				searched_cookie = cookie.substring(val_1,val_2);
  				searched_cookie = searched_cookie.replace(/^\""*/, '').replace(/\""*$/, '');
  			}
		}
	}
	return searched_cookie;
}

function console_log(msg) {
    if (window.console && window.console.log) {
        window.console.log(msg);
    }
    else if (window.opera && window.opera.postError) {
        window.opera.postError(msg);
    }
}
