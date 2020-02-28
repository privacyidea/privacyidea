/*!
   angular-inform v0.0.18
   (c) 2014 (null) McNull https://github.com/McNull/angular-inform
   License: MIT
*/
(function(angular) {

var inform = angular.module('inform', []);


inform.controller('InformCtrl', ["$scope", "inform", function($scope, inform) {

  $scope.messages = inform.messages();
  $scope.remove = inform.remove;
  $scope.cancelTimeout = inform.cancelTimeout;
  $scope.setTimeout = inform.setTimeout;

}]);

inform.directive('inform', function () {
  return {
    restrict: 'AE',
    templateUrl: 'angular-inform/directive.ng.html',
    controller: 'InformCtrl'
  };
});
inform.provider('inform', function () {

  var provider = this;

  this._defaults = {
    type: 'default',
    ttl: 5000
  };

  this.defaults = function (options) {
    provider._defaults = angular.extend(provider._defaults, options || {});
    return provider._defaults;
  };


  this.$get = ['$timeout', '$sce', function ($timeout, $sce) {

    var _messages = [];

    function _indexOf(predicate) {
      var i = _messages.length;

      while (i--) {
        if (predicate(_messages[i])) {
          return i;
        }
      }

      return -1;
    }

    function cancelTimeout(msg) {
      if (msg.timeout) {
        $timeout.cancel(msg.timeout);
        delete msg.timeout;
      }
    }

    function setTimeout(msg) {

      cancelTimeout(msg);

      if (msg.ttl > 0) {
        msg.timeout = $timeout(function () {
          remove(msg);
        }, msg.ttl);
      }
    }

    function add(content, options) {

      var msg = angular.extend({}, provider._defaults, options);

      if(!angular.isString(content)) {
        content = '<pre><code>' + JSON.stringify(content, null, '  ') + '</code></pre>';
        msg.html = true;
      }

      var idx = _indexOf(function (x) {
        return x.content.toString() === content && x.type == msg.type;
      });

      if (idx >= 0) {

        msg = _messages[idx];
        msg.count += 1;

      } else {

        msg.content = content;

        if(msg.html) {
          msg.content = $sce.trustAsHtml(content);
        }

        msg.tickCount = +new Date();
        msg.count = 1;

        _messages.push(msg);
      }

      setTimeout(msg);

      return msg;
    }

    function remove(msg) {

      var idx = _indexOf(function (x) {
        return x === msg;
      });

      if (idx >= 0) {
        _messages.splice(idx, 1);
        cancelTimeout(msg);
      }
    }

    function clear() {
      _messages.length = 0;
    }

    return {
      messages: function () {
        return _messages;
      },
      add: add,
      remove: remove,
      clear: clear,
      cancelTimeout: cancelTimeout,
      setTimeout: setTimeout
    };
  }];

});

angular.module('inform-exception', ['inform'])
  .config(["$provide", function($provide) {
    $provide.decorator('$exceptionHandler', ['$delegate', '$injector',function($delegate, $injector) {

      var inform;

      return function(exception, cause) {
        try {
          inform = inform || $injector.get('inform');
          inform.add(exception.toString(), { type: 'danger', ttl: 0 });
        } catch(ex) {
          console.log('$exceptionHandler', ex);
        }
        $delegate(exception, cause);
      };
    }]);
  }]);

angular.module('inform-http-exception', ['inform'])

  .factory('informHttpInterceptor', ["$q", "inform", function ($q, inform) {

    function interceptor(rejection) {
      try {
        var msg = 'Network error (' + rejection.status + '): ' + rejection.statusText;
        inform.add(msg, { type: 'danger', ttl: 0});
      } catch(ex) {
        console.log('$httpProvider', ex);
      }

      return $q.reject(rejection);
    }

    return {
      requestError: interceptor,
      responseError: interceptor
    };

  }])

  .config(["$httpProvider", function ($httpProvider) {
    $httpProvider.interceptors.push('informHttpInterceptor');
  }]);

// Automatically generated.
// This file is already embedded in your main javascript output, there's no need to include this file
// manually in the index.html. This file is only here for your debugging pleasures.
angular.module('inform').run(['$templateCache', function($templateCache){
  $templateCache.put('angular-inform/directive.ng.html', '<div class=\"inform\"><div ng-repeat=\"msg in messages | orderBy:\'-tickCount\'\" class=\"inform-message-wrap\"><div class=\"inform-message alert alert-{{ msg.type }} alert-dismissible\" role=\"alert\" ng-mouseenter=\"cancelTimeout(msg)\" ng-mouseleave=\"setTimeout(msg)\"><button type=\"button\" class=\"close\" ng-click=\"remove(msg)\"><span>&times;</span></button> <span class=\"inform-message-content\"><span class=\"badge inform-badge\" ng-if=\"msg.count > 1\">{{ msg.count }}</span> <span ng-if=\"msg.html\" ng-bind-html=\"msg.content\"></span> <span ng-if=\"!msg.html\" ng-bind=\"msg.content\"></span></span></div></div></div>');
}]);
})(angular);
//# sourceMappingURL=angular-inform.js.map