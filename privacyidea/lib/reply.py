# -*- coding: utf-8 -*-
#  privacyIDEA is a fork of LinOTP
#  May 08, 2014 Cornelius Kölbel
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
#  Copyright (C) 2010 - 2014 LSE Leading Security Experts GmbH
#  License:  AGPLv3
#  contact:  http://www.linotp.org
#            http://www.lsexperts.de
#            linotp@lsexperts.de
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
request and reply handling
'''

import qrcode
import StringIO
import urllib

import json

from pylons import request
from pylons import tmpl_context as c

from privacyidea.lib.error       import privacyIDEAError
from privacyidea.lib.util        import get_version
from privacyidea.lib.log import log_with

optional = True
required = False

PRIVACYIDEA_ERRORS = [707]

httpErr = {
        '400': 'Bad Request',
        '401': 'Unauthorized',
        '403': 'Forbidden',
        '404': 'Not Found',
        '410': 'Gone',
        '500': 'Internal Server Error',
        '501': 'Not Implemented',
        '502': 'Bad Gateway',
        '503': 'Service Unavailable',
        }

resp = """
<html>
<head>
<title>%s %s</title>
</head>
<body>
<h1>%s %s</h1>
%s
<br>
<br>
</body>
</html>
"""

import logging
log = logging.getLogger(__name__)

def sendError(response, exception, id=1, context=None):
    '''
    sendError - return a json error result document

    remark:
     the 'context' is especially required to catch errors from the _before_
     methods. The return of a _before_ must be of type response and
     must have the attribute response._exception set, to stop further
     processing, which otherwise will have ugly results!!

    :param response:  the pylon response object
    :type  response:  response object
    :param exception: should be a privacyidea exception (s. privacyidea.lib.error.py)
    :type  exception: exception
    :param id:        id value, for future versions
    :type  id:        int
    :param context:   default is None or 'before'
    :type  context:   string

    :return:     json rendered sting result
    :rtype:      string

    '''
    ret = ''
    errId = -311

    ## handle the different types of exception:
    ## Exception, privacyIDEAError, str/unicode
    if hasattr(exception, '__class__') == True \
    and isinstance(exception, Exception):
        errDesc = unicode(exception)
        if isinstance(exception, privacyIDEAError):
            errId = exception.getId()

    elif type(exception) in [str, unicode]:
        errDesc = unicode(exception)

    else:
        errDesc = u"%r" % exception

    HTTP_ERROR = False
    ## check if we have an additional request parameter 'httperror'
    ## which triggers the error to be delivered as HTTP Error
    try:
        httperror = request.params.get('httperror')
    except Exception as exx:
        httperror = "%r" % exx

    if httperror is not None:
        ## now lookup in the config, which privacyidea errors should be shwon as
        ## HTTP error
        privacyidea_errors = c.privacyideaConfig.get('privacyidea.errors', None)
        if privacyidea_errors is None:
            HTTP_ERROR = True
        else:
            privacyidea_errors = privacyidea_errors.split(',')
            if unicode(errId) in privacyidea_errors:
                HTTP_ERROR = True
            else:
                HTTP_ERROR = False

    if HTTP_ERROR is True:
        ## httperror as param exist but is not defined
        ## so fallback to 500 - Internal Server Error
        if len(httperror) == 0: httperror = '500'

        ## prepare the response to be of text/html
        response.content_type = 'text/html'
        response.status = httperror

        code = httperror
        status = httpErr.get(httperror, '')
        desc = '[%s] %d: %s' % (get_version(), errId, errDesc)
        ret = resp % (code, status, code, status, desc)

        if context in ['before', 'after']:
            response._exception = exception
            response.text = u'' + ret
            ret = response

    else:
        response.content_type = 'application/json'
        res = { "jsonrpc": "2.0",
                "result" :
                    {"status": False,
                        "error": {
                            "code"    :   errId,
                            "message" :   errDesc,
                            },
                    },
                 "version": get_version(),
                 "id": id
            }

        ret = json.dumps(res, indent=3)

        if context in ['before', 'after']:
            response._exception = exception
            response.body = ret
            ret = response

    return ret


def sendResult(response, obj, id=1, opt=None):
    '''
        sendResult - return an json result document

        :param response: the pylons response object
        :type  response: response object
        :param obj:      simple result object like dict, sting or list
        :type  obj:      dict or list or string/unicode
        :param  id:      id value, for future versions
        :type   id:      int
        :param opt:      optional parameter, which allows to provide more detail
        :type  opt:      None or simple type like dict, list or string/unicode

        :return:     json rendered sting result
        :rtype:      string

    '''

    response.content_type = 'application/json'

    res = { "jsonrpc": "2.0",
            "result": { "status": True,
                        "value": obj,
                      },
           "version": get_version(),
           "id": id }

    if opt is not None and len(opt) > 0:
        res["detail"] = opt

    return json.dumps(res, indent=3)

def sendCSVResult(response, obj, flat_lines=False, filename="privacyidea-tokendata.csv"):
    '''
    returns a CSV document of the input data (like in /admin/show)

    :param response: The pylons response object
    :param obj: The data, that gets serialized as CSV
    :type obj: JSON object
    :param flat_lines: If True the object only contains a list of the dict { 'cell': ..., 'id': ... } 
                        as in all the flexigrid functions.
    'type flat_lines: boolean
    '''
    delim = "'"
    response.content_type = "application/force-download"
    response.headers['Content-disposition'] = 'attachment; filename=%s' % filename
    output = u""

    if not flat_lines:
        # Do the header
        for k, v in obj.get("data", {})[0].iteritems():
            output += "%s%s%s, " % (delim, k, delim)
        output += "\n"

        # Do the data
        for row in obj.get("data", {}):
            for val in row.values():
                if type(val) in [str, unicode]:
                    value = val.replace("\n", " ")
                else:
                    value = val
                output += "%s%s%s, " % (delim, value, delim)
            output += "\n"
    else:
        for l in obj:
            for elem in l.get("cell", []):
                output += "'%s', " % elem
            
            output += "\n"

    return output

def sendXMLResult(response, obj, id=1):
    response.content_type = 'text/xml'
    res = '<?xml version="1.0" encoding="UTF-8"?>\
            <jsonrpc version="2.0">\
            <result>\
                <status>True</status>\
                <value>%s</value>\
            </result>\
            <version>%s</version>\
            <id>%s</id>\
            </jsonrpc>' % (obj, get_version(), id)
    return res


def sendXMLError(response, exception, id=1):
    response.content_type = 'text/xml'
    if not hasattr(exception, "getId"):
        errId = -311
        errDesc = str(exception)
    else:
        errId = exception.getId()
        errDesc = exception.getDescription()
    res = '<?xml version="1.0" encoding="UTF-8"?>\
            <jsonrpc version="2.0">\
            <result>\
                <status>False</status>\
                <error>\
                    <code>%s</code>\
                    <message>%s</message>\
                </error>\
            </result>\
            <version>%s</version>\
            <id>%s</id>\
            </jsonrpc>' % (errId, errDesc, get_version(), id)
    return res

@log_with(log)
def sendQRImageResult(response, data, param=None, id=1, typ='html'):
    '''
    method
        sendQRImageResult

    arguments
        response - the pylon response object
        param    - the paramters of the request
        id       -
        html     - print qrcode wrapped by html or not

    '''
    width = 0
    alt = None
    ret = None

    if param is None:
        param = {}

    if 'qr' in param:
        typ = param.get('qr')
        del param['qr']

    if 'width' in param:
        width = param.get('width')
        del param['width']

    if 'alt' in param:
        alt = param.get('alt')
        del param['alt']

    if typ in ['img', 'embed']:
        response.content_type = 'text/html'
        ret = create_img(data, width, alt)

    elif typ in ['png']:
        response.content_type = 'image/png'
        ret = create_png(data)
        response.content_length = len(ret)

    else:
        response.content_type = 'text/html'
        ret = create_html(data, width, param)

    return ret


def create_png(data, alt=None):
    '''

    '''

    img = qrcode.make(data)

    output = StringIO.StringIO()
    img.save(output)
    o_data = output.getvalue()
    output.close()

    return o_data


def create_img(data, width=0, alt=None):
    '''
        _create_img - create the qr image data

        :param data: input data that will be munched into the qrcode
        :type  data: string
        :param width: image width in pixel
        :type  width: int

        :return: <img/> taged data
        :rtype:  string
    '''
    width_str = ''
    alt_str = ''

    o_data = create_png(data, alt=alt)
    data_uri = o_data.encode("base64").replace("\n", "")

    if width != 0:
        width_str = " width=%d " % (int(width))

    if alt is not None:
        val = urllib.urlencode({'alt':alt})
        alt_str = " alt=%r " % (val[len('alt='):])

    ret_img = '<img %s  %s  src="data:image/png;base64,%s"/>' % (alt_str, width_str, data_uri)

    return ret_img


def create_html(data, width=0, alt=None):
    '''
        _create_html - create the qr image data embeded in html tag

        :param data: input data that will be munched into the qrcode
        :type  data: string
        :param width: image width in pixel
        :type  width: int

        :return: <img/> taged data
        :rtype:  string
    '''
    alt_str = ''

    img = create_img(data, width=width, alt=alt)
    if alt is not None:
        if type(alt) in (str, u''):
            alt_str = '<p>%s</p>' % alt
        elif type(alt) == dict:
            alta = []
            for k in alt.keys():
                alta.append('<li> %s:%s </li>' % (k, alt.get(k)))
            alt_str = '<ul>%s</ul>' % " ".join(alta)
        elif type(alt) == list:
            alta = []
            for k in alt:
                alta.append('<li> %s </li>' % (k))


    ret_html = '<html><body>%s%s</body></html>' % (img , alt_str)

    return ret_html


#eof#######################################################

