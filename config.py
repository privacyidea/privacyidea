import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # SQL_ALCHEMY_DATABASE_URI = "mysql://privacyidea:XmbSrlqy5d4IS08zjz"
    # "GG5HTt40Cpf5@localhost/privacyidea"
    PI_ENCFILE = "tests/testdata/enckey"
    PI_HSM = "default"
    PI_AUDIT_MODULE = "privacyidea.lib.auditmodules.sqlaudit"
    PI_AUDIT_KEY_PRIVATE = "tests/testdata/private.pem"
    PI_AUDIT_KEY_PUBLIC = "tests/testdata/public.pem"
    # PI_AUDIT_SQL_URI = sqlite://


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 't0p s3cr3t'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    # This is used to encrypt the auth token
    SECRET_KEY = 'secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    # This is used to encrypt the admin passwords
    PI_PEPPER = ""
    # This is only for testing encrypted files
    PI_ENCFILE_ENC = "tests/testdata/enckey.enc"


class ProductionConfig(Config):
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    SQLALCHEMY_DATABASE_URI = "mysql://pi2:pi2@localhost/pi2"
    SECRET_KEY = os.environ.get('SECRET_KEY') or 't0p s3cr3t'
    # This is used to encrypt the admin passwords
    PI_PEPPER = "Never know..."


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
