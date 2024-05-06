from privacyidea.lib.containertemplate.containertemplatebase import TemplateOptionsBase, ContainerTemplateBase


class YubikeyTemplateOptions(TemplateOptionsBase):
    PIN_POLICY = "pin_policy"


class YubikeyContainerTemplate:
    _custom_option_values = {
        TemplateOptionsBase.TOKEN_TYPES: ["certificate", "hotp", "yubikey", "yubico"],
        YubikeyTemplateOptions.PIN_POLICY: str
    }

    template_option_values = ContainerTemplateBase.template_option_values.copy()
    template_option_values.update(_custom_option_values)

    def __init__(self, db_template):
        super().__init__(db_template)

    def get_template_options(self):
        return self.template_option_values.keys()

    def get_template_option_value(self, option):
        return self.template_option_values[option]

    def get_type_specific_options(self):
        return [x for x in self.template_option_values.keys()
                if x not in ContainerTemplateBase.template_option_values.keys()]
