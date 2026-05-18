/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { PolicyTemplate, PolicyTemplateIndex } from "./policy-templates.service";

export const POLICY_TEMPLATE_INDEX: PolicyTemplateIndex = {
  enroll_tokenlabel: "Set the tokenlabel of a Google Authenticator to a sensible value during enrollment.",
  selfservice1: "Some sensible actions for users in the WebUI.",
  webui1: "Users need to authenticate against privacyIDEA.",
  webui2: "Users need to authenticate against their userstore.",
  superuser: "An administrator, who is allowed to do everything.",
  helpdesk: "A helpdesk user, who is allowed to manage all token stuff.",
  hide_welcome: "Hide the welcome dialog from the administrator."
};

export const POLICY_TEMPLATES: Record<string, PolicyTemplate> = {
  enroll_tokenlabel: {
    name: "enroll_tokenlabel",
    description: "Set the tokenlabel of a Google Authenticator to a sensible value.",
    scope: "enrollment",
    action: {
      tokenlabel: "{user}@{realm}/{serial}"
    }
  },

  hide_welcome: {
    name: "hide_welcome",
    scope: "webui",
    action: {
      hide_welcome_info: true
    }
  },

  webui1: {
    name: "webui1",
    scope: "webui",
    action: {
      login_mode: "privacyIDEA",
      logout_time: "240"
    }
  },

  webui2: {
    name: "webui2",
    scope: "webui",
    action: {
      login_mode: "userstore",
      logout_time: "240"
    }
  },

  selfservice1: {
    name: "selfservice1",
    scope: "user",
    action: {
      assign: true,
      auditlog: true,
      enrollHOTP: true,
      resync: true,
      reset: true,
      setpin: true
    }
  },

  helpdesk: {
    name: "helpdesk",
    scope: "admin",
    action: {
      enable: true,
      disable: true,
      auditlog: true,
      fetch_authentication_items: false,
      set: true,
      setpin: true,
      resync: true,
      reset: true,
      revoke: false,
      assign: true,
      unassign: true,
      importtokens: false,
      delete: true,
      userlist: true,
      machinelist: true,
      machinetokens: true,
      authitems: true,
      tokenrealms: true,
      getserial: true,
      getrandom: true,
      copytokenpin: true,
      copytokenuser: true,
      losttoken: true,
      adduser: false,
      enrollSMS: true,
      policydelete: false,
      policywrite: false,
      enrollTIQR: true,
      configdelete: false,
      enrollREMOTE: true,
      enrollSPASS: true,
      enrollPAPER: true,
      deleteuser: false,
      enrollEMAIL: true,
      resolverdelete: false,
      enrollMOTP: true,
      enrollPW: true,
      enrollHOTP: true,
      enrollQUESTION: true,
      enrollCERTIFICATE: true,
      configwrite: false,
      enrollTOTP: true,
      enrollREGISTRATION: true,
      enrollYUBICO: true,
      resolverwrite: false,
      updateuser: false,
      enrollU2F: true,
      mangle_machine_tokens: false,
      system_documentation: false,
      caconnectordelete: false,
      caconnectorwrite: false,
      mresolverdelete: false,
      enrollRADIUS: true,
      set_hsm_password: false,
      getchallenges: true,
      enroll4EYES: true,
      enrollYUBIKEY: true,
      enrollDAPLUG: true,
      mresolverwrite: false,
      enrollSSHKEY: true,
      manage_machine_tokens: false,
      smtpserver_write: false,
      radiusserver_write: false
    }
  },

  superuser: {
    name: "superuser",
    scope: "admin",
    action: {
      enable: true,
      disable: true,
      auditlog: true,
      fetch_authentication_items: true,
      set: true,
      setpin: true,
      resync: true,
      reset: true,
      revoke: true,
      assign: true,
      unassign: true,
      importtokens: true,
      delete: true,
      userlist: true,
      machinelist: true,
      machinetokens: true,
      authitems: true,
      tokenrealms: true,
      getserial: true,
      getrandom: true,
      copytokenpin: true,
      copytokenuser: true,
      losttoken: true,
      adduser: true,
      enrollSMS: true,
      policydelete: true,
      policywrite: true,
      enrollTIQR: true,
      configdelete: true,
      enrollREMOTE: true,
      enrollSPASS: true,
      enrollPAPER: true,
      deleteuser: true,
      enrollEMAIL: true,
      resolverdelete: true,
      enrollMOTP: true,
      enrollPW: true,
      enrollHOTP: true,
      enrollOCRA: true,
      enrollQUESTION: true,
      enrollCERTIFICATE: true,
      configwrite: true,
      enrollTOTP: true,
      enrollREGISTRATION: true,
      enrollYUBICO: true,
      resolverwrite: true,
      updateuser: true,
      enrollU2F: true,
      mangle_machine_tokens: true,
      system_documentation: true,
      caconnectordelete: true,
      caconnectorwrite: true,
      mresolverdelete: true,
      enrollRADIUS: true,
      set_hsm_password: true,
      getchallenges: true,
      enroll4EYES: true,
      enrollYUBIKEY: true,
      enrollDAPLUG: true,
      mresolverwrite: true,
      enrollSSHKEY: true,
      manage_machine_tokens: true,
      smtpserver_write: true,
      radiusserver_write: true,
      auditlog_download: true,
      clienttype: true,
      enrollpin: true,
      eventhandling_write: true,
      privacyideaserver_write: true,
      settokeninfo: true,
      smsgateway_write: true,
      triggerchallenge: true,
      managesubscription: true,
      enrollPUSH: true,
      enrollTAN: true,
      enrollVASCO: true,
      periodictask_write: true,
      statistics_read: true,
      statistics_delete: true,
      radiusserver_read: true,
      tokenlist: true,
      policyread: true,
      mresolverread: true,
      configread: true,
      smsgateway_read: true,
      privacyideaserver_read: true,
      resolverread: true,
      eventhandling_read: true,
      smtpserver_read: true,
      periodictask_read: true,
      caconnectorread: true,
      enrollINDEXEDSECRET: true,
      enrollWEBAUTHN: true,
      setrandompin: true,
      tokengroup_delete: true,
      tokengroups: true,
      tokengroup_list: true,
      tokengroup_add: true,
      serviceid_add: true,
      serviceid_delete: true,
      serviceid_list: true,
      enrollAPPLSPEC: true,
      daypassword_force_server_generate: true,
      enrollDAYPASSWORD: true,
      setdescription: true,
      container_description: true,
      container_info: true,
      container_state: true,
      container_create: true,
      container_delete: true,
      container_add_token: true,
      container_remove_token: true,
      container_assign_user: true,
      container_unassign_user: true,
      container_realms: true,
      container_list: true,
      enrollPASSKEY: true,
      container_register: true,
      container_unregister: true,
      container_rollover: true,
      container_template_create: true,
      container_template_delete: true,
      container_template_list: true
    }
  }
};
