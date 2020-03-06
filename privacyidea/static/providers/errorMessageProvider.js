/**
 * https://www.privacyidea.org
 * (c) Cornelius  Kölbel, cornelius@privacyidea.org
 *
 * 2020-02-14 Jean-Pierre Höhmann, <jean-pierre.hoehmann@netknights.it>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program. If not, see <http://www.gnu.org/licenses/>.
 */

/*
 * Messages for the various types of DOMException.
 *
 * This will provide localized error messages for DOMExceptions. The factory
 * provides a dictionary, with one error message for each type of DOMException.
 * The included types are the standardized errors as specified by WebIDL
 * Level 1, along with any new error messages present in the editors draft for
 * WebIDL, as it stood in the 21st of January 2020 (the latter are needed for
 * WebAuthn).
 */
angular
    .module('privacyideaApp.errorMessage', [])
    .factory('domExceptionErrorMessage', [
        'gettextCatalog',
        function domExceptionErrorMessageFactory(
            gettextCatalog
        ) {
            return {
                "IndexSizeError": gettextCatalog.getString(
                    "The index is not in the allowed range"
                ),
                "HierarchyRequestError": gettextCatalog.getString(
                    "The operation would yield an incorrect node tree."
                ),
                "WrongDocumentError": gettextCatalog.getString(
                    "The object is in the wrong document."
                ),
                "InvalidCharacterError": gettextCatalog.getString(
                    "The string contains invalid characters."
                ),
                "NoModificationAllowedError": gettextCatalog.getString(
                    "The object can not be modified."
                ),
                "NotFoundError": gettextCatalog.getString(
                    "The object can not be found here."
                ),
                "NotSupportedError": gettextCatalog.getString(
                    "The operation is not supported."
                ),
                "InUseAttributeError": gettextCatalog.getString(
                    "The attribute is in use."
                ),
                "InvalidStateError": gettextCatalog.getString(
                    "The object is in an invalid state."
                ),
                "SyntaxError": gettextCatalog.getString(
                    "The string did not match the expected pattern."
                ),
                "InvalidModificationError": gettextCatalog.getString(
                    "The object can not be modified in this way."
                ),
                "NamespaceError": gettextCatalog.getString(
                    "The operation is not allowed by namespaces in XML."
                ),
                "InvalidAccessError": gettextCatalog.getString(
                    "The object does not support the operation or argument."
                ),
                "SecurityError": gettextCatalog.getString(
                    "The operation is insecure."
                ),
                "NetworkError": gettextCatalog.getString(
                    "A network error occurred."
                ),
                "AbortError": gettextCatalog.getString(
                    "The operation was aborted."
                ),
                "URLMismatchError": gettextCatalog.getString(
                    "The given URL does not match another URL."
                ),
                "QuotaExceededError": gettextCatalog.getString(
                    "The quota has been exceeded."
                ),
                "TimeoutError": gettextCatalog.getString(
                    "The operation timed out."
                ),
                "InvalidNodeTypeError": gettextCatalog.getString(
                    "The supplied node is incorrect or has an incorrect ancestor for this operation."
                ),
                "DataCloneError": gettextCatalog.getString(
                    "The object can not be cloned."
                ),
                "EncodingError": gettextCatalog.getString(
                    "The encoding operation (either encoded or decoding) failed." /* (sic) */
                ),
                "NotReadableError": gettextCatalog.getString(
                    "The I/O operation failed."
                ),
                "UnknownError": gettextCatalog.getString(
                    "The operation failed for an unknown transient reason (e.g. out of memory)."
                ),
                "ConstraintError": gettextCatalog.getString(
                    "A mutation operation in a transaction failed because a constraint was not satisfied."
                ),
                "DataError": gettextCatalog.getString(
                    "Provided data is inaccurate."
                ),
                "TransactionInactiveError": gettextCatalog.getString(
                    "A request was placed against a transaction which is currently not active, or which is finished."
                ),
                "ReadOnlyError": gettextCatalog.getString(
                    "The mutating operation was attempted in a \"readonly\" transaction."
                ),
                "VersionError": gettextCatalog.getString(
                    "An attempt was made to open a database using a lower version than the existing version."
                ),
                "OperationError": gettextCatalog.getString(
                    "The operation failed for an operation-specific reason."
                ),
                "NotAllowedError": gettextCatalog.getString(
                    "The request is not allowed by the user agent or the platform in the current context, possibly because the user denied permission."
                )
            };
        }
    ]);
