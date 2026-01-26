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
import { ScrollToTopDirective } from "../shared/directives/app-scroll-to-top.directive";
import { AuthService } from "../../services/auth/auth.service";
import { EMPTY_EVENT, EventHandler, EventService } from "../../services/event/event.service";
import { EventPanelComponent } from "./event-panel/event-panel.component";
import { MatTableDataSource, MatTableModule } from "@angular/material/table";
import { CommonModule } from "@angular/common";
import { MatButtonModule } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { animate, state, style, transition, trigger } from "@angular/animations";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatTooltip } from "@angular/material/tooltip";
import { MatDialog } from "@angular/material/dialog";
import { Sort } from "@angular/material/sort";
import { ClearableInputComponent } from "../shared/clearable-input/clearable-input.component";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatPaginator } from "@angular/material/paginator";
import { TableUtilsService, TableUtilsServiceInterface } from "../../services/table-utils/table-utils.service";
import { MatFormField } from "@angular/material/form-field";
import { of } from "rxjs";
import { HighlightPipe } from "../shared/pipes/highlight.pipe";

@Component({
  selector: "app-event",
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    ScrollToTopDirective,
    MatIcon,
    MatSlideToggle,
    MatTooltip,
    ClearableInputComponent,
    MatFormField,
    MatInput,
    MatLabel,
    MatPaginator,
    HighlightPipe
  ],
  standalone: true,
  templateUrl: "./event.component.html",
  styleUrl: "./event.component.scss",
  animations: [
    trigger("detailExpand", [
      state("collapsed", style({ height: "0px", minHeight: "0" })),
      state("expanded", style({ height: "*" })),
      transition("expanded <=> collapsed", animate("225ms cubic-bezier(0.4, 0.0, 0.2, 1)"))
    ])
  ]
})
export class EventComponent {
  protected readonly authService = inject(AuthService);
  protected readonly eventService = inject(EventService);
  protected readonly EMPTY_EVENT = EMPTY_EVENT;
  protected readonly dialog = inject(MatDialog);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);

  columnKeysMap: Record<string, string> = {
    "ordering": "Ordering",
    "name": "Name",
    "handlermodule": "Handler Module",
    "position": "Position",
    "event": "Events",
    "action": "Action",
    "conditions": "Conditions",
    "active": "Active",
    "delete": "Delete"
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
      .map(([key, value]) => `${key}: ${value}`)
      .join(", ");
  }

  private clientsideSortEventData(data: EventHandler[], s: Sort): EventHandler[] {
    if (!s.direction) return data;
    const dir = s.direction === "asc" ? 1 : -1;
    const key = s.active as keyof EventHandler;
    return data.sort((a: any, b: any) => {
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

  private openEventHandlerDialog(eventHandler?: EventHandler, isNew?: boolean): void {
    const dialogData = {
      data: { eventHandler, isNewEvent: isNew },
      width: "auto",
      height: "auto",
      maxWidth: "100vw",
      maxHeight: "100vh"
    };
    this.dialog.open(EventPanelComponent, dialogData);
  }

  onEditEventHandler(eventHandler: EventHandler) {
    this.openEventHandlerDialog(eventHandler, false);
  }

  onCreateNewEventHandler() {
    this.openEventHandlerDialog(EMPTY_EVENT, true);
  }

  onDeleteEventHandler(eventHandler: EventHandler) {
    this.eventService.deleteWithConfirmDialog(eventHandler, this.dialog, () => this.eventService.allEventsResource.reload());
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

  protected readonly Object = Object;
  protected readonly of = of;
  protected readonly Array = Array;
}
