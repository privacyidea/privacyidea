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

import { Routes } from "@angular/router";
import { detailsTitle, newTitle, PAGE_NAMES } from "@core/route-titles";
import { dashboardGuard } from "@app/guards/dashboard.guard";
import { logsLandingRedirect } from "@app/routing/landing-redirects";
import { pendingChangesGuard } from "@app/guards/pending-changes.guard";
import { AuditComponent } from "@components/logs/audit/audit.component";
import { DashboardComponent } from "@components/dashboard/dashboard.component";
import { ClientsComponent } from "@components/logs/clients/clients.component";
import { AuthenticationLog } from "@components/logs/authentication-log/authentication-log";
import { LockedUsersComponent } from "@components/logs/locked-users/locked-users.component";
import { BlocklistComponent } from "@components/logs/blocklist/blocklist.component";
import { MachineDetailsComponent } from "@components/configuration/machines/machine-details/machine-details.component";
import { MachinesComponent } from "@components/configuration/machines/machines.component";
import { PeriodicTaskEditComponent } from "@components/configuration/periodic-task/periodic-task-edit/periodic-task-edit.component";
import { PeriodicTaskComponent } from "@components/configuration/periodic-task/periodic-task.component";
import { SubscriptionComponent } from "@components/configuration/subscription/subscription.component";
import { SystemConfigComponent } from "@components/configuration/system/system-config.component";
import { TokenTypeConfigComponent } from "@components/configuration/token-type-config/token-type-config.component";
import { EventEditPageComponent } from "@components/event/event-edit-page/event-edit-page.component";
import { EventComponent } from "@components/event/event.component";
import { CaConnectorsComponent } from "@components/external-services/ca-connectors/ca-connectors.component";
import { ApiClientEditComponent } from "@components/policies/api-clients/api-client-edit/api-client-edit.component";
import { ApiClientsComponent } from "@components/policies/api-clients/api-clients.component";
import { NewCaConnectorComponent } from "@components/external-services/ca-connectors/new-ca-connector/new-ca-connector.component";
import { NewPrivacyideaServerComponent } from "@components/external-services/privacyidea-servers/new-privacyidea-server/new-privacyidea-server.component";
import { PrivacyideaServersComponent } from "@components/external-services/privacyidea-servers/privacyidea-servers.component";
import { NewRadiusServerComponent } from "@components/external-services/radius-servers/new-radius-server/new-radius-server.component";
import { RadiusServersComponent } from "@components/external-services/radius-servers/radius-servers.component";
import { NewServiceIdComponent } from "@components/external-services/service-ids/new-service-id/new-service-id.component";
import { ServiceIdsComponent } from "@components/external-services/service-ids/service-ids.component";
import { NewSmsGatewayComponent } from "@components/external-services/sms-gateways/new-sms-gateway/new-sms-gateway.component";
import { SmsGatewaysComponent } from "@components/external-services/sms-gateways/sms-gateways.component";
import { NewSmtpServerComponent } from "@components/external-services/smtp-servers/new-smtp-server/new-smtp-server.component";
import { SmtpServersComponent } from "@components/external-services/smtp-servers/smtp-servers.component";
import { NewTokengroupComponent } from "@components/external-services/tokengroups/new-tokengroup/new-tokengroup.component";
import { TokengroupsComponent } from "@components/external-services/tokengroups/tokengroups.component";
import { MachineResolverDetailsComponent } from "@components/machine-resolver/machine-resolver-details/machine-resolver-details.component";
import { MachineResolverComponent } from "@components/machine-resolver/machine-resolver.component";
import { NewsComponent } from "@components/news/news.component";
import { PolicyEditPageComponent } from "@components/policies/policy-edit-page/policy-edit-page.component";
import { UISettingsComponent } from "@components/configuration/ui-settings/ui-settings.component";
import { PoliciesTableComponent } from "@components/policies/policies-table/policies-table.component";
import { ConditionalAccessComponent } from "@components/conditional-access/conditional-access.component";
import { ConditionalAccessEditPageComponent } from "@components/conditional-access/conditional-access-edit-page/conditional-access-edit-page.component";
import { ChallengesTableComponent } from "@components/token/challenges-table/challenges-table.component";
import { ContainerCreateComponent } from "@components/container/container-create/container-create.component";
import { ContainerDetailsComponent } from "@components/container/container-details/container-details.component";
import { ContainerTableComponent } from "@components/container/container-table/container-table.component";
import { ContainerTemplatesComponent } from "@components/container/container-templates/container-templates.component";
import { ContainerTemplateEditPageComponent } from "@components/container/container-templates/container-template-edit-page/container-template-edit-page.component";
import { TokenApplicationsComponent } from "@components/token/token-applications/token-applications.component";
import { TokenDetailsComponent } from "@components/token/token-details/token-details.component";
import { TokenEnrollmentComponent } from "@components/token/token-enrollment/token-enrollment.component";
import { TokenFindSerialComponent } from "@components/token/token-find-serial/token-find-serial.component";
import { TokenImportComponent } from "@components/token/token-import/token-import.component";
import { TokenTableComponent } from "@components/token/token-table/token-table.component";
import { UserCreateComponent } from "@components/user/user-create/user-create.component";
import { RealmTableComponent } from "@components/user/realm-table/realm-table.component";
import { UserDetailsComponent } from "@components/user/user-details/user-details.component";
import { UserNewResolverComponent } from "@components/user/user-new-resolver/user-new-resolver.component";
import { UserResolversComponent } from "@components/user/user-resolver/user-resolver.component";
import { UserTableComponent } from "@components/user/user-table/user-table.component";

