class TemplateOptionsBase:
    TOKEN_COUNT = "token_count"
    TOKEN_TYPES = "token_types"
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

    @property
    def name(self):
        return self._db_template.name

    @name.setter
    def name(self, value):
        self._db_template.name = value
        self._db_template.save()

    @property
    def container_type(self):
        return self._db_template.type

    @container_type.setter
    def container_type(self, value):
        self._db_template.type = value
        self._db_template.save()
