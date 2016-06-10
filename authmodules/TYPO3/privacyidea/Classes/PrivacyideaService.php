<?php
namespace NetKnightsGmbH\privacyidea;

/***************************************************************
 *
 *  Copyright notice
 *
 *  (c) 2015 Cornelius Kölbel <cornelius.koelbel@netknights.it>, NetKnights GmbH
 *
 *  All rights reserved
 *
 *  This script is part of the TYPO3 project. The TYPO3 project is
 *  free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The GNU General Public License can be found at
 *  http://www.gnu.org/copyleft/gpl.html.
 *
 *  This script is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  This copyright notice MUST APPEAR in all copies of the script!
 ***************************************************************/

/**
 * Service "privacyIDEA authentication" for the "privacyidea" extension. This
 * service will authenticate a user against your own hosted privacyIDEA
 * authentication backend. This is done by issuing a POST REST Request to
 * <service>/validate/check with the username and the password.
 * The password may consist of Password and OTP.
 * This way you can authenticate many different TYPO3 instances against one
 * privacyIDEA system.
 *
 * @author Cornelius Kölbel <cornelius.koelbel@netknights.it>
 * @package TYPO3
 * @subpackage tx_privacyidea
 */


class PrivacyideaService extends \TYPO3\CMS\Sv\AbstractAuthenticationService {

	/**
	 * Standard extension key for the service
	 * The extension key.
	 *
	 * @var string
	 */
	public $extKey = 'privacyidea';

	/**
	 * Standard prefix id for the service
	 * Same as class name
	 *
	 * @var string
	 */
	public $prefixId = 'tx_privacyidea_service';

	/**
	 * Standard relative path for the service
	 * Path to this script relative to the extension dir.
	 *
	 * @var string
	 */
	public $scriptRelPath = 'service/class.tx_privacyidea_service.php';

	/**
	 * The privacyIDEA authentication class
	 */
	protected $privacyIDEAAuth = NULL;

	/**
	 * Initializes the service.
	 *
	 * @return boolean
	 */
	public function init() {
		$this->logger = \TYPO3\CMS\Core\Utility\GeneralUtility::makeInstance('TYPO3\CMS\Core\Log\LogManager')->getLogger(__CLASS__);
		$this->logger->info("Initialize privacyIDEA");
		$available = FALSE;
		$this->extConf = unserialize ($GLOBALS['TYPO3_CONF_VARS']['EXT']['extConf']['privacyidea']);
		if (isset($this->extConf['privacyIDEABackend']) && $this->extConf['privacyIDEABackend'] == 'allUsers' && TYPO3_MODE == 'BE') {
			$this->logger->info("Authenticating with privacyIDEA at the Backend");
			$available = TRUE;
		} elseif (isset($this->extConf['privacyIDEABackend']) && $this->extConf['privacyIDEABackend'] == 'adminOnly' && TYPO3_MODE == 'BE') {
			$this->logger->info("Authenticating with privacyIDEA at the Backend (Admin Users)");
			$available = TRUE;
		} elseif (isset($this->extConf['privacyIDEAFrontend']) && (bool)$this->extConf['privacyIDEAFrontend'] && TYPO3_MODE == 'FE') {
			$this->logger->info("Authenticating with privacyIDEA at the Frontend");
			$available = TRUE;
		} else {
			$this->logger->warning("privacyIDEA Service deactivated.");
		}
		$this->privacyIDEAAuth = \TYPO3\CMS\Core\Utility\GeneralUtility::makeInstance('NetKnightsGmbH\privacyidea\PrivacyideaAuth',
			$this->extConf["privacyIDEAURL"],
			$this->extConf["privacyIDEARealm"],
			$this->extConf["privacyIDEAsslcheck"]);
		return $available;
	}

	/**
	 * Authenticates the user against privacyIDEA backend
	 *
	 * Will return one of following authentication status codes:
	 *  - 0 - authentication failure
	 *  - 100 - just go on. User is not authenticated but there is still no reason to stop
	 *  - 200 - the service was able to authenticate the user
	 *
	 * @param array $user Array containing the userdata
	 * @return int authentication statuscode, one of 0, 100 and 200
	 */
	public function authUser(array $user) {
		// 0 means authentication failure
		$ret = 0;
		if ($this->authInfo['loginType'] == 'BE' &&
			!($user['admin']) &&
			$this->extConf['privacyIDEABackend'] == 'allUsers'
		) {
			$ret = 100;
		} else {
			$username = $this->login['uname'];
			$password = $this->login['uident_text'];
			$this->logger->info("try to authenticate user [$username]");

			$authResult = $this->privacyIDEAAuth->checkOtp($username, $password);
			if ($authResult === TRUE) {
				$ret = 200;
			} else {
				if ($this->extConf['privacyIDEApassthru']) {
					$ret = 100;
					$this->logger->info("privacyIDEA authentication failed, but passing to other authentication modules.");
				} else {
					$this->logger->error("Failed to authenticate $username");
				}
			}
		}
		return $ret;
	}
}
