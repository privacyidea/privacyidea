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
import { NgClass, NgOptimizedImage } from "@angular/common";
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle
} from "@angular/material/expansion";
import { MatInput, MatLabel, MatSuffix } from "@angular/material/input";
import { MatList, MatListItem } from "@angular/material/list";
import { ROUTE_PATHS } from "../../../route_paths";
import { MatAnchor, MatButton } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
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
    MatAccordion,
    MatButton,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatFormField,
    MatIconModule,
    MatInput,
    MatLabel,
    MatList,
    MatListItem,
    MatSuffix,
    NgOptimizedImage,
    MatIcon,
    RouterLink,
    NgClass,
    MatAnchor,
    MatTooltipModule,
    FormsModule,
    UserUtilsPanelComponent
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

  onSingleHeaderClick(event: MouseEvent, route_path: string): void {
    event.preventDefault();
    (event as any).stopImmediatePropagation?.();
    event.stopPropagation();

    this.router.navigate([route_path]);
  }
}
