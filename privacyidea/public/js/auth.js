/**
 * @author koelbel
 */

function clientUrlFetchSync(myUrl, params) {
	/*
	 * clientUrlFetchSync - to submit a syncronous  http request
	 *
	 * @remark: introduced the params (:dict:) so we could switch to
	 * 			a POST request, which will allow more and secure data
	 */

	var resp = $.ajax({
		url : myUrl,
		data : params,
		async : false,
		type : 'POST',
	}).responseText;

	return resp;
}

function getOcraChallenge() {
	var user = $('#user').val();
	var targetId = 'display';
	var userId = 'user2';

	var params = {};
	params['user'] = $('#user').val();
	params['data'] = $('#challenge').val();
	params['qr'] = 'img';

	var url = '/ocra/request';

	try {
		var data = clientUrlFetchSync(url, params);
		if ( typeof (data) == "object") {
			var err = data.result.error.message;
			alert(err);
		} else {
			var img = data;
			$('#' + targetId).html(img);
			$('#' + userId).val(user);
		}
	} catch (e) {
		alert(e);
	}
}

function getOcra2Challenge() {
	var user = $('#user').val();
	var targetId = 'display';
	var userId = 'user2';

	var params = {};
	params['user'] = $('#user').val();
	params['pass'] = $('#pin').val();
	params['data'] = $('#challenge').val();
	params['qr'] = 'img';

	var url = '/validate/check';

	try {
		var data = clientUrlFetchSync(url, params);
		if ( typeof (data) == "object") {
			var err = data.result.error.message;
			alert(err);
		} else {
			var img = data;
			$('#' + targetId).html(img);
			$('#' + userId).val(user);
		}
	} catch (e) {
		alert(e);
	}
}


function login_user(column) {
	var user = "";
	var pass = "";
	if (column == 3) {
		user = $('#user3').val();
		pass = encodeURIComponent($('#pass3').val() + $('#otp3').val());
	} else {
		user = $('#user').val();
		pass = $('#pass').val();
	}

	var params = {};
	params['user'] = user;
	params['pass'] = pass;

	var resp = clientUrlFetchSync('/validate/check', params);
	var data = jQuery.parseJSON(resp);

	if (false == data.result.status) {
		alert(data.result.error.message);
	} else {
		if (true == data.result.value) {
			alert("User successfully authenticated!");
		} else if ("detail" in data && "message" in data.detail) {
			alert(data.detail.message)
		} else {
			alert("User failed to authenticate!");
		}
		//$('#user').val('');
		$('#pass').val('');
		$('#otp3').val('');
	}

}

$(document).ready(function() {

	$("button").button();

	/*
	* Auth login callbacks
	*/

	// auth/index
	$("#form_login").submit(function() {
		login_user( column = 2);
		return false;
	});

	// auth/index3
	$("#form_login3").submit(function() {
		login_user( column = 3);
		return false;
	});

	// auth/ocra
	$("#form_challenge_ocra").submit(function() {
		getOcraChallenge();
		return false;
	});

	$("#form_login_ocra").submit(function() {
		login_user( column = 2);
		return false;
	});

	// auth/ocra2
	$("#form_challenge_ocra2").submit(function() {
		getOcra2Challenge();
		return false;
	});

	$("#form_login_ocra2").submit(function() {
		login_user( column = 2);
		return false;
	});

});

