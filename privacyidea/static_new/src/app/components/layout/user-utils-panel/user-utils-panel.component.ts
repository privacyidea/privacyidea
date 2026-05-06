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

import { DatePipe, NgClass } from "@angular/common";
import { Component, HostListener, computed, inject, signal } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { from } from "rxjs";
import { SaveAndExitDialogComponent } from "src/app/components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { ThemeSwitcherComponent } from "src/app/components/shared/theme-switcher/theme-switcher.component";
import { ROUTE_PATHS } from "src/app/route_paths";
import { AuditService, AuditServiceInterface } from "src/app/services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "src/app/services/auth/auth.service";
import { CaConnectorService, CaConnectorServiceInterface } from "src/app/services/ca-connector/ca-connector.service";
import { ClientsService, ClientsServiceInterface } from "src/app/services/clients/clients.service";
import {
  ContainerTemplateService,
  ContainerTemplateServiceInterface
} from "src/app/services/container-template/container-template.service";
import { ContainerService, ContainerServiceInterface } from "src/app/services/container/container.service";
import { ContentService, ContentServiceInterface } from "src/app/services/content/content.service";
import { DialogService, DialogServiceInterface } from "src/app/services/dialog/dialog.service";
import {
  DocumentationService,
  DocumentationServiceInterface
} from "src/app/services/documentation/documentation.service";
import { EventService, EventServiceInterface } from "src/app/services/event/event.service";
import {
  MachineResolverService,
  MachineResolverServiceInterface
} from "src/app/services/machine-resolver/machine-resolver.service";
import { MachineService, MachineServiceInterface } from "src/app/services/machine/machine.service";
import { NotificationService, NotificationServiceInterface } from "src/app/services/notification/notification.service";
import {
  PendingChangesService,
  PendingChangesServiceInterface
} from "src/app/services/pending-changes/pending-changes.service";
import { PeriodicTaskService } from "src/app/services/periodic-task/periodic-task.service";
import { PolicyService, PolicyServiceInterface } from "src/app/services/policies/policies.service";
import {
  PrivacyideaServerService,
  PrivacyideaServerServiceInterface
} from "src/app/services/privacyidea-server/privacyidea-server.service";
import {
  RadiusServerService,
  RadiusServerServiceInterface
} from "src/app/services/radius-server/radius-server.service";
import { RealmService, RealmServiceInterface } from "src/app/services/realm/realm.service";
import { ResolverService, ResolverServiceInterface } from "src/app/services/resolver/resolver.service";
import { ServiceIdService, ServiceIdServiceInterface } from "src/app/services/service-id/service-id.service";
import {
  SessionTimerService,
  SessionTimerServiceInterface
} from "src/app/services/session-timer/session-timer.service";
import { SmsGatewayService, SmsGatewayServiceInterface } from "src/app/services/sms-gateway/sms-gateway.service";
import { SmtpService, SmtpServiceInterface } from "src/app/services/smtp/smtp.service";
import { SubscriptionService } from "src/app/services/subscription/subscription.service";
import { SystemService, SystemServiceInterface } from "src/app/services/system/system.service";
import { ChallengesService, ChallengesServiceInterface } from "src/app/services/token/challenges/challenges.service";
import { TokenService, TokenServiceInterface } from "src/app/services/token/token.service";
import { TokengroupService, TokengroupServiceInterface } from "src/app/services/tokengroup/tokengroup.service";
import { UserService, UserServiceInterface } from "src/app/services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "src/app/services/version/version.service";

