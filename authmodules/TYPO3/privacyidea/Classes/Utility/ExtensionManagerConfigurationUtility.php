<?php
namespace NetKnightsGmbH\privacyidea\Utility;

/***************************************************************
 *
 *  Copyright notice
 *
 *  (c) 2015 Cornelius Kölbel <cornelius.koelbel@netknights.it>, NetKnights GmbH
 *           Jakob Lechner <mail@jalr.de>
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

class ExtensionManagerConfigurationUtility {

	/**
	 * @var array
	 */
	protected $beModes = array();

	/**
	 * Initializes this object.
	 *
	 * @return void
	 */
	private function init() {
		$this->beModes = array('disabled', 'adminOnly', 'allUsers');
		$this->getLanguageService()->includeLLFile('EXT:privacyidea/Resources/Private/Language/locallang.xlf');
	}

	/**
	 * Renders a selector element that allows to select how privacyidea is used in backend
	 *
	 * @param array $params Field information to be rendered
	 * @param \TYPO3\CMS\Core\TypoScript\ConfigurationForm $pObj The calling parent object.
	 * @return string The HTML selector
	 */
	public function buildBeModeSelector(array $params, $pObj) {
		$this->init();

		$propertyName = $params['propertyName'];
		$pField = '';
		foreach ($this->beModes as $beMode) {
			$sel = ($params['fieldValue'] == $beMode ? ' selected="selected" ' : '');
			$pField .= '<option value="' . htmlspecialchars($beMode) . '"' . $sel . '>' . $this->getLanguageService()->getLL('ext.privacyidea.beMode.' . $beMode) . '</option>';
		}
		$pField = '<select id="' . $propertyName . '" name="' . $params['fieldName'] . '" >' . $pField . '</select>';
		return $pField;
	}

	/**
	 * @return \TYPO3\CMS\Lang\LanguageService
	 */
	protected function getLanguageService() {
		return $GLOBALS['LANG'];
	}

}

