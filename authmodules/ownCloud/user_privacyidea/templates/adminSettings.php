<?php
?>
<div class="section" id="privacyIDEASettings">

    <h2>privacyIDEA</h2>

    <p><em>
            <?php p($l->t('Two-Factor-Authentication for all users, authenticated against a central privacyIDEA system.')); ?>
        </em>
    </p>

    <input type="checkbox"
           name="enable_privacyidea" id="enable_privacyidea"
           value="1" <?php
    if ($_['enable_privacyidea']) print_unescaped('checked="checked"');
    ?> />
    <label for="enable_privacyidea">
        <?php p($l->t('Use privacyIDEA to authenticate the users.')); ?>
    </label><br/>

    <input type="checkbox"
           name="allow_normal_login" id="allow_normal_login"
           value="1" <?php
    if ($_['allow_normal_login']) print_unescaped('checked="checked"');
    ?> />
    <label for="allow_normal_login">
        <?php p($l->t('Also allow users to authenticate with their normal password.')); ?>
    </label><br/>

    <input type="checkbox"
           name="allow_api" id="allow_api"
           value="1" <?php
    if ($_['allow_api']) print_unescaped('checked="checked"');
    ?> />
    <label for="allow_api">
        <?php p($l->t('Allow API access to remote.php with static password.')); ?>
    </label><br/>

    <input type="checkbox"
           name="verify_ssl" id="verify_ssl"
           value="1" <?php
    if ($_['verify_ssl']) print_unescaped('checked="checked"');
    ?> />
    <label for="verify_ssl">
        <?php p($l->t('Verify the SSL certificate of the privacyIDEA server.')); ?>
    </label><br/>

    <label for="privacyidea_url">
        <?php p($l->t('URL of the privacyIDEA server')); ?>
    </label>
    <input type="text"
           name="privacyidea_url" id="privacyidea_url"
           value="<?php p($_['privacyidea_url']) ?>">
    <br/>

    <label for="privacyidea_proxy">
        <?php p($l->t('Address of proxy server')); ?>
    </label>
    <input type="text"
           name="privacyidea_proxy" id="privacyidea_proxy"
           value="<?php p($_['privacyidea_proxy']) ?>">
           <p>
           <em>
           <?php p($l->t('If you need a proxy server to connect to
           privacyIDEA, specify it like "https://your.proxy.server:8080"')); ?>
           </em>
           </p>
    <br/>

    <label for="realm">
        <?php p($l->t('Realm')); ?>
    </label>
    <input type="text"
           name="realm" id="realm"
           value="<?php p($_['realm']) ?>">
           <p>
           <em>
           <?php p($l->t('Specify a realm, if the users are not located in
           the default realm.'))
           ; ?>
           </em>
           </p>

    <br/>
    <!--
	<h3>Test connection</h3>
	<label for="username">
	    <?php p($l->t('Username')); ?>
	</label>
	<input type="text"
	    name="privacyidea_user" id="privacyidea_user">

	<label for="user_password">
	    <?php p($l->t('Password')); ?>
	</label>
	<input type="password"
	    name="user_password" id="user_password">

	<button id="test_privacyidea">Test connection</button>
-->
</div>
