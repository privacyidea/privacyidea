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
import { Component, computed, inject, signal, ViewChild, ElementRef, AfterViewInit, OnDestroy, NgZone } from "@angular/core";
import { NgClass, NgOptimizedImage, NgTemplateOutlet } from "@angular/common";
import { MatToolbar } from "@angular/material/toolbar";
import { MatTabsModule } from "@angular/material/tabs";
import { ROUTE_PATHS } from "src/app/route_paths";
import { MatButton, MatIconButton } from "@angular/material/button";
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
import { MatMenuModule } from "@angular/material/menu";
import { OverflowNavDirective } from "./overflow-nav.directive";

export interface NavItem {
  icon: string;
  label: string;
  route?: string;
  section: string;
  iconClass?: string;
  /** For sub-nav: check condition for visibility */
  visible?: () => boolean;
  /** For sub-nav: check if this is the active sub-item */
  isActive?: () => boolean;
  /** For items that are always active (e.g. Details when on details page) */
  alwaysActive?: boolean;
  /** Click handler instead of routerLink */
  action?: () => void;
}

export interface SubNavSection {
  section: string;
  items: NavItem[];
  /** Right-side items (support, docs) */
  rightItems?: NavItem[];
}

@Component({
  selector: "app-navigation",
  imports: [
    MatToolbar,
    MatTabsModule,
    MatButton,
    MatIconButton,
    MatIconModule,
    NgOptimizedImage,
    MatIcon,
    RouterLink,
    NgClass,
    MatTooltipModule,
    FormsModule,
    UserUtilsPanelComponent,
    NgTemplateOutlet,
    MatMenuModule,
    OverflowNavDirective
  ],
  templateUrl: "./navigation.component.html",
  styleUrl: "./navigation.component.scss"
})
export class NavigationComponent implements AfterViewInit, OnDestroy {
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

  @ViewChild("mainNavRef", { static: false }) mainNavRef!: ElementRef<HTMLElement>;

  primaryNavItems: NavItem[] = [
    { icon: "shield", label: $localize`Token`, route: ROUTE_PATHS.TOKENS, section: "token" },
    { icon: "folder", label: $localize`Container`, route: ROUTE_PATHS.TOKENS_CONTAINERS, section: "container" },
    { icon: "supervised_user_circle", label: $localize`Users`, route: ROUTE_PATHS.USERS, section: "users" },
    { icon: "gavel", label: $localize`Policies`, route: ROUTE_PATHS.POLICIES, section: "policies" },
    { icon: "flag", label: $localize`Events`, route: ROUTE_PATHS.EVENTS, section: "events" },
    { icon: "receipt_long", label: $localize`Audit`, route: ROUTE_PATHS.AUDIT, section: "audit" },
    { icon: "hub", label: $localize`External Services`, route: ROUTE_PATHS.EXTERNAL_SERVICES_SMTP, section: "external" },
    { icon: "miscellaneous_services", label: $localize`Configuration`, route: ROUTE_PATHS.CONFIGURATION_SYSTEM, section: "config" },
  ];

  visibleNavCount = signal(this.primaryNavItems.length);
  private resizeObserver: ResizeObserver | null = null;
  private ngZone = inject(NgZone);

  get visibleNavItems(): NavItem[] {
    return this.getFilteredNavItems().slice(0, this.visibleNavCount());
  }

  get overflowNavItems(): NavItem[] {
    return this.getFilteredNavItems().slice(this.visibleNavCount());
  }

  private getFilteredNavItems(): NavItem[] {
    return this.primaryNavItems.filter(item => {
      if (item.section === "policies") return this.authService.actionAllowed("policyread");
      if (item.section === "events") return this.authService.actionAllowed("eventhandling_read");
      return true;
    });
  }

  ngAfterViewInit(): void {
    this.setupOverflowDetection();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  private setupOverflowDetection(): void {
    if (!this.mainNavRef) return;
    const navEl = this.mainNavRef.nativeElement;

    this.resizeObserver = new ResizeObserver(() => {
      this.ngZone.run(() => this.calculateVisibleItems(navEl));
    });
    this.resizeObserver.observe(navEl);

    // Initial calculation
    setTimeout(() => this.calculateVisibleItems(navEl), 0);
  }

  private calculateVisibleItems(navEl: HTMLElement): void {
    const filteredItems = this.getFilteredNavItems();
    const buttons = Array.from(navEl.querySelectorAll<HTMLElement>(".nav-button"));
    if (buttons.length === 0) {
      this.visibleNavCount.set(filteredItems.length);
      return;
    }

    const navWidth = navEl.clientWidth;
    const moreButtonWidth = 56; // approximate width of the "More" button
    const gap = 4;
    let usedWidth = 0;
    let count = 0;

    for (const btn of buttons) {
      // Temporarily make visible to measure
      const wasHidden = btn.classList.contains("overflow-hidden");
      if (wasHidden) {
        btn.style.position = "absolute";
        btn.style.visibility = "hidden";
        btn.style.display = "";
        btn.classList.remove("overflow-hidden");
      }

      const btnWidth = btn.offsetWidth + gap;

      if (wasHidden) {
        btn.classList.add("overflow-hidden");
        btn.style.position = "";
        btn.style.visibility = "";
        btn.style.display = "";
      }

      const remaining = filteredItems.length - count;
      const needsMore = remaining > 1;
      const availableWidth = needsMore ? navWidth - moreButtonWidth : navWidth;

      if (usedWidth + btnWidth <= availableWidth) {
        usedWidth += btnWidth;
        count++;
      } else {
        break;
      }
    }

    // Always show at least 1 item
    this.visibleNavCount.set(Math.max(1, Math.min(count, filteredItems.length)));
  }

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

  isOverflowSectionActive = computed(() => {
    return this.overflowNavItems.some(item => item.section === this.activeSection());
  });

  openSupport(): void {
    window.open("https://netknights.it/support_link_admin", "_blank");
  }

  openExternalLink(url: string): void {
    window.open(url, "_blank");
  }
}
