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
import { TokenGetSerialComponent } from "./components/token/token-get-serial/token-get-serial.component";
import { TokenTableComponent } from "./components/token/token-table/token-table.component";
import { UserDetailsComponent } from "./components/user/user-details/user-details.component";
import { UserTableComponent } from "./components/user/user-table/user-table.component";
import { AuditComponent } from "./components/audit/audit.component";
import { PoliciesComponent } from "./components/policies/policies.component";
import { TokenImportComponent } from "./components/token/token-import/token-import.component";
import { ContainerTemplatesComponent } from "./components/token/container-templates/container-templates.component";
import { RealmTableComponent } from "./components/user/realm-table/realm-table.component";
import { ClientsComponent } from "./components/audit/clients/clients.component";
import { MachineResolverComponent } from "./components/machine-resolver/machine-resolver.component";
import { PeriodicTaskComponent } from "./components/configuration/periodic-task/periodic-task.component";
import { UserResolversComponent } from "./components/user/user-sources/user-resolvers.component";
import { UserNewResolverComponent } from "./components/user/user-new-resolver/user-new-resolver.component";

export const routes: Routes = [
  {
    path: "tokens",
    children: [
      { path: "", component: TokenTableComponent },
      { path: "enrollment", component: TokenEnrollmentComponent },
      { path: "challenges", component: ChallengesTableComponent },
      { path: "applications", component: TokenApplicationsComponent },
      { path: "get-serial", component: TokenGetSerialComponent },
      {
        path: "containers",
        children: [
          { path: "", component: ContainerTableComponent },
          { path: "create", component: ContainerCreateComponent },
          { path: "details/:serial", component: ContainerDetailsComponent },
          { path: "templates", component: ContainerTemplatesComponent }
        ]
      },
      { path: "details/:serial", component: TokenDetailsComponent },
      { path: "import", component: TokenImportComponent }
    ]
  },
  {
    path: "users",
    children: [
      { path: "", component: UserTableComponent },
      { path: "details/:username", component: UserDetailsComponent },
      { path: "realms", component: RealmTableComponent },
      { path: "resolvers", component: UserResolversComponent },
      { path: "new-resolver", component: UserNewResolverComponent },
      { path: "edit-resolver/:name", component: UserNewResolverComponent }
    ]
  },
  {
    path: "policies",
    children: [{ path: "", component: PoliciesComponent }]
  },
  {
    path: "configuration",
    children: [{ path: "machine_resolver", component: MachineResolverComponent }]
  },
  {
    path: "audit",
    children: [
      { path: "", component: AuditComponent },
      { path: "clients", component: ClientsComponent }
    ]
  },
  {
    path: "configuration",
    children: [{ path: "periodic-tasks", component: PeriodicTaskComponent }]
  }
];
