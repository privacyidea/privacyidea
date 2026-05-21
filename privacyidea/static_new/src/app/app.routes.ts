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
import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { LayoutComponent } from "./components/layout/layout.component";
import { LoginComponent } from "./components/login/login.component";
import { adminMatch, AuthGuard, selfServiceMatch } from "./guards/auth.guard";
import { ApplicationService } from "@services/application/application.service";
import { AuditService } from "@services/audit/audit.service";
import { CaConnectorService } from "@services/ca-connector/ca-connector.service";
import { ChallengesService } from "@services/token/challenges/challenges.service";
import { ClientsService } from "@services/clients/clients.service";
import { ContainerService } from "@services/container/container.service";
import { ContainerTemplateService } from "@services/container-template/container-template.service";
import { ContentService } from "@services/content/content.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { EventService } from "@services/event/event.service";
import { MachineResolverService } from "@services/machine-resolver/machine-resolver.service";
import { MachineService } from "@services/machine/machine.service";
import { PendingChangesService } from "@services/pending-changes/pending-changes.service";
import { PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { PolicyService } from "@services/policies/policies.service";
import { PrivacyideaServerService } from "@services/privacyidea-server/privacyidea-server.service";
import { RadiusServerService } from "@services/radius-server/radius-server.service";
import { RealmService } from "@services/realm/realm.service";
import { ResolverService } from "@services/resolver/resolver.service";
import { ServiceIdService } from "@services/service-id/service-id.service";
import { SmsGatewayService } from "@services/sms-gateway/sms-gateway.service";
import { SmtpService } from "@services/smtp/smtp.service";
import { SubscriptionExpiryService } from "@services/subscription/subscription-expiry.service";
import { SubscriptionService } from "@services/subscription/subscription.service";
import { SystemService } from "@services/system/system.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokengroupService } from "@services/tokengroup/tokengroup.service";
import { TokenService } from "@services/token/token.service";
import { UiPolicyService } from "@services/ui-policy/ui-policy.service";
import { UserService } from "@services/user/user.service";


export const routes: Routes = [
  { path: "login", component: LoginComponent },
  { path: "", redirectTo: "login", pathMatch: "full" },
  {
    path: "",
    component: LayoutComponent,
    canActivateChild: [AuthGuard],
    providers: [
      ApplicationService,
      AuditService,
      CaConnectorService,
      ChallengesService,
      ClientsService,
      ContainerService,
      ContainerTemplateService,
      ContentService,
      DocumentationService,
      EventService,
      MachineResolverService,
      MachineService,
      PendingChangesService,
      PeriodicTaskService,
      PolicyService,
      PrivacyideaServerService,
      RadiusServerService,
      RealmService,
      ResolverService,
      ServiceIdService,
      SmsGatewayService,
      SmtpService,
      SubscriptionExpiryService,
      SubscriptionService,
      SystemService,
      TableUtilsService,
      TokengroupService,
      TokenService,
      UiPolicyService,
      UserService,
    ],
    children: [
      {
        path: "",
        canMatch: [adminMatch],
        loadChildren: () => import("./admin.routes").then((m) => m.routes)
      },
      {
        path: "",
        canMatch: [selfServiceMatch],
        loadChildren: () => import("./self-service.routes").then((m) => m.routes)
      }
    ]
  },
  { path: "**", redirectTo: "login" }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: false })],
  exports: [RouterModule]
})
export class AppRoutingModule {}
