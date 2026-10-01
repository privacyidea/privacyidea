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
import { NgClass, NgOptimizedImage, NgTemplateOutlet } from "@angular/common";
import { AfterViewInit, Component, computed, ElementRef, inject, OnDestroy, signal, ViewChild } from "@angular/core";
import { MatButton, MatIconButton } from "@angular/material/button";
import { MatIcon, MatIconModule } from "@angular/material/icon";
import { MatMenuModule } from "@angular/material/menu";
import { MatToolbar } from "@angular/material/toolbar";
import { MatTooltipModule } from "@angular/material/tooltip";
import { Router, RouterLink } from "@angular/router";
import { WidgetPaletteComponent } from "@components/dashboard/widget-palette/widget-palette.component";
import { UserUtilsPanelComponent } from "@components/layout/user-utils-panel/user-utils-panel.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ConfigService, ConfigServiceInterface } from "@services/config/config.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { DocumentationService, DocumentationServiceInterface } from "@services/documentation/documentation.service";
import { EventService, EventServiceInterface } from "@services/event/event.service";
import { NotificationService, NotificationServiceInterface } from "@services/notification/notification.service";
import {
  PendingChangesService,
  PendingChangesServiceInterface
} from "@services/pending-changes/pending-changes.service";
import { PeriodicTaskService } from "@services/periodic-task/periodic-task.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { SessionTimerService, SessionTimerServiceInterface } from "@services/session-timer/session-timer.service";
import { SystemService, SystemServiceInterface } from "@services/system/system.service";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { VersioningService, VersioningServiceInterface } from "@services/version/version.service";
import { UiPreferencesService, UiPreferencesServiceInterface } from "@services/user-settings/ui-preferences.service";

import { ROUTE_PATHS } from "@app/route_paths";
import { LANDING_PAGE_ROUTES } from "@core/landing-page";
import { OverflowNavDirective } from "../../shared/directives/overflow-nav/overflow-nav.directive";

export interface NavItem {
  icon: string;
  label: string;
  route?: string;
  section: string;
  iconClass?: string;
  visible?: () => boolean;
  isActive?: () => boolean;
  alwaysActive?: boolean;
  action?: () => void;
}

export interface SubNavSection {
  section: string;
  items: NavItem[];
  rightItems?: NavItem[];
}

