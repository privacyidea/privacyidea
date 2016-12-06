.. _paper_token:

Paper Token
-----------

.. index:: Paper Token

The token type *paper* lets you print out a list of OTP values, which you can
use to authenticate and cross of the list.

The paper token is based on the :ref:`hotp_token`. I.e. you need to use one
value after the other.

Customization
~~~~~~~~~~~~~

CSS
....

You can customize the look and feel of the printed paper token.
You may change the style sheep ``papertoken.css`` which is only loaded for
printing.

Header and Footer
.................

Then you may add a header in front and a footer behind the table containing
the OTP values.

Create the files

 * static/customize/views/includes/token.enrolled.paper.top.html
 * static/customize/views/includes/token.enrolled.paper.bottom.html

to display the contents before (top) and behind (bottom) the table.

Within these html templates you may use angular replacements. To get the
serial number of the token use

    {{ tokenEnrolled.serial }}

to get the name and realm of the user use

    {{ newUser.user }}
    {{ newUser.realm }}

A good example for the ``token.enrolled.paper.top.html`` is:

    <h1>{{ enrolledToken.serial }}</h1>
    <p>
      Please use the OTP values of your paper token in order one after the
      other. You may scratch of or otherwise mark used values.
    </p>

A good example for the ``token.enrolled.paper.bottom.html`` is:

    <p>
      The paper token is a weak second factor. Please assure, that noone gets
      hold  of this paper and can make a copy of it.
    </p>
    <p>
      Store it at a safe location.
    </p>

.. note:: You can change the directory *static/customize* to a URL that fits
   your needs the best by defining a variable `PI_CUSTOMIZATION` in the file
   *pi.cfg*. This way you can put all modifications in one place apart from
   the original code.

OTP Table
.........

If you want to change the complete layout of the table you need to
overwrite the file
``static/components/token/views/token.enrolled.paper.html``. The
scope variable {{ enrolledToken.otps }} contains an object with the complete
OTP value list.
