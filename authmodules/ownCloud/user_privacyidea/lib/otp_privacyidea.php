<?php

/**
 * privacyidea authentication module for ownCloud
 * See https://www.privacyidea.org
 *
 * 2015-10-26 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            use \OCP\Util::writeLog
 *            Add privacyIDEA realm
 * 2015-06-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            initial writeup
 *            inspired by user_ldap and user_otp
 *
 *    This program is free software: you can redistribute it and/or
 *    modify it under the terms of the GNU Affero General Public
 *    License, version 3, as published by the Free Software Foundation.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the
 *               GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *
 */

/**
 * User authentication against privacyIDEA
 *
 * @category Apps
 * @package  UserPrivacyIDEA
 * @author   Cornelius Kölbel <cornelius.koelbel@netknights.it>
 * @license  http://www.gnu.org/licenses/agpl AGPL
 * @link     http://github.com/privacyidea/privacyidea
 */
class OC_User_PRIVACYIDEA extends OC_User_Backend
{

    private static $_backends = null;
    private $_userBackend = null;

    protected $possibleActions = array(
        self::CREATE_USER => 'createUser',
        self::SET_PASSWORD => 'setPassword',
        self::CHECK_PASSWORD => 'checkPassword',
        //self::GET_HOME => 'getHome',
        self::GET_DISPLAYNAME => 'getDisplayName',
        //self::SET_DISPLAYNAME => 'setDisplayName',
        //self::PROVIDE_AVATAR => 'canChangeAvatar',
        self::COUNT_USERS => 'countUsers',
    );

    /**
     * Create a new privacyIDEA authentication provider
     */
    public function __contrust()
    {
        parent::__contruct();
    }

    public function userExists($uid)
    {
        $found_anywhere = false;
        foreach (self::$_backends as $backendObj) {
            if ($backendObj->userExists($uid)) {
                $found_anywhere = true;
            }
        }
        return $found_anywhere;
    }

    /**
     * Collect all the users from all user backends
     */
    public function getUsers($search = '', $limit = null, $offset = null)
    {
        $all_users = array();
        foreach (self::$_backends as $backendObj) {
            $all_users = array_merge($all_users, $backendObj->getUsers($search, $limit, $offset));
        }
        return $all_users;
    }

    /**
     * Delete a user in an underlying user backend
     */
    public function deleteUser($uid)
    {
        $user_deleted = false;
        foreach (self::$_backends as $backendObj) {
            if ($backendObj->deleteUser($uid)) {
                $user_deleted = true;
            }
        }
        return $user_deleted;
    }

    public function createUser($uid, $password)
    {
        $user_created = false;
        foreach (self::$_backends as $backendObj) {
            if ($backendObj->createUser($uid, $password)) {
                $user_created = true;
                # If there are more than one user backend, we stop as soon as we were
                # able to create the user successfully in one backend.
                break;
            }
        }
        return $user_created;
    }

    public function getDisplayName($uid) {
        $displayname = "";
        foreach (self::$_backends as $backendObj) {
            $r = $backendObj->getDisplayName($uid);
            if ($r) {
                $displayname = $r;
            }
        }
        return $displayname;
    }


    /*
     * Set the password in the underlying user backend
     */
    public function setPassword($uid, $password) {
        $result = false;
        foreach (self::$_backends as $backendObj) {
            $result = $backendObj->setPassword($uid, $password);
        }
        return $result;
    }

    /*
     * Check if any of the old user backends supports userlisting
     */
    public function hasUserListings()
    {
        $any_listing = false;
        foreach (self::$_backends as $backendObj) {
            if ($backendObj->hasUserListings()) {
                $any_listing = true;
            }
        }
        return $any_listing;
    }

    /**
     * Here we register the previously used backends, so that we can pass the
     * calls for userList and userExist to those backends
     */
    public function registerBackends($usedBackends)
    {
        if (self::$_backends === null) {
            foreach ($usedBackends as $backend) {
                \OCP\Util::writeLog('user_privacyidea', 'registering backend  '
                    . $backend, \OCP\Util::DEBUG);
                self::$_backends[$backend] = new $backend();
            }
        }
    }

