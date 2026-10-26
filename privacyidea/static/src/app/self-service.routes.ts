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

import { pendingChangesGuard } from "@app/guards/pending-changes.guard";
import { AuditSelfServiceComponent } from "./components/logs/audit/audit.self-service.component";
import { AssignTokenSelfServiceComponent } from "./components/token/assign-token-self-service/assign-token-self-service.component";
import { ContainerCreateSelfServiceComponent } from "./components/container/container-create/container-create.self-service.component";
import { ContainerCreateWizardComponent } from "./components/container/container-create/container-create.wizard.component";
import { ContainerDetailsComponent } from "./components/container/container-details/container-details.component";
import { ContainerTableSelfServiceComponent } from "./components/container/container-table/container-table.self-service.component";
import { TokenDetailsSelfServiceComponent } from "./components/token/token-details/token-details.self-service.component";
import { TokenEnrollmentSelfServiceComponent } from "./components/token/token-enrollment/token-enrollment.self-service.component";
import { TokenEnrollmentWizardComponent } from "./components/token/token-enrollment/token-enrollment.wizard.component";
import { TokenTableSelfServiceComponent } from "./components/token/token-table/token-table.self-service.component";
import { UserDetailsSelfServiceComponent } from "./components/user/user-details/user-details.self-service.component";
import { UserSelfServiceComponent } from "./components/user/user.self-service.component";
import { AuthenticationLog } from "@components/logs/authentication-log/authentication-log";
import { NewsComponent } from "./components/news/news.component";
import { logsLandingRedirect } from "@app/routing/landing-redirects";

export const routes: Routes = [
  {
    path: "tokens",
    children: [
      {
        path: "",
        pathMatch: "full",
        title: PAGE_NAMES.tokens,
        component: TokenTableSelfServiceComponent
      },
      {
        path: "enrollment",
        title: PAGE_NAMES.enrollToken,
        component: TokenEnrollmentSelfServiceComponent,
        canDeactivate: [pendingChangesGuard]
      },
      { path: "assign-token", title: PAGE_NAMES.assignToken, component: AssignTokenSelfServiceComponent },
      { path: "details/:serial", title: detailsTitle(PAGE_NAMES.tokens), component: TokenDetailsSelfServiceComponent },
      {
        path: "wizard",
        title: PAGE_NAMES.tokenWizard,
        component: TokenEnrollmentWizardComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "containers",
    children: [
      { path: "", title: PAGE_NAMES.containers, component: ContainerTableSelfServiceComponent },
      {
        path: "create",
        title: newTitle(PAGE_NAMES.containers),
        component: ContainerCreateSelfServiceComponent,
        canDeactivate: [pendingChangesGuard]
      },
      {
        path: "details/:serial",
        title: detailsTitle(PAGE_NAMES.containers),
        component: ContainerDetailsComponent
      },
      {
        path: "wizard",
        title: PAGE_NAMES.containerWizard,
        component: ContainerCreateWizardComponent,
        canDeactivate: [pendingChangesGuard]
      }
    ]
  },
  {
    path: "users",
    children: [
      { path: "", pathMatch: "full", title: PAGE_NAMES.users, component: UserSelfServiceComponent },
      { path: "details", title: detailsTitle(PAGE_NAMES.users), component: UserDetailsSelfServiceComponent }
    ]
  },
  {
    path: "logs",
    children: [
      { path: "", pathMatch: "full", redirectTo: logsLandingRedirect },
      { path: "audit", title: PAGE_NAMES.audit, component: AuditSelfServiceComponent },
      { path: "authentication-log", title: PAGE_NAMES.authenticationLog, component: AuthenticationLog }
    ]
  },
  {
    path: "news",
    title: PAGE_NAMES.news,
    component: NewsComponent
  }
];
