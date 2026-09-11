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
import { Component, computed, input, output, signal } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltipModule } from "@angular/material/tooltip";
import { CopyableComponent } from "@components/shared/copyable/copyable.component";
import { FilterValueButtonComponent } from "@components/shared/filter-value-button/filter-value-button.component";
import { AuthenticationLogEntry } from "@services/authentication-log/authentication-log.service";

// What each recorded derivation is called in the column, and what the badge explains on hover. Mirrors
// privacyidea.lib.utils.ClientIpSource. A value outside this table - including null, which is what an entry
// written before the recording carries - gets no badge at all: the one thing that must never be shown is a
// guess, and "direct" would be exactly that.
const IP_SOURCE_META: Record<string, { label: string; tooltip: string; modifier: string }> = {
  REMOTE_ADDR: {
    label: $localize`direct`,
    tooltip: $localize`The address privacyIDEA saw the connection come from. No client override is configured, so no forwarded address is honoured.`,
    modifier: "ip-source-badge--direct"
  },
  REMOTE_ADDR_UNMAPPED: {
    label: $localize`unmapped`,
    tooltip: $localize`A client override is configured, but this peer is not allowed to map the client any further, so the address it connected from was used.`,
    modifier: "ip-source-badge--unmapped"
  },
  X_FORWARDED_FOR: {
    label: $localize`proxy`,
    tooltip: $localize`Taken from the X-Forwarded-For header, from a proxy the client override permits.`,
    modifier: "ip-source-badge--proxy"
  },
  CLIENT_PARAM: {
    label: $localize`client parameter`,
    tooltip: $localize`Taken from the request's own client parameter, which the client override permits for this proxy path.`,
    modifier: "ip-source-badge--param"
  }
};

// What each hop of the recorded path is called in the expanded view.
const HOP_SOURCE_LABELS: Record<string, string> = {
  REMOTE_ADDR: $localize`connection`,
  X_FORWARDED_FOR: $localize`X-Forwarded-For`,
  CLIENT_PARAM: $localize`client parameter`
};

/**
 * The authentication log's Source IP cell: which address the request was judged to come from, and how that was
 * decided.
 *
 * The effective address stays the one visible line - it is what authorization and conditional access act on, and
 * it is what the column has always shown. Everything else is behind an expand toggle: the peer the request
 * actually arrived from, and the path that was considered to get from one to the other.
 *
 * Everything past the peer is client-supplied. It is shown as what the request *claimed*, never as fact.
 */
@Component({
  selector: "app-source-ip-cell",
  standalone: true,
  imports: [CopyableComponent, FilterValueButtonComponent, MatIcon, MatTooltipModule],
  templateUrl: "./source-ip-cell.html",
  styleUrl: "./source-ip-cell.scss"
})
export class SourceIpCell {
  readonly sourceIp = input<string | null | undefined>(null);
  readonly peerIp = input<string | null | undefined>(null);
  readonly sourceIpSource = input<string | null | undefined>(null);
  readonly ipChain = input<AuthenticationLogEntry["ip_chain"]>(null);
  // Whether the cell offers the inline "filter by this value" button, which the table turns off while the
  // column header carries a value picker of its own.
  readonly showFilter = input<boolean>(true);
  // Identifies this cell's revealed body for aria-controls; unique within the rendered page.
  readonly cellId = input<string>("");

  readonly filterValue = output<{ key: string; value: string }>();

  readonly expanded = signal(false);

  readonly badge = computed(() => {
    const source = this.sourceIpSource();
    return source ? (IP_SOURCE_META[source] ?? null) : null;
  });

  // The peer is only worth its own line when it is not the address already shown.
  readonly showsPeer = computed<boolean>(() => {
    const peer = this.peerIp();
    return !!peer && peer !== this.sourceIp();
  });

  readonly hops = computed(() => {
    const chain = this.ipChain();
    return Array.isArray(chain) ? chain : [];
  });

  readonly canExpand = computed<boolean>(() => this.showsPeer() || this.hops().length > 0);

  hopLabel(source: string): string {
    return HOP_SOURCE_LABELS[source] ?? source;
  }

  toggle(): void {
    this.expanded.update((expanded) => !expanded);
  }

  onFilter(key: string, value: string): void {
    this.filterValue.emit({ key, value });
  }
}
