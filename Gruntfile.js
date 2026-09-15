module.exports = function(grunt) {
grunt.loadNpmTasks('grunt-angular-gettext');
grunt.initConfig({
  nggettext_extract: {
    pot: {
      files: {
        'po/template.pot': ['privacyidea/static_old/components/*/views/*.html',
                            'privacyidea/static_old/templates/*.html',
                            'privacyidea/static_old/components/*/controllers/*.js',
                            'privacyidea/static_old/components/*/factories/*.js',
                            'privacyidea/static_old/*.js']
      }
    },
  },
  nggettext_compile: {
    all: {
      files: {
        'privacyidea/static_old/components/translation/translations.js': ['po/*.po']
      }
    },
  },
})
};