@Component({
  selector: "app-navigation",
  host: { "[class.has-custom-logo]": "customLogo()" },
  imports: [
    MatToolbar,
    MatIconButton,
    MatIconModule,
    NgOptimizedImage,
    MatIcon,
    RouterLink,
    NgClass,
    MatTooltipModule,
    UserUtilsPanelComponent,
    NgTemplateOutlet,
    MatMenuModule,
    OverflowNavDirective,
    MatButton,
    WidgetPaletteComponent
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
  protected readonly uiPreferencesService: UiPreferencesServiceInterface = inject(UiPreferencesService);
  protected readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  protected readonly sessionTimerService: SessionTimerServiceInterface = inject(SessionTimerService);
  protected readonly periodicTaskService = inject(PeriodicTaskService);
  protected readonly eventService: EventServiceInterface = inject(EventService);
  protected readonly systemService: SystemServiceInterface = inject(SystemService);
  protected readonly configService: ConfigServiceInterface = inject(ConfigService);
  protected readonly dashboardLayoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);
  private readonly pendingChanges: PendingChangesServiceInterface = inject(PendingChangesService);
  protected readonly router = inject(Router);
  protected readonly ROUTE_PATHS = ROUTE_PATHS;
  private itemWidths = new Map<string, number>();
  private moreButtonWidth = 110;
  private lastNavWidth = -1;
  // Extra pixels needed to show another item (or all of them) compared with keeping the current count.
  private readonly unfoldHysteresis = 16;
  private resizeObserver: ResizeObserver | null = null;
  @ViewChild("mainNavRef", { static: false }) mainNavRef!: ElementRef<HTMLElement>;
  // .version-text's own margin has to shrink in the same instant this panel hides the
  // username/realm text, not at some independently-tuned width of its own - a plain media query
  // drifted out of sync with this signal's actual breakpoint and made the two rows misalign.
  @ViewChild(UserUtilsPanelComponent) userUtilsPanel!: UserUtilsPanelComponent;
  primaryNavItems: NavItem[] = [
    {
      icon: "dashboard",
      label: $localize`:@@nav.dashboard:Dashboard`,
      route: ROUTE_PATHS.DASHBOARD,
      section: "dashboard"
    },
    { icon: "shield", label: $localize`:@@common.token:Token`, route: ROUTE_PATHS.TOKENS, section: "token" },
    {
      icon: "supervised_user_circle",
      label: $localize`:@@nav.users:Users`,
      route: ROUTE_PATHS.USERS,
      section: "users"
    },
    { icon: "gavel", label: $localize`:@@common.policies:Policies`, route: ROUTE_PATHS.POLICIES, section: "policies" },
    {
      icon: "event_repeat",
      label: $localize`:@@nav.subscription:Subscription`,
      route: ROUTE_PATHS.SUBSCRIPTION,
      section: "subscription"
    },
    // The "logs" umbrella section still carries several sub-pages (see the "logs" secondary toolbar in the
    // template: Audit, Known Clients, Authentication Log, Locked Users, IP Blocklist) that master's own "audit"
    // rename does not know about, so this keeps routing to ROUTE_PATHS.LOGS/section "logs" rather than master's
    // flattened single-page ROUTE_PATHS.AUDIT/"audit".
    { icon: "receipt_long", label: $localize`:@@nav.audit:Audit`, route: ROUTE_PATHS.LOGS, section: "logs" },
    {
      icon: "hub",
      label: $localize`:@@nav.externalServices:External Services`,
      route: ROUTE_PATHS.EXTERNAL_SERVICES_SMTP,
      section: "external_services"
    },
    {
      icon: "miscellaneous_services",
      label: $localize`:@@nav.configuration:Configuration`,
      route: ROUTE_PATHS.CONFIGURATION_SYSTEM,
      section: "config"
    }
  ];
  visibleNavCount = signal(this.primaryNavItems.length);
  landingPage = computed(() => LANDING_PAGE_ROUTES[this.uiPreferencesService.landingPage()]);
  customLogo = computed(() => {
    if (!this.configService.config()?.logo) {
      return null;
    }
    return environment.proxyUrl + "/static/public/" + this.configService.config()?.logo;
  });
  versionPrefix = computed(() => {
    if (this.customLogo()) {
      return "privacyIDEA ";
    }
    return "";
  });
  activeSection = computed(() => {
    const url = this.contentService.routeUrl();
    if (url.startsWith(ROUTE_PATHS.DASHBOARD) || url.startsWith(ROUTE_PATHS.NEWS)) return "dashboard";
    if (url.startsWith(ROUTE_PATHS.USERS)) return "users";
    if (url.startsWith(ROUTE_PATHS.POLICIES) || url.startsWith(ROUTE_PATHS.EVENTS)) return "policies";
    if (url.startsWith(ROUTE_PATHS.SUBSCRIPTION)) return "subscription";
    if (url.startsWith(ROUTE_PATHS.LOGS)) return "logs";
    if (url.startsWith(ROUTE_PATHS.EXTERNAL_SERVICES)) return "external_services";
    if (url.startsWith(ROUTE_PATHS.CONFIGURATION)) return "config";
    if (url.startsWith(ROUTE_PATHS.TOKENS) || url.startsWith(ROUTE_PATHS.CONTAINERS)) return "token";
    return "token";
  });
  isOverflowSectionActive = computed(() => {
    return this.overflowNavItems.some((item) => item.section === this.activeSection());
  });

  get visibleNavItems(): NavItem[] {
    const items = this.getFilteredNavItems();
    const count = this.visibleNavCount();
    const activeSection = this.activeSection();
    const activeIdx = items.findIndex((item) => item.section === activeSection);

    if (activeIdx !== -1 && activeIdx >= count && count > 0) {
      return [...items.slice(0, count - 1), items[activeIdx]];
    }

    return items.slice(0, count);
  }

  get overflowNavItems(): NavItem[] {
    const items = this.getFilteredNavItems();
    const count = this.visibleNavCount();
    const activeSection = this.activeSection();
    const activeIdx = items.findIndex((item) => item.section === activeSection);

    if (activeIdx !== -1 && activeIdx >= count && count > 0) {
      const head = items.slice(0, count - 1);
      const activeItem = items[activeIdx];
      return items.filter((item) => item !== activeItem && !head.includes(item));
    }

    return items.slice(count);
  }

  ngAfterViewInit(): void {
    this.setupOverflowDetection();
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  onSingleHeaderClick(event: MouseEvent, route_path: string): void {
    event.preventDefault();
    event.stopImmediatePropagation?.();
    event.stopPropagation();

    this.router.navigate([route_path]);
  }

  protected enterDashboardEdit(): void {
    this.dashboardLayoutService.beginEdit();
    this.pendingChanges.registerHasChanges(() => this.dashboardLayoutService.hasPendingChanges());
    this.pendingChanges.registerValidChanges(() => true);
    this.pendingChanges.registerSave(() => {
      this.dashboardLayoutService.saveEdit();
      return Promise.resolve(true);
    });
  }

  protected saveDashboard(): void {
    this.dashboardLayoutService.saveEdit();
    this.pendingChanges.clearAllRegistrations();
  }

  protected cancelDashboard(): void {
    this.dashboardLayoutService.cancelEdit();
    this.pendingChanges.clearAllRegistrations();
  }

  openSupport(): void {
    window.open("https://netknights.it/support_link_admin", "_blank");
  }

  openExternalLink(url: string): void {
    window.open(url, "_blank");
  }

  private getFilteredNavItems(): NavItem[] {
    return this.primaryNavItems.filter((item) => {
      switch (item.section) {
        case "dashboard":
          return this.authService.adminDashboard();
        case "token":
          return this.authService.anyTokenActionAllowed() || this.authService.anyContainerActionAllowed();
        case "users":
          return this.authService.actionAllowed("userlist");
        case "policies":
          return this.authService.actionAllowed("policyread") || this.authService.actionAllowed("eventhandling_read");
        case "subscription":
          return this.authService.actionAllowed("managesubscription");
        case "logs":
          return this.authService.oneActionAllowed([
            "auditlog",
            "authentication_log_read",
            "clienttype",
            "user_lock_read",
            "blocklist_read"
          ]);
        case "external_services":
          return this.authService.oneActionAllowed([
            "smtpserver_read",
            "radiusserver_read",
            "privacyideaserver_read",
            "smsgateway_read"
          ]);
        case "config":
          return this.authService.oneActionAllowed([
            "configread",
            "resolverread",
            "mresolverread",
            "caconnectorread",
            "periodictask_read"
          ]);
        default:
          return true;
      }
    });
  }

  private setupOverflowDetection(): void {
    if (!this.mainNavRef) return;
    const navEl = this.mainNavRef.nativeElement;

    this.resizeObserver = new ResizeObserver((entries) => {
      // A size change of the bar that does not move its width is ignored; a size change of an
      // item or of the More button (a label or locale change) always re-measures.
      const itemResized = entries.some((entry) => entry.target !== navEl);
      if (!itemResized && navEl.clientWidth === this.lastNavWidth) return;
      this.calculateVisibleItems(navEl);
    });
    this.resizeObserver.observe(navEl);

    setTimeout(() => this.calculateVisibleItems(navEl), 0);
  }

  private calculateVisibleItems(navEl: HTMLElement): void {
    const filteredItems = this.getFilteredNavItems();
    const activeSection = this.activeSection();
    const activeIdx = filteredItems.findIndex((item) => item.section === activeSection);

    // A hovered item is mid-transition, so its width is not its resting width: it only provides a
    // width while none is stored. Its next size change re-measures it through the observer.
    for (const item of Array.from(navEl.querySelectorAll<HTMLElement>(".nav-item[data-section]"))) {
      const section = item.getAttribute("data-section");
      this.resizeObserver?.observe(item);
      if (section && (!item.matches(":hover") || !this.itemWidths.has(section))) {
        this.itemWidths.set(section, item.offsetWidth);
      }
    }

    // The More button's width is measured while it is rendered and cached, so the budget does not
    // depend on whether the button currently exists.
    const moreBtnContainer = navEl.querySelector<HTMLElement>(".more-button")?.closest<HTMLElement>(".nav-item");
    if (moreBtnContainer) this.resizeObserver?.observe(moreBtnContainer);
    if (moreBtnContainer?.offsetWidth) {
      this.moreButtonWidth = moreBtnContainer.offsetWidth;
    }

    const navWidth = navEl.clientWidth;
    this.lastNavWidth = navWidth;
    const gap = 8;
    const safetyBuffer = 30;
    const itemCount = filteredItems.length;
    const current = Math.min(this.visibleNavCount(), itemCount);

    const widthOf = (items: NavItem[]) =>
      items.reduce(
        (sum, item, idx) => sum + (this.itemWidths.get(item.section) || 200) + (idx < items.length - 1 ? gap : 0),
        0
      );

    // Whether the first `c` items (the active item standing in for the last one when it is
    // overflowed) fit. Every count, including "all items", is judged against the same budget, which
    // always reserves the More button, so the folded and the unfolded state cannot each decide for
    // the other. `margin` is the extra room a state must have to be entered.
    const fits = (c: number, margin: number): boolean => {
      const shown =
        activeIdx !== -1 && activeIdx >= c
          ? [...filteredItems.slice(0, c - 1), filteredItems[activeIdx]]
          : filteredItems.slice(0, c);
      return widthOf(shown) <= navWidth - this.moreButtonWidth - safetyBuffer - margin;
    };

    let count = 0;
    for (let c = 1; c <= itemCount; c++) {
      // Showing more than the current count requires the hysteresis margin; keeping or showing
      // fewer does not.
      if (fits(c, c > current ? this.unfoldHysteresis : 0)) {
        count = c;
      } else {
        break;
      }
    }

    // With every item visible the More button is gone, so the whole list only has to fit the bar.
    // The same extra room as for any unfold applies when entering that state.
    const allFitMargin = current < itemCount ? this.unfoldHysteresis : 0;
    if (widthOf(filteredItems) <= navWidth - safetyBuffer - allFitMargin) {
      count = itemCount;
    }

    this.visibleNavCount.set(count);
  }
}
