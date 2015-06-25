<?php
\OCP\App::registerAdmin('user_privacyidea', 'adminSettings');

OC::$CLASSPATH['OC_User_PRIVACYIDEA'] = 'apps/user_privacyidea/lib/otp_privacyidea.php';

$enabled = OCP\Config::getAppValue('privacyIDEA','enable_privacyidea');
if($enabled === "yes") {
    OCP\Util::writeLog('user_privacyidea', 'privacyIDEA is enabled',
    OCP\Util::DEBUG);

    $usedBackends = OC_User::getUsedBackends();
    OC_User::clearBackends();
    $piBackend = new OC_User_PRIVACYIDEA();
    // register all previously used backend
    $piBackend->registerBackends($usedBackends);
    // register our own user backend
    OC_User::useBackend($piBackend);

} else {
    OCP\Util::writeLog('user_privacyidea', 'privacyIDEA is disabled: '.$enabled, OCP\Util::DEBUG);
}
