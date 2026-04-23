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
import { Component, computed, inject } from "@angular/core";
import { NgClass, NgOptimizedImage, NgTemplateOutlet } from "@angular/common";
import { MatToolbar } from "@angular/material/toolbar";
import { MatTabsModule } from "@angular/material/tabs";
import { ROUTE_PATHS } from "src/app/route_paths";
import { MatButton } from "@angular/material/button";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { Router, RouterLink } from "@angular/router";
import { UserService, UserServiceInterface } from "../../../services/user/user.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { NotificationService, NotificationServiceInterface } from "../../../services/notification/notification.service";
import {
  SessionTimerService,
  SessionTimerServiceInterface
} from "../../../services/session-timer/session-timer.service";
import { VersioningService, VersioningServiceInterface } from "../../../services/version/version.service";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  DocumentationService,
  DocumentationServiceInterface
} from "../../../services/documentation/documentation.service";
import { FormsModule } from "@angular/forms";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { PeriodicTaskService } from "../../../services/periodic-task/periodic-task.service";
import { EventService, EventServiceInterface } from "../../../services/event/event.service";
import { SystemService, SystemServiceInterface } from "../../../services/system/system.service";
import { ConfigService, ConfigServiceInterface } from "../../../services/config/config.service";
import { environment } from "../../../../environments/environment";
import { UserUtilsPanelComponent } from "@components/layout/user-utils-panel/user-utils-panel.component";

@Component({
  selector: "app-navigation",
  imports: [
    MatToolbar,
    MatTabsModule,
    MatButton,
    MatIconModule,
    NgOptimizedImage,
    MatIcon,
    RouterLink,
    NgClass,
    MatTooltipModule,
    FormsModule,
    UserUtilsPanelComponent,
    NgTemplateOutlet
  ],
  templateUrl: "./navigation.component.html",
  styleUrl: "./navigation.component.scss"
})
export class NavigationComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly versioningService: VersioningServiceInterface = inject(VersioningService);
  protected readonly documentationService: DocumentationServiceInterface = inject(DocumentationService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  protected readonly periodicTaskService = inject(PeriodicTaskService);
  protected readonly eventService: EventServiceInterface = inject(EventService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly configService: ConfigServiceInterface = inject(ConfigService);
  protected readonly router: Router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;

  customLogo = computed(() => {
    if (!this.configService.config()?.logo) {
      return null;
    }
    return environment.proxyUrl + "/static/public/" + this.configService.config()?.logo;
  });
  versionText = computed(() => {
    if (this.customLogo()) {
      return $localize`privacyIDEA Version ` + this.versioningService.version();
    }
    return $localize`Version ` + this.versioningService.version();
  });

  activeSection = computed(() => {
    const url = this.contentService.routeUrl();
    if (url.includes("containers")) return "container";
    if (url.startsWith(ROUTE_PATHS.USERS)) return "users";
    if (url.startsWith(ROUTE_PATHS.POLICIES)) return "policies";
    if (url.startsWith(ROUTE_PATHS.EVENTS)) return "events";
    if (url.startsWith(ROUTE_PATHS.AUDIT) || url.startsWith(ROUTE_PATHS.CLIENTS)) return "audit";
    if (url.startsWith("/external-services")) return "external";
    if (url.startsWith("/configuration") || url.startsWith(ROUTE_PATHS.SUBSCRIPTION)
      || url.startsWith(ROUTE_PATHS.MACHINE_RESOLVER)) return "config";
    if (url.startsWith(ROUTE_PATHS.TOKENS)) return "token";
    return "token";
  });

  onSingleHeaderClick(event: MouseEvent, route_path: string): void {
    event.preventDefault();
    (event as any).stopImmediatePropagation?.();
    event.stopPropagation();

    this.router.navigate([route_path]);
  }

  openSupport(): void {
    window.open("https://netknights.it/support_link_admin", "_blank");
  }
}
