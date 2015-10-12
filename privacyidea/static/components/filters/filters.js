myApp.filter('capitalize', function () {
    return function (input, all) {
        return (!!input) ? input.replace(/([^\W_]+[^\s-]*) */g,
            function (txt) {
                return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
            }) : '';
    };
});

/*
 This is a tokeninfo filter, that truncates long entries like
 "sshkey" and "certificate".
 */
myApp.filter('truncate', function () {
    return function (input, charCount) {
        var output  = input;
        if (output.length > charCount) {
          output = output.substr(0, charCount) + '...';
        }
        return output;
        };
});
