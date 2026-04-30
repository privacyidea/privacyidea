/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ChallengesTableComponent } from "./components/token/challenges-table/challenges-table.component";
import { ContainerCreateComponent } from "./components/token/container-create/container-create.component";
import { ContainerDetailsComponent } from "./components/token/container-details/container-details.component";
import { ContainerTableComponent } from "./components/token/container-table/container-table.component";
import { TokenApplicationsComponent } from "./components/token/token-applications/token-applications.component";
import { TokenDetailsComponent } from "./components/token/token-details/token-details.component";
import { TokenEnrollmentComponent } from "./components/token/token-enrollment/token-enrollment.component";
import { TokenFindSerialComponent } from "@components/token/token-find-serial/token-find-serial.component";
import { TokenTableComponent } from "./components/token/token-table/token-table.component";
import { UserDetailsComponent } from "./components/user/user-details/user-details.component";
import { UserTableComponent } from "./components/user/user-table/user-table.component";
import { AuditComponent } from "./components/audit/audit.component";
import { TokenImportComponent } from "./components/token/token-import/token-import.component";
import { RealmTableComponent } from "./components/user/realm-table/realm-table.component";
import { ClientsComponent } from "./components/audit/clients/clients.component";
import { MachineResolverComponent } from "./components/machine-resolver/machine-resolver.component";
import { PeriodicTaskComponent } from "./components/configuration/periodic-task/periodic-task.component";
import { MachinesComponent } from "./components/configuration/machines/machines.component";
import { MachineDetailsDialogComponent } from "./components/configuration/machines/machine-details-dialog/machine-details-dialog.component";
import { SmtpServersComponent } from "./components/external-services/smtp-servers/smtp-servers.component";
import { NewSmtpServerComponent } from "./components/external-services/smtp-servers/new-smtp-server/new-smtp-server.component";
import { RadiusServersComponent } from "./components/external-services/radius-servers/radius-servers.component";
import { NewRadiusServerComponent } from "./components/external-services/radius-servers/new-radius-server/new-radius-server.component";
import { SmsGatewaysComponent } from "./components/external-services/sms-gateways/sms-gateways.component";
import { NewSmsGatewayComponent } from "./components/external-services/sms-gateways/new-sms-gateway/new-sms-gateway.component";
import { PrivacyideaServersComponent } from "./components/external-services/privacyidea-servers/privacyidea-servers.component";
import { NewPrivacyideaServerComponent } from "./components/external-services/privacyidea-servers/new-privacyidea-server/new-privacyidea-server.component";
import { CaConnectorsComponent } from "./components/external-services/ca-connectors/ca-connectors.component";
import { NewCaConnectorComponent } from "./components/external-services/ca-connectors/new-ca-connector/new-ca-connector.component";
import { TokengroupsComponent } from "./components/external-services/tokengroups/tokengroups.component";
import { NewTokengroupComponent } from "./components/external-services/tokengroups/new-tokengroup/new-tokengroup.component";
import { ServiceIdsComponent } from "./components/external-services/service-ids/service-ids.component";
import { NewServiceIdComponent } from "./components/external-services/service-ids/new-service-id/new-service-id.component";
import { UserResolversComponent } from "./components/user/user-resolver/user-resolver.component";
import { pendingChangesGuard } from "./guards/pending-changes.guard";
import { PoliciesTableComponent } from "./components/policies/policies-table/policies-table.component";
import { SubscriptionComponent } from "./components/configuration/subscription/subscription.component";
import { EventComponent } from "./components/event/event.component";
import { EventPanelComponent } from "./components/event/event-panel/event-panel.component";
import { SystemConfigComponent } from "./components/configuration/system/system-config.component";
import { TokenTypeConfigComponent } from "./components/configuration/token-type-config/token-type-config.component";
import { ContainerTemplatesComponent } from "@components/token/container-templates/container-templates.component";
import { UserNewResolverComponent } from "@components/user/user-new-resolver/user-new-resolver.component";
import { EditPolicyDialogComponent } from "./components/policies/dialogs/edit-policy-dialog/edit-policy-dialog.component";

export const routes: Routes = [
  {
    path: "tokens",
    children: [
      { path: "", component: TokenTableComponent },
      { path: "enrollment", component: TokenEnrollmentComponent },
      { path: "challenges", component: ChallengesTableComponent },
      { path: "applications", component: TokenApplicationsComponent },
      { path: "get-serial", component: TokenFindSerialComponent },
      {
        path: "containers",
        children: [
          { path: "", component: ContainerTableComponent },
          { path: "create", component: ContainerCreateComponent },
          { path: "details/:serial", component: ContainerDetailsComponent },
          { path: "templates", component: ContainerTemplatesComponent, canDeactivate: [pendingChangesGuard] }
        ]
      },
      { path: "details/:serial", component: TokenDetailsComponent },
      { path: "import", component: TokenImportComponent }
    ]
  },
  {
    path: "users",
    children: [
      { path: "", component: UserTableComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:username", component: UserDetailsComponent, canDeactivate: [pendingChangesGuard] },
      { path: "realms", component: RealmTableComponent },
      { path: "resolvers", component: UserResolversComponent },
      { path: "resolvers/new", component: UserNewResolverComponent, canDeactivate: [pendingChangesGuard] },
      { path: "resolvers/details/:name", component: UserNewResolverComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "policies",
    children: [
      { path: "", component: PoliciesTableComponent },
      { path: "new", component: EditPolicyDialogComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:name", component: EditPolicyDialogComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "events",
    children: [
      { path: "", component: EventComponent, canDeactivate: [pendingChangesGuard] },
      { path: "new", component: EventPanelComponent, canDeactivate: [pendingChangesGuard] },
      { path: "details/:id", component: EventPanelComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "configuration",
    children: [
      // { path: "", component: SystemComponent },
      { path: "machine_resolver", component: MachineResolverComponent },
      {
        path: "machines",
        children: [
          { path: "", component: MachinesComponent },
          { path: "details/:id", component: MachineDetailsDialogComponent }
        ]
      },
      { path: "periodic-tasks", component: PeriodicTaskComponent },
      { path: "subscription", component: SubscriptionComponent },
      { path: "system", component: SystemConfigComponent },
      { path: "tokens", component: TokenTypeConfigComponent, canDeactivate: [pendingChangesGuard] }
    ]
  },
  {
    path: "audit",
    children: [
      { path: "", component: AuditComponent },
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
