<?php

/**
 * privacyidea authentication module.
 * 2015-04-11 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *            minor changes by code climate
 * 2014-09-29 Cornelius Kölbel, cornelius@privacyidea.org
 * 
 * This is forked from simplesamlphp-linotp,
 * (https://github.com/lsexperts/simplesamlphp-linotp)
 * which is based on Radius.php
 *
 */
class sspmod_privacyidea_Auth_Source_privacyidea extends sspmod_core_Auth_UserPassBase {

	/**
	 * The URL of the privacyidea server
	 */
	private $privacyideaserver;

	/**
	 * If the sslcert should be checked
	 */
	private $sslverifyhost;

	/**
	 * If the sslcert should be checked
	 */
	private $sslverifypeer;
	
	/**
	 * The realm of the user
	 */
	private $realm;
	
	/**
	 * The attribute map. It is an array
	 */
	 
	private $attributemap = array();
	
	/**
	 * Constructor for this authentication source.
	 *
	 * @param array $info  Information about this authentication source.
	 * @param array $config  Configuration.
	 */
	public function __construct($info, $config) {
		assert('is_array($info)');
		assert('is_array($config)');

		/* Call the parent constructor first, as required by the interface. */
		parent::__construct($info, $config);

		if (array_key_exists('privacyideaserver', $config)) {
            $this->privacyideaserver = $config['privacyideaserver'];
        }
        if (array_key_exists('realm', $config)) {
            $this->realm = $config['realm'];
        }
        if (array_key_exists('sslverifyhost', $config)) {
            $this->sslverifyhost = $config['sslverifyhost'];
        }
        if (array_key_exists('sslverifypeer', $config)) {
            $this->sslverifypeer = $config['sslverifypeer'];
        }
        if (array_key_exists('attributemap', $config)) {
			$this->attributemap = $config['attributemap'];
		}
		
	}


	/**
	 * Attempt to log in using the given username and password.
	 *
	 * @param string $username  The username the user wrote.
	 * @param string $password  The password the user wrote.
	 * @return array  Associative array with the users attributes.
	 */
	protected function login($username, $password) {
		assert('is_string($username)');
		assert('is_string($password)');

        	$curl_instance = curl_init();
        
	        $escPassword = urlencode($password);
	        $escUsername = urlencode($username);

		$url = $this->privacyideaserver . '/validate/samlcheck?user='.$escUsername
			.'&pass=' . $escPassword . '&realm=' . $this->realm;
		
		//throw new Exception("url: ". $url);
		SimpleSAML_Logger::debug("privacyidea URL:" . $url);
	
        	curl_setopt($curl_instance, CURLOPT_URL, $url);
	        curl_setopt($curl_instance, CURLOPT_HEADER, TRUE);
	        curl_setopt($curl_instance, CURLOPT_RETURNTRANSFER, TRUE);
	        if ($this->sslverifyhost) {
			curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 1);
		} else {
			curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 0);
		}
		if ($this->sslverifypeer) {
			curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 1);
		} else {
			curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 0);
		}
	    
	    	$response = curl_exec($curl_instance);
		$header_size = curl_getinfo($curl_instance,CURLINFO_HEADER_SIZE);
		$body = json_decode(substr( $response, $header_size ));
	       
		$status=True;
		$value=True;
    
		try {
			$status = $body->result->status;
			$value = $body->result->value->auth;
		} catch (Exception $e) {
			throw new SimpleSAML_Error_BadRequest("We were not able to read the response from the privacyidea server:" . $e);
		}
		
	    	if ( False===$status ) {
			/* We got a valid JSON respnse, but the STATUS is false */
			throw new SimpleSAML_Error_BadRequest("Valid JSON response, but some internal error occured in privacyidea server.");
				
		} else {
			/* The STATUS is true, so we need to check the value */
			if ( False===$value ) {
				throw new SimpleSAML_Error_Error("WRONGUSERPASS");
			}
		}
		/* status and value are true
		 * We can go on and fill attributes
		 */

		/* If we get this far, we have a valid login. */
		$attributes = array();
		$arr = array( "username", "surname", "email", "givenname", "mobile", "phone", "realm", "resolver");
		reset($arr);
		foreach ( $arr as $key) {
			if (array_key_exists($key, $this->attributemap)) {
				$attributes[$this->attributemap[$key]] = array( $body->result->value->attributes->$key );
			} else {
				$attributes[$key] = array( $body->result->value->attributes->$key );
			}	
		}
		return $attributes;
	}

}
