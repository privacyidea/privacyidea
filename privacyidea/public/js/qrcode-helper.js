
function generate_qrcode(typenumber, text) {

	var qr = new QRCode(typenumber, QRErrorCorrectLevel.H);
	
	qr.addData(text);
	
	qr.make();
	
	var output =  "";
	output += "<table style='border-width: 0px; border-style: none; border-color: #0000ff; border-collapse: collapse;'>";
	
	for (var r = 0; r < qr.getModuleCount(); r++) {
	
	    output += "<tr>";
	
	    for (var c = 0; c < qr.getModuleCount(); c++) {
	
			output += "<td style='border-width: 0px; border-style: none; border-color: #0000ff; border-collapse: collapse; padding: 0; margin: 0;";
			output += "width: 4px; height: 4px;"
	        if (qr.isDark(r, c) ) {
	            output += "background-color: #000000;'/>";
	        } else {
	            output += "background-color: #ffffff;'/>";
	        }
	
	    }
	
	    output += "</tr>";
	
	}
	
	output += "</table>";
	
	return output;
}
