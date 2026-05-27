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

import { CommonModule } from "@angular/common";
import {
  Component,
  computed,
  ElementRef,
  inject,
  linkedSignal,
  signal,
  viewChild,
  ViewChild,
  WritableSignal
} from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatFormField } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { Sort } from "@angular/material/sort";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { MatTooltip } from "@angular/material/tooltip";
import { Router } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { ClearableInputComponent } from "@components/shared/clearable-input/clearable-input.component";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { HighlightPipe } from "@components/shared/pipes/highlight.pipe";
import { AuthService } from "@services/auth/auth.service";
import { EMPTY_EVENT, EventHandler, EventService } from "@services/event/event.service";
import { TableUtilsService, TableUtilsServiceInterface } from "@services/table-utils/table-utils.service";
import { of } from "rxjs";

@Component({
  selector: "app-event",
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    ScrollToTopDirective,
    MatIcon,
    MatSlideToggle,
    ClearableInputComponent,
    MatFormField,
    MatInput,
    MatLabel,
    MatPaginator,
    HighlightPipe,
    MatTooltip
  ],
  standalone: true,
  templateUrl: "./event.component.html",
  styleUrl: "./event.component.scss"
})
export class EventComponent {
  protected readonly authService = inject(AuthService);
  protected readonly eventService = inject(EventService);
  protected readonly EMPTY_EVENT = EMPTY_EVENT;
  private readonly router = inject(Router);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  columnKeysMap: Record<string, string> = {
    ordering: "Ordering",
    name: "Name",
    handlermodule: "Handler Module",
    position: "Position",
    event: "Events",
    action: "Action",
    conditions: "Conditions",
    active: "Active",
    delete: "Delete"
  };
  columnKeys = computed(() => {
    let keys = Object.keys(this.columnKeysMap);
    if (!this.authService.actionAllowed("eventhandling_write")) {
      keys = keys.filter((k) => k !== "delete");
    }
    return keys;
  });

  detailedView = signal(false);

  @ViewChild("filterHTMLInputElement", { static: false }) filterInput!: ElementRef<HTMLInputElement>;
  pageSizeOptions = this.tableUtilsService.pageSizeOptions;
  paginator = viewChild(MatPaginator);
  sort = signal({ active: "", direction: "" } as Sort);
  filterString = signal<string>("");

  totalLength: WritableSignal<number> = linkedSignal({
    source: this.eventService.eventHandlers,
    computation: (eventResource, previous) => {
      if (eventResource) {
        return eventResource.length ?? 0;
      }
      return previous?.value ?? 0;
    }
  });

  eventHandlerDataSource: WritableSignal<MatTableDataSource<EventHandler>> = linkedSignal({
    source: () => ({
      eventHandlers: this.eventService.eventHandlers(),
      paginator: this.paginator(),
      sort: this.sort()
    }),
    computation: (source) => {
      const sorted = this.clientsideSortEventData(source.eventHandlers ?? [], this.sort());
      const dataSource = new MatTableDataSource(sorted);
      dataSource.paginator = source.paginator ?? null;

      dataSource.filterPredicate = (data: EventHandler, filter: string) => {
        const normalizedFilter = filter.trim().toLowerCase();
        if (!normalizedFilter) {
          return true;
        }
        return (
          data.name.toLowerCase().includes(normalizedFilter) ||
          data.handlermodule.toLowerCase().includes(normalizedFilter) ||
          data.position.toLowerCase().includes(normalizedFilter) ||
          data.action.toLowerCase().includes(normalizedFilter) ||
          this.filterMatchesActionOptions(data, normalizedFilter) ||
          this.filterMatchesEvents(data, normalizedFilter) ||
          this.filterMatchesConditions(data, normalizedFilter)
        );
      };

      return dataSource;
    }
  });

  private filterMatchesEvents(data: EventHandler, filter: string): boolean {
    // checks if the filter string matches any of the events in the event handler
    for (const event of data.event) {
      if (event.toLowerCase().includes(filter)) {
        return true;
      }
    }
    return false;
  }

  private filterMatchesConditions(data: EventHandler, filter: string): boolean {
    // checks if the filter string matches any of the events in the event handler
    for (const condition of Object.entries(data.conditions)) {
      if ((condition[0] + ": " + condition[1]).toLowerCase().includes(filter)) {
        return true;
      }
    }
    return false;
  }

  private filterMatchesActionOptions(data: EventHandler, filter: string): boolean {
    // checks if the filter string matches any of the events in the event handler
    for (const option of Object.entries(data.options || {})) {
      if ((option[0] + ": " + option[1]).toLowerCase().includes(filter)) {
        return true;
      }
    }
    return false;
  }

  formatConditions(conditions: any): string {
    if (!conditions || typeof conditions !== "object") return "";
    return Object.entries(conditions)
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join(", ");
  }

  private clientsideSortEventData(data: EventHandler[], s: Sort): EventHandler[] {
    if (!s.direction) return data;
    const dir = s.direction === "asc" ? 1 : -1;
    const key = s.active as keyof EventHandler;
    return data.sort((a: EventHandler, b: EventHandler) => {
      const va = (a?.[key] ?? "").toString().toLowerCase();
      const vb = (b?.[key] ?? "").toString().toLowerCase();
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return 0;
    });
  }

  onFilterInput(value: string): void {
    this.filterString.set(value);
    const ds = this.eventHandlerDataSource();
    ds.filter = value.trim().toLowerCase();
  }

  onEditEventHandler(eventHandler: EventHandler) {
    this.router.navigateByUrl(ROUTE_PATHS.EVENTS_DETAILS + eventHandler.id);
  }

  onCreateNewEventHandler() {
    this.router.navigateByUrl(ROUTE_PATHS.EVENTS_NEW);
  }

  async onDeleteEventHandler(eventHandler: EventHandler) {
    await this.eventService.deleteWithConfirmDialog(eventHandler);
    this.eventService.allEventsResource.reload();
  }

  getEventArray(event: unknown): string[] {
    return Array.isArray(event) ? event : [];
  }

  toggleDetailedView(): void {
    this.detailedView.set(!this.detailedView());
  }

  onClearFilter() {
    this.filterString.set("");
    this.onFilterInput("");
  }

  toggleActive(eventHandler: EventHandler): void {
    if (eventHandler.active) {
      this.eventService.disableEvent(eventHandler.id);
    } else {
      this.eventService.enableEvent(eventHandler.id);
    }
  }

  protected readonly Object = Object;
  protected readonly of = of;
  protected readonly Array = Array;
}
