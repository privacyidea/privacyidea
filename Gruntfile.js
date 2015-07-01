module.exports = function(grunt) {
grunt.loadNpmTasks('grunt-angular-gettext');
grunt.initConfig({
  nggettext_extract: {
    pot: {
      files: {
        'po/template.pot': ['privacyidea/static/components/*/views/*.html',
                            'privacyidea/static/templates/*.html']
      }
    },
  },
  nggettext_compile: {
    all: {
      files: {
        'privacyidea/static/components/translation/translations.js': ['po/*.po']
      }
    },
  },
})
};
