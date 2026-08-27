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
import { DatePipe } from "@angular/common";
import { Component, computed, effect, inject, LOCALE_ID, OnInit, signal, TemplateRef, viewChild } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { TruncationTooltipDirective } from "@components/shared/directives/truncation-tooltip.directive";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { IntegrationsService, IntegrationsServiceInterface } from "@services/integrations/integrations.service";
import {
  SubscriptionService,
  SubscriptionState,
  SubscriptionStatus
} from "@services/subscription/subscription.service";

/**
 * A row of the overview: the server, a section header, or one component. Section
 * headers carry no status; every other row does.
 */
export interface SubscriptionRow {
  kind: "server" | "label" | "component";
  indent: number;
  label?: string;
  application?: string;
  status?: SubscriptionStatus;
}

/** A node of the section tree the overview is built from. */
interface SectionNode {
  label?: string;
  application?: string;
  children?: SectionNode[];
}

/**
 * Display name, section grouping and product-landing-page slug for the server row: it is
 * not one of the dashboard integrations from the shared catalog (see
 * services/integrations/integrations.service.ts and issue #5705), just always present on
 * its own at the top.
 */
const SERVER_DISPLAY_NAME = "privacyIDEA Server";
const PTL_BASE_URL = "https://netknights.it/plugin-traffic-light";
const SERVER_PTL_SLUG = "privacyidea-server";

/**
 * Display label per dashboard section key. The catalog's `Integration.section` is a
 * stable key (e.g. "system_login"), not display text - the backend has no access to the
 * admin's UI locale, so each frontend translates it locally.
 */
function sectionLabel(section: string): string {
  switch (section) {
    case "use_cases":
      return $localize`Use Cases`;
    case "system_login":
      return $localize`System Login`;
    case "single_sign_on":
      return $localize`Single Sign On`;
    default:
      return section;
  }
}

