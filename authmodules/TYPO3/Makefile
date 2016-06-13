VERSION="0.2.0"
LINE=$(shell grep version privacyidea/ext_emconf.php) 
#| cut -d "'" -f 4)

create_extension:
	(cd privacyidea; zip -r ../privacyidea_$(VERSION).zip *)

clean:
	rm -f privacyidea_*.zip