    /**
     * Check the password against privacyIDEA
     */
    public function checkPassword($uid, $password)
    {
        $authenticated_user = "";
        // check if we are called by a desktop client
        $allow_api = (\OCP\Config::getAppValue('privacyIDEA', 'allow_api') === "yes");
        $client_call = (basename($_SERVER['SCRIPT_NAME']) === 'remote.php');

        \OCP\Util::writeLog('user_privacyidea', 'API: '. $allow_api, \OCP\Util::DEBUG);
        \OCP\Util::writeLog('user_privacyidea', 'Client Call: '. $client_call, \OCP\Util::DEBUG);

        if (($client_call === true) && ($allow_api === true)) {
            \OCP\Util::writeLog('user_privacyidea', 'Authenticating with normal password', \OCP\Util::DEBUG);
            foreach (self::$_backends as $backendObj) {
                $r = $backendObj->checkPassword($uid, $password);
                if ($r) {
                    $authenticated_user = $r;
                }
            }
        } else {
            // We are called from within a browser.
            OCP\Util::writeLog('user_privacyidea', 'privacyIDEA checkPassword',
                OCP\Util::DEBUG);

            $sslcheck = \OCP\Config::getAppValue('privacyIDEA',
                'verify_ssl');
            $allow_normal_login = \OCP\Config::getAppValue('privacyIDEA', 'allow_normal_login');
            $url = \OCP\Config::getAppValue('privacyIDEA', 'privacyidea_url');
            OCP\Util::writeLog('user_privacyidea', "calling " . $url . " for user " .
                $uid . " (" . $sslcheck . ")",
                OCP\Util::DEBUG);
            $realm = \OCP\Config::getAppValue('privacyIDEA', 'realm');
            $proxy = \OCP\Config::getAppValue('privacyIDEA', 'privacyidea_proxy');
            $result = $this->checkOtp($url, $uid, $password, $sslcheck, $realm, $proxy);
            OCP\Util::writeLog('user_privacyidea', 'privacyidea returned ' . $result,
                OCP\Util::INFO);
            if ($result) {
                $authenticated_user = $uid;
            } else {
                if ($allow_normal_login === "yes") {
                    foreach (self::$_backends as $backendObj) {
                        $r = $backendObj->checkPassword($uid, $password);
                        if ($r) {
                            $authenticated_user = $r;
                        }
                    }
                }
            }
        }
        return $authenticated_user;
    }

    /**
     * Do the ajax call.
     */
    public function checkOtp($url, $username, $password, $sslcheck, $realm, $proxy)
    {
        $curl_instance = curl_init();
        $escPassword = urlencode($password);
        $escUsername = urlencode($username);
        $url = $url . '/validate/check';
        curl_setopt($curl_instance, CURLOPT_URL, $url);
        curl_setopt($curl_instance, CURLOPT_POST, 3);
        if ($proxy) {
            curl_setopt($curl_instance, CURLOPT_PROXY, $proxy);
        }
        curl_setopt($curl_instance, CURLOPT_USERAGENT,'OwnCloud-PrivacyIDEA');

        $poststring = "user=$username&pass=$password";
        if ($realm) {
            $poststring = "$poststring&realm=$realm";
        }
        curl_setopt($curl_instance, CURLOPT_POSTFIELDS, $poststring);
        curl_setopt($curl_instance, CURLOPT_HEADER, TRUE);
        curl_setopt($curl_instance, CURLOPT_RETURNTRANSFER, TRUE);
        if ($sslcheck === "Yes") {
            curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 1);
            curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 1);
        } else {
            curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 0);
            curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 0);
        }
        $response = curl_exec($curl_instance);
        $header_size = curl_getinfo($curl_instance, CURLINFO_HEADER_SIZE);
        $body = json_decode(substr($response, $header_size));

        $status = True;
        $value = True;

        try {
            $status = $body->result->status;
            $value = $body->result->value;
            $res = $value;
        } catch (Exception $e) {
            $res = FALSE;
        }
        return $res;
    }
}