@Component({
  selector: "app-subscriptions-widget",
  standalone: true,
  imports: [
    WidgetStateComponent,
    MatTooltipModule,
    MatIcon,
    MatIconButton,
    DatePipe,
    CopyButtonComponent,
    TruncationTooltipDirective
  ],
  templateUrl: "./subscriptions-widget.component.html",
  styleUrl: "./subscriptions-widget.component.scss"
})
export class SubscriptionsWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "subscriptions";
  static override readonly requiredAction = "managesubscription";
  static override readonly title = $localize`Subscriptions`;
  static override readonly icon = "event_repeat";
  static override readonly titleLink = ROUTE_PATHS.SUBSCRIPTION;
  static override readonly titleLinkAction = "managesubscription";
  // The default is tall enough for the compact view to show every component without
  // scrolling, at the row height the inherited font size gives; widening it makes room for
  // the detailed view's extra columns.
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 11 };
  static override readonly minSize: WidgetSize = { cols: 5, rows: 4 };
  static override readonly maxSize: WidgetSize = { cols: 16, rows: 16 };

  // Read by the widget frame, which renders these in its header.
  override readonly headerActions = viewChild<TemplateRef<unknown>>("headerActions");

  private readonly subscriptionService = inject(SubscriptionService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly integrationsService: IntegrationsServiceInterface = inject(IntegrationsService);
  private readonly store = inject(DashboardDataStore);
  private readonly locale = inject(LOCALE_ID);

  /**
   * Dashboard rows grouped by section, in the order the catalog reports them. Each
   * distinct section becomes a top-level group (there is no further nesting: "System
   * Login" and "Single Sign On" are peers of "Use Cases", not children of it).
   */
  private readonly sections = computed<SectionNode[]>(() => {
    const bySection = new Map<string, SectionNode[]>();
    for (const integration of this.integrationsService.dashboardIntegrations()) {
      const section = integration.section ?? "";
      const children = bySection.get(section) ?? [];
      children.push({ application: integration.id });
      bySection.set(section, children);
    }
    return Array.from(bySection.entries()).map(([section, children]) => ({ label: sectionLabel(section), children }));
  });

  private readonly dataRef = signal<DashboardDataRef<PiResponse<SubscriptionStatus[]>> | null>(null);
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);
  override readonly refreshFailed = computed(() => {
    const ref = this.dataRef();
    return !!ref && ref.error() && ref.value() !== undefined;
  });

  /** Compact shows the two status dots only; detailed adds the expiry and version columns. */
  readonly detailed = signal(false);

  // Localized in the component: a tooltip bound to an expression is not extractable in
  // the template.
  readonly detailToggleTooltip = computed(() => (this.detailed() ? $localize`Compact view` : $localize`Detailed view`));

  readonly rows = computed<SubscriptionRow[]>(() => this.buildRows(this.dataRef()?.value()?.result?.value ?? []));

  /** The panel's data as JSON, for the copy button. Section headers are left out. */
  readonly statusJson = computed(() =>
    JSON.stringify(
      this.rows()
        .filter((row) => row.kind !== "label")
        .map((row) => row.status),
      null,
      2
    )
  );

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      const value = ref.value();
      if (value === undefined) {
        this.state.set(ref.error() ? "error" : "loading");
        return;
      }
      this.state.set(value.result?.status === true ? "ready" : "error");
    });
  }

  override reload(): void {
    this.ngOnInit();
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("managesubscription")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(
      this.store.load("dashboard:subscription-status", () => this.subscriptionService.getSubscriptionStatus())
    );
  }

  toggleDetailed(): void {
    this.detailed.update((detailed) => !detailed);
  }

  protected displayName(application: string): string {
    if (application === "privacyidea") {
      return SERVER_DISPLAY_NAME;
    }
    return this.integrationsService.labelFor(application);
  }

  /**
   * Landing page of a component as <base>/<language>/<sla|non-sla|expired>/<slug>. Only
   * German is served in its own language, every other locale gets the English page.
   * Returns null for components without a slug, which are then rendered as plain text.
   */
  protected componentLink(status: SubscriptionStatus): string | null {
    const slug =
      status.application === "privacyidea"
        ? SERVER_PTL_SLUG
        : this.integrationsService.integrations().find((integration) => integration.id === status.application)
            ?.ptl_slug;
    if (!slug) {
      return null;
    }
    const language = this.locale.startsWith("de") ? "de" : "en";
    return `${PTL_BASE_URL}/${language}/${this.subscriptionSegment(status.subscription)}/${slug}`;
  }

  /**
   * Which of the three landing pages a row points at: none on file, one that has expired,
   * or a subscription that still covers the component - valid, expiring and exceeded are
   * all subscribers.
   */
  private subscriptionSegment(state: SubscriptionState): string {
    switch (state) {
      case "none":
        return "non-sla";
      case "expired":
        return "expired";
      default:
        return "sla";
    }
  }

  protected usageDotClass(inUse: boolean): string {
    return inUse ? "dot-good" : "dot-bad";
  }

  /**
   * The glyph shown inside a status dot. Without it the usage column would be a green
   * dot against a red one, which is the pair colour-blind admins cannot separate, so
   * every state carries a shape next to its colour.
   */
  protected dotGlyph(dotClass: string): string {
    switch (dotClass) {
      case "dot-good":
        return "\u2713";
      case "dot-warn":
        return "!";
      case "dot-bad":
        return "\u2715";
      default:
        return "\u2013";
    }
  }

  /**
   * Why the usage dot has the colour it has. For the "subscription or recent activity"
   * rule we name the branch that actually applies instead of making the admin guess.
   */
  protected usageReason(status: SubscriptionStatus): string {
    if (status.is_server) {
      return $localize`In use: this is the privacyIDEA server itself.`;
    }
    if (!status.in_use) {
      return $localize`Not in use: no subscription, and not seen in the last 7 days.`;
    }
    return status.subscription === "none"
      ? $localize`In use: seen within the last 7 days.`
      : $localize`In use: covered by a subscription.`;
  }

  protected subscriptionDotClass(state: SubscriptionState): string {
    switch (state) {
      case "valid":
        return "dot-good";
      case "expiring":
      case "exceeded":
        return "dot-warn";
      case "expired":
        return "dot-bad";
      default:
        return "dot-none";
    }
  }

  /**
   * What the expiry column adds next to the date: the state of the subscription and how
   * far off that date is. The state is spelled out because the detailed view has no
   * status dots, and because a date alone cannot say that an otherwise valid
   * subscription is exceeded.
   */
  protected expiryNote(status: SubscriptionStatus): string {
    const state = this.subscriptionStateLabel(status.subscription);
    const daysLeft = status.days_left;
    if (daysLeft === null) {
      return state;
    }
    if (daysLeft === 0) {
      // The count is between calendar dates, so zero means the date is today: neither
      // "0 days left" nor "0 days ago" says that.
      return $localize`${state}:state:, today`;
    }
    return daysLeft < 0
      ? $localize`${state}:state:, ${-daysLeft}:days: days ago`
      : $localize`${state}:state:, ${daysLeft}:days: days left`;
  }

  /** Lower case: the label is read inside the expiry column's note, not on its own. */
  private subscriptionStateLabel(state: SubscriptionState): string {
    switch (state) {
      case "valid":
        return $localize`valid`;
      case "expiring":
        return $localize`expiring`;
      case "exceeded":
        return $localize`exceeded`;
      case "expired":
        return $localize`expired`;
      default:
        return $localize`no subscription`;
    }
  }

  protected subscriptionReason(state: SubscriptionState): string {
    switch (state) {
      case "valid":
        return $localize`Valid: subscription in place and no other condition applies.`;
      case "expiring":
        return $localize`Expiring: the subscription ends in less than 60 days.`;
      case "exceeded":
        return $localize`Exceeded: subscription is valid, but more tokens are in use than it allows.`;
      case "expired":
        return $localize`Expired: the subscription's end date has passed.`;
      default:
        return $localize`No subscription. Get a subscription for enterprise support.`;
    }
  }

  /** Placeholder status for a component the backend did not report. */
  private unusedStatus(application: string): SubscriptionStatus {
    return {
      application,
      in_use: false,
      subscription: "none",
      last_seen: null,
      date_till: null,
      days_left: null,
      versions: [],
      current_version: null,
      current_version_date: null,
      current_version_url: null
    };
  }

  /** Turn the backend status list into the flat, sectioned rows the template renders. */
  private buildRows(entries: SubscriptionStatus[]): SubscriptionRow[] {
    const statusByApplication = new Map<string, SubscriptionStatus>();
    let serverStatus: SubscriptionStatus | null = null;
    for (const entry of entries) {
      if (entry.is_server) {
        serverStatus = entry;
      }
      statusByApplication.set(entry.application, entry);
    }
    const rows: SubscriptionRow[] = [
      { kind: "server", indent: 0, status: serverStatus ?? this.unusedStatus("privacyidea") }
    ];
    this.flattenSections(this.sections(), 0, rows, statusByApplication);
    return rows;
  }

  private flattenSections(
    nodes: SectionNode[],
    depth: number,
    rows: SubscriptionRow[],
    statusByApplication: Map<string, SubscriptionStatus>
  ): void {
    for (const node of nodes) {
      if (node.label) {
        rows.push({ kind: "label", indent: depth, label: node.label });
        this.flattenSections(node.children ?? [], depth + 1, rows, statusByApplication);
      } else if (node.application) {
        rows.push({
          kind: "component",
          indent: depth,
          application: node.application,
          status: statusByApplication.get(node.application) ?? this.unusedStatus(node.application)
        });
      }
    }
  }
}
