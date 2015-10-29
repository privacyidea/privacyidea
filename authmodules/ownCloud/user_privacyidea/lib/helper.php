<?php

namespace OCA\user_privacyidea\lib;

class Helper
{

    public static function is_privacyidea_enabled()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'enable_privacyidea', 'yes');
        return ($result === 'yes') ? true : false;
    }

    public static function is_ssl_check()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'verify_ssl', 'yes');
        return ($result === 'yes') ? true : false;
    }

    public static function get_url()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'privacyidea_url', 'https://localhost');
        \OCP\Util::writeLog('user_privacyidea', "Gettting result: $result",
            \OCP\Util::DEBUG);
        return $result;
    }

    public static function get_realm()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'realm', '');
        \OCP\Util::writeLog('user_privacyidea', "Getting result for realm: $result",
            \OCP\Util::DEBUG);
        return $result;
    }

    public static function get_proxy()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'privacyidea_proxy', '');
        \OCP\Util::writeLog('user_privacyidea', "Getting result for proxy: $result",
            \OCP\Util::DEBUG);
        return $result;
    }

    public static function is_normal_login_allowed()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'allow_normal_login', 'no');
        return ($result === 'yes') ? true : false;
    }

    public static function is_api_allowed()
    {
        $appConfig = \OC::$server->getAppConfig();
        $result = $appConfig->getValue('privacyIDEA',
            'allow_api', 'no');
        return ($result === 'yes') ? true : false;
    }

}
