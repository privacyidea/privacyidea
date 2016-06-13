<?php

$EM_CONF[$_EXTKEY] = array(
	'title' => 'privacyidea',
	'description' => 'Two factor authentication for TYPO3 frontend and backend authenticating against your own privacyIDEA server.
privacyIDEA supports many different type of authentication devices like OTP token, display cards, Yubikey, SMS, Email...',
	'category' => 'services',
	'author' => 'Cornelius Kölbel',
	'author_email' => 'cornelius.koelbel@netknights.it',
	'author_company' => 'NetKnights GmbH',
	'state' => 'beta',
	'internal' => '',
	'uploadfolder' => '0',
	'createDirs' => '',
	'clearCacheOnLoad' => 0,
	'version' => '0.2.0',
	'constraints' => array(
		'depends' => array(
			'typo3' => '6.2.0-7.6.99',
		),
		'conflicts' => array(
		),
		'suggests' => array(
		),
	),
);
