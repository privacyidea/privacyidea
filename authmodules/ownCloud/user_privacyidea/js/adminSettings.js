$(document).ready(function() {

        // On data change we save the settings.
        $('#privacyIDEASettings input[type="checkbox"]').change(function() {
                var value = 'no';
                if (this.checked) {
                        value = 'yes';
                }
                OC.AppConfig.setValue('privacyIDEA', $(this).attr('name'), value);
        });

        $('#privacyIDEASettings input[type="text"]').keyup(function() {
                OC.AppConfig.setValue('privacyIDEA', $(this).attr('name'),
                    $(this).val());
        });

        $('#test_privacyidea').click(function(){
           alert($('#privacyidea_user').val());
           alert($('#user_password').val());
        });
});
