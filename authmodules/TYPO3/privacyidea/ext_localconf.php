<?php
defined('TYPO3_MODE') or die();

\TYPO3\CMS\Core\Utility\ExtensionManagementUtility::addService($_EXTKEY,
		  'auth',
		  'tx_privacyidea_service',
        array(
                'title' => 'Authentication against privacyIDEA for FE/BE',
                'description' => 'authenticate user by using OTP with privacyIDEA',
                'subtype' => 'authUserFE,authUserBE',
                'available' => TRUE,
                'priority' => 80,
                'quality' => 80,
                'os' => '',
                'exec' => '',
                'className' => 'NetKnightsGmbH\\privacyidea\\PrivacyideaService'
        )
);
