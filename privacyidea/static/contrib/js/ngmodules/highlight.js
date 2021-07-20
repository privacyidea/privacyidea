'use strict';

/**
 * Wraps the
 * @param text {string} haystack to search through
 * @param search {string} needle to search for
 * @param [caseSensitive] {boolean} optional boolean to use case-sensitive searching
 */
angular.module('ui.highlight',[]).filter('highlight', function () {
  return function (text, search, caseSensitive) {
    if (text && (search || angular.isNumber(search))) {
      // replace html special characters in so that won't get interpreted by ng-bind-html
      text = text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
      search = search.toString();
      if (caseSensitive) {
        var search_modifier = 'gi';
      } else {
        var search_modifier = 'g';
      }
      return text.replace(new RegExp(search, 'gi'), '<span class="ui-match">$&</span>');
    } else {
      return text;
    }
  };
});
