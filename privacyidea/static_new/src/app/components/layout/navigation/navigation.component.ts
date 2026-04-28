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
import {
  AfterViewInit,
  Component,
  computed,
  ElementRef,
  inject,
  NgZone,
  OnDestroy,
  signal,
  ViewChild
} from "@angular/core";
import { NgClass, NgOptimizedImage, NgTemplateOutlet } from "@angular/common";
import { MatToolbar } from "@angular/material/toolbar";
import { MatTabsModule } from "@angular/material/tabs";
import { ROUTE_PATHS } from "src/app/route_paths";
import { MatIconButton } from "@angular/material/button";
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
  imports: [
    MatToolbar,
    MatTabsModule,
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
  private itemWidths = new Map<string, number>();
  private resizeObserver: ResizeObserver | null = null;
  private ngZone = inject(NgZone);
  @ViewChild("mainNavRef", { static: false }) mainNavRef!: ElementRef<HTMLElement>;
  primaryNavItems: NavItem[] = [
    { icon: "shield", label: $localize`Token`, route: ROUTE_PATHS.TOKENS, section: "token" },
    { icon: "folder", label: $localize`Container`, route: ROUTE_PATHS.TOKENS_CONTAINERS, section: "container" },
    { icon: "supervised_user_circle", label: $localize`Users`, route: ROUTE_PATHS.USERS, section: "users" },
    { icon: "gavel", label: $localize`Policies`, route: ROUTE_PATHS.POLICIES, section: "policies" },
    { icon: "event_repeat", label: $localize`Subscription`, route: ROUTE_PATHS.SUBSCRIPTION, section: "subscription" },
    { icon: "receipt_long", label: $localize`Audit`, route: ROUTE_PATHS.AUDIT, section: "audit" },
    {
      icon: "hub",
      label: $localize`External Services`,
      route: ROUTE_PATHS.EXTERNAL_SERVICES_SMTP,
      section: "external"
    },
    {
      icon: "miscellaneous_services",
      label: $localize`Configuration`,
      route: ROUTE_PATHS.CONFIGURATION_SYSTEM,
      section: "config"
    }
  ];
  visibleNavCount = signal(this.primaryNavItems.length);
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
    if (url.startsWith(ROUTE_PATHS.SUBSCRIPTION)) return "subscription";
    if (url.startsWith(ROUTE_PATHS.AUDIT) || url.startsWith(ROUTE_PATHS.CLIENTS)) return "audit";
    if (url.startsWith("/external-services")) return "external";
    if (url.startsWith("/configuration") || url.startsWith(ROUTE_PATHS.MACHINE_RESOLVER) || url.startsWith(ROUTE_PATHS.EVENTS)) return "config";
    if (url.startsWith(ROUTE_PATHS.TOKENS)) return "token";
    return "token";
  });
  isOverflowSectionActive = computed(() => {
    return this.overflowNavItems.some(item => item.section === this.activeSection());
  });

  get visibleNavItems(): NavItem[] {
    const items = this.getFilteredNavItems();
    const count = this.visibleNavCount();
    const activeSection = this.activeSection();
    const activeIdx = items.findIndex(item => item.section === activeSection);

    if (activeIdx !== -1 && activeIdx >= count) {
      return [...items.slice(0, count - 1), items[activeIdx]];
    }

    return items.slice(0, count);
  }

  get overflowNavItems(): NavItem[] {
    const items = this.getFilteredNavItems();
    const count = this.visibleNavCount();
    const activeSection = this.activeSection();
    const activeIdx = items.findIndex(item => item.section === activeSection);

    if (activeIdx !== -1 && activeIdx >= count) {
      const head = items.slice(0, count - 1);
      const activeItem = items[activeIdx];
      return items.filter(item => item !== activeItem && !head.includes(item));
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
    (event as any).stopImmediatePropagation?.();
    event.stopPropagation();

    this.router.navigate([route_path]);
  }

  openSupport(): void {
    window.open("https://netknights.it/support_link_admin", "_blank");
  }

  openExternalLink(url: string): void {
    window.open(url, "_blank");
  }

  private getFilteredNavItems(): NavItem[] {
    return this.primaryNavItems.filter(item => {
      if (item.section === "policies") return this.authService.actionAllowed("policyread");
      return true;
    });
  }

  private setupOverflowDetection(): void {
    if (!this.mainNavRef) return;
    const navEl = this.mainNavRef.nativeElement;

    this.resizeObserver = new ResizeObserver(() => {
      this.ngZone.run(() => this.calculateVisibleItems(navEl));
    });
    this.resizeObserver.observe(navEl);

    setTimeout(() => this.calculateVisibleItems(navEl), 0);
  }

  private calculateVisibleItems(navEl: HTMLElement): void {
    const filteredItems = this.getFilteredNavItems();

    const currentNavItems = Array.from(navEl.querySelectorAll<HTMLElement>(".nav-item[data-section]"));

    for (const item of currentNavItems) {
      const section = item.getAttribute("data-section");
      if (section) {
        this.itemWidths.set(section, item.offsetWidth);
      }
    }

    const moreBtn = navEl.querySelector<HTMLElement>(".more-button");
    const moreBtnContainer = moreBtn?.closest(".nav-item") as HTMLElement;
    const moreButtonWidth = moreBtnContainer?.offsetWidth || 80;

    const navWidth = navEl.clientWidth;
    const gap = 4;
    let usedWidth = 0;
    let count = 0;

    for (const item of filteredItems) {
      const itemWidth = this.itemWidths.get(item.section) || 120; // Fallback to a reasonable default

      const remaining = filteredItems.length - count;
      const needsMore = remaining > 1;
      const availableWidth = needsMore ? navWidth - moreButtonWidth : navWidth;

      if (usedWidth + itemWidth + gap <= availableWidth) {
        usedWidth += itemWidth + gap;
        count++;
      } else {
        break;
      }
    }

    this.visibleNavCount.set(Math.max(1, Math.min(count, filteredItems.length)));
  }
}
