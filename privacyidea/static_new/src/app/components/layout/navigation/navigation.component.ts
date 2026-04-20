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
import { Component, computed, inject, signal } from "@angular/core";
import { NgClass, NgOptimizedImage } from "@angular/common";
import { MatList, MatListItem } from "@angular/material/list";
import { ROUTE_PATHS } from "../../../route_paths";
import { MatAnchor, MatButton } from "@angular/material/button";
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
import { MatIconButton } from "@angular/material/button";
import { MatDrawer, MatDrawerContainer, MatDrawerContent } from "@angular/material/sidenav";

export type NavSection = 'token' | 'container' | 'users' | 'policies' | 'events' | 'audit' | 'external-services' | 'configuration' | null;

@Component({
  selector: "app-navigation",
  imports: [
    MatButton,
    MatIconModule,
    MatList,
    MatListItem,
    NgOptimizedImage,
    MatIcon,
    RouterLink,
    NgClass,
    MatAnchor,
    MatTooltipModule,
    FormsModule,
    UserUtilsPanelComponent,
    MatIconButton,
    MatDrawer,
    MatDrawerContainer,
    MatDrawerContent
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

  activeSection = signal<NavSection>(null);

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

  toggleSection(section: NavSection, defaultRoute?: string): void {
    if (this.activeSection() === section) {
      this.activeSection.set(null);
    } else {
      this.activeSection.set(section);
      if (defaultRoute) {
        this.router.navigate([defaultRoute]);
      }
    }
  }

  navigateSingle(route: string): void {
    this.activeSection.set(null);
    this.router.navigate([route]);
  }

  isSubDrawerOpen(): boolean {
    return this.activeSection() !== null;
  }
}
