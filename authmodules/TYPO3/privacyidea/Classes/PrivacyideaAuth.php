<?php
namespace NetKnightsGmbH\privacyidea;
/***************************************************************
 *  Copyright notice
 *
 *  (c) 2015 Cornelius Kölbel <cornelius.koelbel@netknights.it>
 *
 *  All rights reserved
 *
 *  This script is free software; you can redistribute it and/or modify
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


class PrivacyideaAuth {
	
		protected $url = NULL;
		protected $realm = NULL;
		protected $sslcheck = TRUE;

        /**
         * Constructor for this class
         *
         */
		public function __construct( $url, $realm=NULL, $sslcheck=TRUE ) {
			$this->url = $url;
			$this->realm = $realm;
			$this->sslcheck = $sslcheck;
			$this->logger = \TYPO3\CMS\Core\Utility\GeneralUtility::makeInstance('TYPO3\CMS\Core\Log\LogManager')->getLogger(__CLASS__);		  		
      }


		public function checkOtp($username, $password) {        	
			$curl_instance = curl_init();
			$escPassword = urlencode($password);
	      $escUsername = urlencode($username);
			$url = $this->url . '/validate/check';
			$this->logger->info("authenticating against $url");
			curl_setopt($curl_instance, CURLOPT_URL, $url);
			curl_setopt($curl_instance, CURLOPT_POST, 3);
			$poststring = "user=$username&pass=$password&realm=$this->realm";
			$this->logger->debug("using the poststring $poststring");
			curl_setopt($curl_instance, CURLOPT_POSTFIELDS, $poststring);						
	      curl_setopt($curl_instance, CURLOPT_HEADER, TRUE);
	      curl_setopt($curl_instance, CURLOPT_RETURNTRANSFER, TRUE);
	      if ($this->sslcheck) {
				curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 1);
				curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 1);
			} else {
				curl_setopt($curl_instance, CURLOPT_SSL_VERIFYHOST, 0);
				curl_setopt($curl_instance, CURLOPT_SSL_VERIFYPEER, 0);
			}	    
	    	$response = curl_exec($curl_instance);
	    	$this->logger->debug($response);
			$header_size = curl_getinfo($curl_instance,CURLINFO_HEADER_SIZE);
			$body = json_decode(substr( $response, $header_size ));
	       
			$status=True;
			$value=True;
    
			try {
				$status = $body->result->status;
				$value = $body->result->value;
				$res = $value;
			} catch (Exception $e) {
				$this->logger->error($e);
				$res = FALSE;
			}			
			return $res;
		}
}	