@Component({
  selector: "app-user-utils-panel",
  imports: [MatIcon, MatIconButton, MatTooltip, ThemeSwitcherComponent, NgClass, DatePipe],
  templateUrl: "./user-utils-panel.component.html",
  styleUrl: "./user-utils-panel.component.scss"
})
export class UserUtilsPanelComponent {
  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly containerService: ContainerServiceInterface = inject(ContainerService);
  private readonly challengeService: ChallengesServiceInterface = inject(ChallengesService);
  private readonly machineService: MachineServiceInterface = inject(MachineService);
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly documentationService: DocumentationServiceInterface = inject(DocumentationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly clientsService: ClientsServiceInterface = inject(ClientsService);
  private readonly policyService: PolicyServiceInterface = inject(PolicyService);
  private readonly subscriptionService = inject(SubscriptionService);
  private readonly machineResolverService: MachineResolverServiceInterface = inject(MachineResolverService);
  private readonly containerTemplateService: ContainerTemplateServiceInterface = inject(ContainerTemplateService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  private readonly resolverService: ResolverServiceInterface = inject(ResolverService);
  private readonly smtpService: SmtpServiceInterface = inject(SmtpService);
  private readonly radiusService: RadiusServerServiceInterface = inject(RadiusServerService);
  private readonly smsGatewayService: SmsGatewayServiceInterface = inject(SmsGatewayService);
  private readonly privacyideaService: PrivacyideaServerServiceInterface = inject(PrivacyideaServerService);
  private readonly tokengroupService: TokengroupServiceInterface = inject(TokengroupService);
  private readonly caConnectorService: CaConnectorServiceInterface = inject(CaConnectorService);
  private readonly serviceIdService: ServiceIdServiceInterface = inject(ServiceIdService);
  protected readonly periodicTaskService = inject(PeriodicTaskService);
  protected readonly eventService: EventServiceInterface = inject(EventService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  private readonly pendingChangesService: PendingChangesServiceInterface = inject(PendingChangesService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  protected readonly router: Router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  isLargeScreen = signal(window.innerWidth > 1630);

  @HostListener("window:resize")
  onResize() {
    this.isLargeScreen.set(window.innerWidth > 1630);
  }

  profileText = computed(() => {
    let profileText = this.authService.username();
    if (this.authService.realm()) {
      profileText += " @ " + this.authService.realm();
    }
    if (this.authService.role()) {
      profileText += " (" + this.authService.role() + ")";
    }
    return profileText;
  });

  sessionTimeFormat = computed(() => {
    // Use non-breaking half space (U+202F) between number and unit
    if (this.sessionTimerService.remainingTime()! < 599999) {
      // less than 10 minutes remaining, show minutes and seconds
      return "m:ss";
    } else if (this.sessionTimerService.remainingTime()! < 3600000) {
      // less than an hour, show only minutes
      return "m'\u202Fmin'";
    }
    // show hours and minutes
    return "H'\u202Fh' mm'\u202Fmin'";
  });

  localNode = computed(() => this.authService.showNode());

  profileTooltip = computed(() => {
    let tooltip = this.profileText();
    if (this.localNode()) {
      tooltip += " – " + this.localNode();
    }
    return tooltip;
  });

  logout(): void {
    if (this.pendingChangesService.hasChanges) {
      this.dialogService
        .openDialog({
          component: SaveAndExitDialogComponent,
          data: {
            saveExitDisabled: !this.pendingChangesService.validChanges,
            allowSaveExit: true
          }
        })
        .afterClosed()
        .subscribe((result) => {
          if (result === "discard") {
            this.pendingChangesService.clearAllRegistrations();
            this.authService.logout();
          } else if (result === "save-exit") {
            const saveResult = this.pendingChangesService.save();
            from(Promise.resolve(saveResult)).subscribe((success) => {
              if (success) {
                this.pendingChangesService.clearAllRegistrations();
                this.authService.logout();
              }
            });
          }
        });
    } else {
      this.authService.logout();
    }
  }

  refreshPage() {
    if (this.contentService.onTokenDetails()) {
      this.tokenService.tokenDetailResource.reload();
      this.containerService.containerResource.reload();
      return;
    } else if (this.contentService.onTokensContainersDetails()) {
      this.containerService.containerDetailsResource.reload();
      this.tokenService.tokenResource.reload();
      this.userService.usersResource.reload();
      return;
    } else if (this.contentService.onUserDetails()) {
      this.userService.usersResource.reload();
      this.tokenService.tokenResource.reload();
      this.tokenService.userTokenResource.reload();
      this.containerService.containerResource.reload();
      return;
    }

    switch (this.contentService.routeUrl()) {
      case ROUTE_PATHS.TOKENS:
        this.tokenService.tokenResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_CONTAINERS:
        this.containerService.containerResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_CHALLENGES:
        this.challengeService.challengesResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_APPLICATIONS:
        this.machineService.tokenApplicationResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_ENROLLMENT:
        this.containerService.containerResource.reload();
        this.userService.usersResource.reload();
        break;
      case ROUTE_PATHS.AUDIT:
        this.auditService.auditResource.reload();
        break;
      case ROUTE_PATHS.CLIENTS:
        this.clientsService.clientsResource.reload();
        break;
      case ROUTE_PATHS.USERS:
        this.userService.usersResource.reload();
        break;
      case ROUTE_PATHS.USERS_REALMS:
        this.realmService.realmResource.reload();
        this.resolverService.resolversResource.reload();
        break;
      case ROUTE_PATHS.POLICIES:
        this.policyService.allPoliciesResource.reload();
        this.policyService.policyActionResource.reload();
        break;
      case ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS:
        this.periodicTaskService.periodicTasksResource.reload();
        break;
      case ROUTE_PATHS.CONFIGURATION_SYSTEM:
      case ROUTE_PATHS.CONFIGURATION_TOKENTYPES:
        this.systemService.systemConfigResource.reload();
        break;
      case ROUTE_PATHS.CONFIGURATION_MACHINES:
        this.machineService.machinesResource.reload();
        break;
      case ROUTE_PATHS.SUBSCRIPTION:
        this.subscriptionService.reload();
        break;
      case ROUTE_PATHS.USERS_RESOLVERS:
        this.resolverService.resolversResource.reload();
        break;
      case ROUTE_PATHS.MACHINE_RESOLVER:
        this.machineResolverService.machineResolverResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_SMTP:
        this.smtpService.smtpServerResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_RADIUS:
        this.radiusService.radiusServerResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_SMS:
        this.smsGatewayService.smsGatewayResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_PRIVACYIDEA:
        this.privacyideaService.remoteServerResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS:
        this.tokengroupService.tokengroupResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_CA_CONNECTORS:
        this.caConnectorService.caConnectorResource.reload();
        break;
      case ROUTE_PATHS.EXTERNAL_SERVICES_SERVICE_IDS:
        this.serviceIdService.serviceIdResource.reload();
        break;
      case ROUTE_PATHS.EVENTS:
        this.eventService.allEventsResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_GET_SERIAL:
        this.tokenService.tokenTypesResource.reload();
        this.realmService.realmResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_IMPORT:
        this.realmService.realmResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_ASSIGN_TOKEN:
        this.tokenService.tokenSerialResource.reload();
        break;
      case ROUTE_PATHS.TOKENS_WIZARD:
        // No additional resources required for the wizard currently.
        break;
      case ROUTE_PATHS.TOKENS_CONTAINERS_WIZARD:
      case ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES:
      case ROUTE_PATHS.TOKENS_CONTAINERS_CREATE:
        this.containerTemplateService.templatesResource.reload();
        this.containerTemplateService.templateTokenTypesResource.reload();
        break;
    }
  }
}
