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

import { inject } from "@angular/core";
import { Routes } from "@angular/router";
import { dashboardGuard } from "@app/guards/dashboard.guard";
import { logsLandingRedirect } from "@app/routing/landing-redirects";
import { pendingChangesGuard } from "@app/guards/pending-changes.guard";
import { AuthService } from "@services/auth/auth.service";
import { AuditComponent } from "@components/logs/audit/audit.component";
import { DashboardComponent } from "@components/dashboard/dashboard.component";
import { ClientsComponent } from "@components/logs/clients/clients.component";
import { AuthenticationLog } from "@components/logs/authentication-log/authentication-log";
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
import { PolicyEditPageComponent } from "@components/policies/policy-edit-page/policy-edit-page.component";
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
    path: "",
    pathMatch: "full",
    redirectTo: () => (inject(AuthService).adminDashboard() ? "dashboard" : "tokens")
  },
  {
    path: "dashboard",
    component: DashboardComponent,
    canActivate: [dashboardGuard],
    canDeactivate: [pendingChangesGuard]
  },
  {
    path: "tokens",
    children: [
      { path: "", component: TokenTableComponent },
      { path: "enrollment", component: TokenEnrollmentComponent, canDeactivate: [pendingChangesGuard] },
      { path: "challenges", component: ChallengesTableComponent },
      { path: "applications", component: TokenApplicationsComponent },
      { path: "get-serial", component: TokenFindSerialComponent },
      { path: "details/:serial", component: TokenDetailsComponent, canDeactivate: [pendingChangesGuard] },
      { path: "import", component: TokenImportComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "containers",
    children: [
      { path: "", component: ContainerTableComponent },
      { path: "create", component: ContainerCreateComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:serial", component: ContainerDetailsComponent, canDeactivate: [pendingChangesGuard] },
      {
        path: "templates",
        children: [
          { path: "", component: ContainerTemplatesComponent },
          { path: "create", component: ContainerTemplateEditPageComponent, canDeactivate: [pendingChangesGuard] },
          {
            path: "details/:name",
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
      { path: "", component: UserTableComponent },
      { path: "new", component: UserCreateComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:username", component: UserDetailsComponent, canDeactivate: [pendingChangesGuard] },
      { path: "realms", component: RealmTableComponent, canDeactivate: [pendingChangesGuard] },
      { path: "resolvers", component: UserResolversComponent },
      { path: "resolvers/new", component: UserNewResolverComponent, canDeactivate: [pendingChangesGuard] },
      { path: "resolvers/details/:name", component: UserNewResolverComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "policies",
    children: [
      { path: "", component: PoliciesTableComponent },
      { path: "new", component: PolicyEditPageComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:name", component: PolicyEditPageComponent, canDeactivate: [pendingChangesGuard] },
      { path: "conditional-access", component: ConditionalAccessComponent },
      {
        path: "conditional-access/new",
        component: ConditionalAccessEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "conditional-access/details/:id",
        component: ConditionalAccessEditPageComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "events",
    children: [
      { path: "", component: EventComponent, canDeactivate: [pendingChangesGuard] },
      { path: "new", component: EventEditPageComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:id", component: EventEditPageComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "configuration",
    children: [
      // { path: "", component: SystemComponent },
      {
        path: "machine_resolver",
        children: [
          { path: "", component: MachineResolverComponent },
          { path: "new", component: MachineResolverDetailsComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: MachineResolverDetailsComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "machines",
        children: [
          { path: "", component: MachinesComponent },
          { path: "details/:id", component: MachineDetailsComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "periodic-tasks",
        children: [
          { path: "", component: PeriodicTaskComponent },
          { path: "new", component: PeriodicTaskEditComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: PeriodicTaskEditComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      { path: "subscription", component: SubscriptionComponent },
      { path: "system", component: SystemConfigComponent, canDeactivate: [pendingChangesGuard] },
      { path: "tokens", component: TokenTypeConfigComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "logs",
    children: [
      { path: "", pathMatch: "full", redirectTo: logsLandingRedirect },
      { path: "audit", component: AuditComponent },
      { path: "authentication-log", component: AuthenticationLog },
      { path: "clients", component: ClientsComponent }
    ]
  },
  {
    path: "external-services",
    children: [
      {
        path: "smtp",
        children: [
          { path: "", component: SmtpServersComponent },
          { path: "new", component: NewSmtpServerComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:identifier", component: NewSmtpServerComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "radius",
        children: [
          { path: "", component: RadiusServersComponent },
          { path: "new", component: NewRadiusServerComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:identifier", component: NewRadiusServerComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "sms",
        children: [
          { path: "", component: SmsGatewaysComponent },
          { path: "new", component: NewSmsGatewayComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: NewSmsGatewayComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "privacyidea",
        children: [
          { path: "", component: PrivacyideaServersComponent },
          { path: "new", component: NewPrivacyideaServerComponent, canDeactivate: [pendingChangesGuard] },
          {
            path: "details/:identifier",
            component: NewPrivacyideaServerComponent,
            canDeactivate: [pendingChangesGuard]
          }
        ]
      },
      {
        path: "ca-connectors",
        children: [
          { path: "", component: CaConnectorsComponent },
          { path: "new", component: NewCaConnectorComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: NewCaConnectorComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "tokengroups",
        children: [
          { path: "", component: TokengroupsComponent },
          { path: "new", component: NewTokengroupComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: NewTokengroupComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      {
        path: "service-ids",
        children: [
          { path: "", component: ServiceIdsComponent },
          { path: "new", component: NewServiceIdComponent, canDeactivate: [pendingChangesGuard] },
          { path: "details/:name", component: NewServiceIdComponent, canDeactivate: [pendingChangesGuard] }
        ]
      }
    ]
  }
];
