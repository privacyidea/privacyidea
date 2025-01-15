#!/bin/bash

set -e

# JavaScript files
declare -a JS
JS=(
    "jquery/dist/jquery.js"
    "angular/angular.js"
    "angular-hotkeys/build/hotkeys.js"
    "angular-inform/dist/angular-inform.js"
    "angular-inform/dist/angular-inform.js.map"
    "bootstrap/dist/js/bootstrap.js"
    "angular-ui-bootstrap/dist/ui-bootstrap-tpls.js"
)

# AngularJS modules
declare -a JS_NGMODULES
JS_NGMODULES=(
    "angular-gettext/dist/angular-gettext.js"
    "ng-idle/angular-idle.js"
    "angular-ui-router/release/angular-ui-router.js"
    "angular-ui-router/release/angular-ui-router.js.map"
    "ng-file-upload/dist/ng-file-upload.js"
    "isteven-angular-multiselect/isteven-multi-select.js"
    "angular-sanitize/angular-sanitize.js"
)

# CSS files
declare -a CSS
CSS=(
    "angular-inform/dist/angular-inform.css"
    "angular-inform/dist/angular-inform.css.map"
    "bootstrap/dist/css/bootstrap.css"
    "bootstrap/dist/css/bootstrap.css.map"
    "bootstrap/dist/css/bootstrap-theme.css"
    "bootstrap/dist/css/bootstrap-theme.css.map"
    "angular-hotkeys/build/hotkeys.css"
    "isteven-angular-multiselect/isteven-multi-select.css"
)

# Font files
declare -a FONTS
FONTS=("bootstrap/fonts/glyphicons-halflings-regular.eot"
    "bootstrap/fonts/glyphicons-halflings-regular.svg"
    "bootstrap/fonts/glyphicons-halflings-regular.ttf"
    "bootstrap/fonts/glyphicons-halflings-regular.woff"
    "bootstrap/fonts/glyphicons-halflings-regular.woff2")


for f in ${JS[@]}; do
    cp "node_modules/$f" "contrib/js/"
done

for f in ${JS_NGMODULES[@]}; do
    cp "node_modules/$f" "contrib/js/ngmodules/"
done

for f in ${CSS[@]}; do
    cp "node_modules/$f" "contrib/css/"
done

for f in ${FONTS[@]}; do
    cp "node_modules/$f" "contrib/fonts/"
done

