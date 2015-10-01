module.exports = function(grunt) {
grunt.loadNpmTasks('grunt-angular-gettext');
grunt.initConfig({
  nggettext_extract: {
    pot: {
      files: {
        'po/template.pot': ['privacyidea/static/components/*/views/*.html',
                            'privacyidea/static/templates/*.html',
                            'privacyidea/static/components/*/controllers/*.js',
                            'privacyidea/static/components/*/factories/*.js',
                            'privacyidea/static/*.js']
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
