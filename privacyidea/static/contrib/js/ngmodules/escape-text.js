'use strict';

/**
 * Wraps the
 * @param text {string} text which is escaped
 */
angular.module('escape_text',[]).filter('escape_text', function () {
  return function (text) {
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
  };
});