export const routes: Routes = [
  {
    path: "dashboard",
    title: PAGE_NAMES.dashboard,
    component: DashboardComponent,
    canActivate: [dashboardGuard],
    canDeactivate: [pendingChangesGuard]
  },
  {
    path: "tokens",
    children: [
      { path: "", title: PAGE_NAMES.tokens, component: TokenTableComponent },
      {
        path: "enrollment",
        title: PAGE_NAMES.enrollToken,
        component: TokenEnrollmentComponent,
        canDeactivate: [pendingChangesGuard]
      },
      { path: "challenges", title: PAGE_NAMES.challenges, component: ChallengesTableComponent },
      { path: "applications", title: PAGE_NAMES.applications, component: TokenApplicationsComponent },
      { path: "get-serial", title: PAGE_NAMES.getSerial, component: TokenFindSerialComponent },
      {
        path: "details/:serial",
        title: detailsTitle(PAGE_NAMES.tokens),
        component: TokenDetailsComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "import",
        title: PAGE_NAMES.importTokens,
        component: TokenImportComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "containers",
    children: [
      { path: "", title: PAGE_NAMES.containers, component: ContainerTableComponent },
      {
        path: "create",
        title: newTitle(PAGE_NAMES.containers),
        component: ContainerCreateComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "details/:serial",
        title: detailsTitle(PAGE_NAMES.containers),
        component: ContainerDetailsComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "templates",
        children: [
          { path: "", title: PAGE_NAMES.containerTemplates, component: ContainerTemplatesComponent },
          {
            path: "create",
            title: newTitle(PAGE_NAMES.containerTemplates),
            component: ContainerTemplateEditPageComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.containerTemplates),
            component: ContainerTemplateEditPageComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      }
    ]
  },
  {
    path: "users",
    children: [
      { path: "", title: PAGE_NAMES.users, component: UserTableComponent },
      {
        path: "new",
        title: newTitle(PAGE_NAMES.users),
        component: UserCreateComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "details/:username",
        title: detailsTitle(PAGE_NAMES.users),
        component: UserDetailsComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "realms",
        title: PAGE_NAMES.realms,
        component: RealmTableComponent,
        canDeactivate: [pendingChangesGuard]
      },
      { path: "resolvers", title: PAGE_NAMES.resolvers, component: UserResolversComponent },
      {
        path: "resolvers/new",
        title: newTitle(PAGE_NAMES.resolvers),
        component: UserNewResolverComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "resolvers/details/:name",
        title: detailsTitle(PAGE_NAMES.resolvers),
        component: UserNewResolverComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "policies",
    children: [
      { path: "", title: PAGE_NAMES.policies, component: PoliciesTableComponent },
      {
        path: "new",
        title: newTitle(PAGE_NAMES.policies),
        component: PolicyEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "details/:name",
        title: detailsTitle(PAGE_NAMES.policies),
        component: PolicyEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "conditional-access",
        title: PAGE_NAMES.conditionalAccess,
        component: ConditionalAccessComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "conditional-access/new",
        title: newTitle(PAGE_NAMES.conditionalAccess),
        component: ConditionalAccessEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "conditional-access/details/:id",
        title: detailsTitle(PAGE_NAMES.conditionalAccess),
        component: ConditionalAccessEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "api-clients",
        children: [
          { path: "", title: PAGE_NAMES.apiClients, component: ApiClientsComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.apiClients),
            component: ApiClientEditComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:id",
            title: detailsTitle(PAGE_NAMES.apiClients),
            component: ApiClientEditComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      }
    ]
  },
  {
    path: "events",
    children: [
      { path: "", title: PAGE_NAMES.events, component: EventComponent, canDeactivate: [pendingChangesGuard] },
      {
        path: "new",
        title: newTitle(PAGE_NAMES.events),
        component: EventEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "details/:id",
        title: detailsTitle(PAGE_NAMES.events),
        component: EventEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "configuration",
    children: [
      // { path: "", component: SystemComponent },
      {
        path: "machine_resolver",
        children: [
          { path: "", title: PAGE_NAMES.machineResolvers, component: MachineResolverComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.machineResolvers),
            component: MachineResolverDetailsComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.machineResolvers),
            component: MachineResolverDetailsComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "machines",
        children: [
          { path: "", title: PAGE_NAMES.machines, component: MachinesComponent },
          {
            path: "details/:id",
            title: detailsTitle(PAGE_NAMES.machines),
            component: MachineDetailsComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "periodic-tasks",
        children: [
          { path: "", title: PAGE_NAMES.periodicTasks, component: PeriodicTaskComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.periodicTasks),
            component: PeriodicTaskEditComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.periodicTasks),
            component: PeriodicTaskEditComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      { path: "subscription", title: PAGE_NAMES.subscription, component: SubscriptionComponent },
      {
        path: "system",
        title: PAGE_NAMES.system,
        component: SystemConfigComponent,
        canDeactivate: [pendingChangesGuard]
      },
      { path: "ui-settings", title: PAGE_NAMES.settings, component: UISettingsComponent },
      {
        path: "tokens",
        title: PAGE_NAMES.tokenTypes,
        component: TokenTypeConfigComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "logs",
    children: [
      { path: "", pathMatch: "full", redirectTo: logsLandingRedirect },
      { path: "audit", title: PAGE_NAMES.audit, component: AuditComponent },
      { path: "authentication-log", title: PAGE_NAMES.authenticationLog, component: AuthenticationLog },
      { path: "clients", title: PAGE_NAMES.clients, component: ClientsComponent },
      { path: "locked-users", title: PAGE_NAMES.lockedUsers, component: LockedUsersComponent },
      { path: "blocklist", title: PAGE_NAMES.blocklist, component: BlocklistComponent }
    ]
  },
  {
    path: "news",
    title: PAGE_NAMES.news,
    component: NewsComponent
  },
  {
    path: "external-services",
    children: [
      {
        path: "smtp",
        children: [
          { path: "", title: PAGE_NAMES.smtp, component: SmtpServersComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.smtp),
            component: NewSmtpServerComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:identifier",
            title: detailsTitle(PAGE_NAMES.smtp),
            component: NewSmtpServerComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "radius",
        children: [
          { path: "", title: PAGE_NAMES.radius, component: RadiusServersComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.radius),
            component: NewRadiusServerComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:identifier",
            title: detailsTitle(PAGE_NAMES.radius),
            component: NewRadiusServerComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "sms",
        children: [
          { path: "", title: PAGE_NAMES.sms, component: SmsGatewaysComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.sms),
            component: NewSmsGatewayComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.sms),
            component: NewSmsGatewayComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "privacyidea",
        children: [
          { path: "", title: PAGE_NAMES.privacyideaServers, component: PrivacyideaServersComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.privacyideaServers),
            component: NewPrivacyideaServerComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:identifier",
            title: detailsTitle(PAGE_NAMES.privacyideaServers),
            component: NewPrivacyideaServerComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "ca-connectors",
        children: [
          { path: "", title: PAGE_NAMES.caConnectors, component: CaConnectorsComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.caConnectors),
            component: NewCaConnectorComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.caConnectors),
            component: NewCaConnectorComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "tokengroups",
        children: [
          { path: "", title: PAGE_NAMES.tokengroups, component: TokengroupsComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.tokengroups),
            component: NewTokengroupComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.tokengroups),
            component: NewTokengroupComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "service-ids",
        children: [
          { path: "", title: PAGE_NAMES.serviceIds, component: ServiceIdsComponent },
          {
            path: "new",
            title: newTitle(PAGE_NAMES.serviceIds),
            component: NewServiceIdComponent,
            canDeactivate: [pendingChangesGuard]
          },
          {
            path: "details/:name",
            title: detailsTitle(PAGE_NAMES.serviceIds),
            component: NewServiceIdComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      }
    ]
  }
];
