class TemplateOptionsBase:
    TOKEN_COUNT = "token_count"
    TOKEN_TYPES = "token_types"
    TOKENS = "tokens"
    USER_MODIFIABLE = "user_modifiable"


class ContainerTemplateBase:
    template_option_values = {
        TemplateOptionsBase.TOKEN_COUNT: int,
        TemplateOptionsBase.TOKEN_TYPES: ["any"],
        TemplateOptionsBase.USER_MODIFIABLE: bool
    }

    def __init__(self, db_template):
        self._db_template = db_template

    def get_template_options(self):
        return self.template_option_values.keys()

    def get_template_option_value(self, option):
        return self.template_option_values[option]

    def get_type_specific_options(self):
        return []

    @classmethod
    def get_class_type(cls):
        """
        Returns the type of the container template class.
        """
        return "generic"

    @property
    def name(self):
        return self._db_template.name

    @name.setter
    def name(self, value):
        self._db_template.name = value
        self._db_template.save()

    @property
    def container_type(self):
        return self._db_template.container_type

    @container_type.setter
    def container_type(self, value):
        self._db_template.type = value
        self._db_template.save()

    @property
    def template_options(self):
        return self._db_template.options

    @template_options.setter
    def template_options(self, options):
        self._db_template.options = options
        self._db_template.save()

    @property
    def id(self):
        return self._db_template.id
