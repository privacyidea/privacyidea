# -*- coding: utf-8 -*-
"""
2022-07-24 Cornelius Kölbel <cornelius.koelbel@netknights.it>
           Move all MS CA mocking into this file.
"""
#
#  License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNE7SS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


class MyTemplateReply(object):
    def __init__(self, templates):
        self.templateNames = templates


class MyCAReply(object):
    def __init__(self, ca_list=None):
        self.caNames = ca_list or []


class MyCSRReply(object):
    def __init__(self, disposition=0, request_id=None, message="CSR invalid"):
        self.disposition = disposition
        self.dispositionMessage = message
        self.requestId = request_id or 4711


class MyCertReply(object):
    def __init__(self, certificate):
        self.cert = certificate


class MyCSRStatusReply(object):
    def __init__(self, disposition):
        self.disposition = disposition


class MyCertificateReply(object):
    def __init__(self, certificate):
        self.cert = certificate


class CAServiceMock(object):

    def __init__(self, config, mock_config=None):
        self.cas = mock_config.get("available_cas") or []
        self.templates = mock_config.get("ca_templates") or []
        self.disposition = mock_config.get("csr_disposition") or 0
        self.certificate = mock_config.get("certificate")

    def GetTemplates(self, _template_request):
        return MyTemplateReply(self.templates)

    def SubmitCSR(self, _submit_request):
        return MyCSRReply(self.disposition)

    def GetCAs(self, _carequest):
        return MyCAReply(self.cas)

    def GetCertificate(self, _get_certificate_request):
        return MyCertReply(certificate=self.certificate)

    def GetCSRStatus(self, _csr_status_request):
        return MyCSRStatusReply(disposition=self.disposition)

    def GetCertificate(self, _certificate_request):
        return MyCertificateReply(certificate=self.certificate)
