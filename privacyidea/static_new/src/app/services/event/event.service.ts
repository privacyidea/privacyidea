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

import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { computed, effect, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { lastValueFrom, Observable, of, throwError } from "rxjs";
import { catchError } from "rxjs/operators";

export interface EventHandler {
  id: number | null;
  name: string;
  active: boolean;
  handlermodule: string;
  ordering: number;
  position: string;
  event: string[];
  action: string;
  options: Record<string, any> | null;
  conditions: Record<string, any>;
}

export const EMPTY_EVENT: EventHandler = {
  id: null,
  name: "",
  active: true,
  handlermodule: "",
  ordering: 0,
  position: "post",
  event: [],
  action: "",
  options: {},
  conditions: {}
};

export interface EventCondition {
  desc: string;
  type: string;
  group?: string;
  value?: any[];
}

export interface ActionOptionDetails {
  type?: string;
  desc?: string;
  description?: string;
  required?: boolean;
  value?: any[];
  visibleIf?: string;
  visibleValue?: any;
}

export type ActionOptions = Record<string, ActionOptionDetails>;

export type EventActions = Record<string, ActionOptions>;

export interface EventHandlerSaveParams {
  id?: string;
  name: string;
  active: boolean;
  handlermodule: string | null;
  ordering: number;
  position: string;
  event: string[];
  action: string;
  conditions: Record<string, unknown>;
  [key: string]: unknown;
}

export interface EventServiceInterface {
  selectedHandlerModule: WritableSignal<string | null>;
  readonly allEventsResource: HttpResourceRef<PiResponse<EventHandler[]> | undefined>;
  eventHandlers: Signal<EventHandler[] | undefined>;

  saveEventHandler(event: EventHandlerSaveParams): Observable<PiResponse<number> | undefined>;

  enableEvent(eventId: number | null): Promise<object | undefined>;

  disableEvent(eventId: number | null): Promise<object | undefined>;

  deleteEvent(eventId: number): Observable<PiResponse<number>>;

  deleteWithConfirmDialog(event: EventHandler): void;

  readonly eventHandlerModulesResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  eventHandlerModules: Signal<string[]>;
  readonly availableEventsResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  availableEvents: Signal<string[]>;
  readonly modulePositionsResource: HttpResourceRef<PiResponse<string[]> | undefined>;
  modulePositions: Signal<string[]>;
  readonly moduleActionsResource: HttpResourceRef<PiResponse<EventActions> | undefined>;
  moduleActions: Signal<EventActions>;
  readonly moduleConditionsResource: HttpResourceRef<PiResponse<Record<string, EventCondition>> | undefined>;
  moduleConditions: Signal<Record<string, EventCondition>>;
  moduleConditionsByGroup: Signal<Record<string, Record<string, EventCondition>> | undefined>;
}

@Injectable()
export class EventService implements EventServiceInterface {
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly http = inject(HttpClient);

  readonly eventBaseUrl = environment.proxyUrl + "/event";
  selectedHandlerModule = signal<string | null>(null);

  // ----------------------------
  // Read existing event handlers
  // ----------------------------

  readonly allEventsResource = httpResource<PiResponse<EventHandler[]>>(() => {
    // Check right to access events
    if (!this.authService.actionAllowed("eventhandling_read")) {
      return undefined;
    }
    // Check if we are on the event route
    if (!this.contentService.onEvents()) {
      return undefined;
    }
    // Everything is valid, fetch events
    return {
      url: `${this.eventBaseUrl}/`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  eventHandlers: Signal<EventHandler[] | undefined> = computed(() => {
    if (this.allEventsResource.hasValue()) {
      return this.allEventsResource.value()?.result?.value ?? [];
    }
    return [] as unknown as EventHandler[];
  });

  // -------------------------------------
  // Edit functionality for event handlers
  // -------------------------------------

  saveEventHandler(event: EventHandlerSaveParams): Observable<PiResponse<number> | undefined> {
    const headers = this.authService.getHeaders();
    const params = { ...event };
    if (params.id == null) {
      delete params.id;
    }
    return this.http.post<PiResponse<number>>(this.eventBaseUrl, params, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to save event handler.", error.error);
        const message = error.error.result?.error?.message || "";
        this.notificationService.error("Failed to save event handler. " + message);
        return of(undefined);
      })
    );
  }

  enableEvent(eventId: number | null) {
    if (eventId === null) {
      this.notificationService.error("Can not enable event handler due to missing ID");
      return Promise.resolve(undefined);
    }
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post(this.eventBaseUrl + "/enable/" + encodeURIComponent(eventId), {}, { headers: headers }).pipe(
        catchError((error) => {
          console.log("Failed to enable event handler:", error);
          this.allEventsResource.reload();
          this.notificationService.error("Failed to enable event handler!");
          return of(undefined);
        })
      )
    );
  }

  disableEvent(eventId: number | null) {
    if (eventId === null) {
      this.notificationService.warning("Can not disable event handler due to missing ID");
      return Promise.resolve(undefined);
    }
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post(this.eventBaseUrl + "/disable/" + encodeURIComponent(eventId), {}, { headers: headers }).pipe(
        catchError((error) => {
          console.log("Failed to disable event handler:", error);
          this.allEventsResource.reload();
          this.notificationService.error("Failed to disable event handler!");
          return of(undefined);
        })
      )
    );
  }

  deleteEvent(eventId: number): Observable<PiResponse<number>> {
    const headers = this.authService.getHeaders();

    return this.http
      .delete<PiResponse<number>>(this.eventBaseUrl + "/" + encodeURIComponent(eventId), { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete event handler.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to delete event handler. " + message);
          return throwError(() => error);
        })
      );
  }

  async deleteWithConfirmDialog(event: EventHandler): Promise<PiResponse<number> | undefined> {
    const confirmation = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Event Handler`,
            items: [event.name],
            itemType: $localize`event handler`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
          }
        })
        .afterClosed()
    );
    if (!confirmation) {
      return;
    }
    try {
      if (event.id == null) {
        this.notificationService.error("Failed to delete event handler: Missing ID.");
        return;
      }
      const result = await lastValueFrom(this.deleteEvent(event.id));

      this.notificationService.success("Successfully deleted event handler.");
      return result;
    } catch {
      // error already handled in deleteEvent
      return;
    }
  }

  // -------------------------------------
  // Get configuration for create and edit
  // -------------------------------------

  readonly eventHandlerModulesResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.contentService.onEvents()) {
      return undefined;
    }
    return {
      url: this.eventBaseUrl + "/handlermodules",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  eventHandlerModules = computed(() => {
    if (!this.eventHandlerModulesResource.hasValue()) return [];
    const resource = this.eventHandlerModulesResource.value();
    if (resource) {
      return resource.result?.value || [];
    }
    return [];
  });

  readonly availableEventsResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.contentService.onEvents()) {
      return undefined;
    }
    return {
      url: this.eventBaseUrl + "/available",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  availableEvents = computed(() => {
    if (!this.availableEventsResource.hasValue()) return [];
    const resource = this.availableEventsResource.value();
    if (resource) {
      return resource.result?.value || [];
    }
    return [];
  });

  readonly modulePositionsResource = httpResource<PiResponse<string[]>>(() => {
    if (!this.selectedHandlerModule()) {
      return undefined;
    }
    return {
      url: this.eventBaseUrl + "/positions/" + encodeURIComponent(this.selectedHandlerModule() || ""),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  modulePositions = computed(() => {
    if (!this.modulePositionsResource.hasValue()) return [];
    const resource = this.modulePositionsResource.value();
    if (resource) {
      return resource.result?.value || [];
    }
    return [];
  });

  readonly moduleActionsResource = httpResource<PiResponse<EventActions>>(() => {
    if (!this.selectedHandlerModule()) {
      return undefined;
    }
    return {
      url: this.eventBaseUrl + "/actions/" + encodeURIComponent(this.selectedHandlerModule() || ""),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  moduleActions = computed(() => {
    if (!this.moduleActionsResource.hasValue()) return {};
    const resource = this.moduleActionsResource.value();
    if (resource) {
      return resource.result?.value || {};
    }
    return {};
  });

  readonly moduleConditionsResource = httpResource<PiResponse<Record<string, EventCondition>>>(() => {
    if (!this.selectedHandlerModule()) {
      return undefined;
    }
    return {
      url: this.eventBaseUrl + "/conditions/" + encodeURIComponent(this.selectedHandlerModule() || ""),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  moduleConditions = computed(() => {
    if (!this.moduleConditionsResource.hasValue()) return {};
    const resource = this.moduleConditionsResource.value();
    if (resource) {
      return resource.result?.value || {};
    }
    return {};
  });

  moduleConditionsByGroup = computed(() => {
    const conditions: Record<string, Record<string, EventCondition>> = {};
    for (const [conditionName, conditionDetails] of Object.entries(this.moduleConditions())) {
      const group = conditionDetails.group || "miscellaneous";
      if (!(group in conditions)) {
        conditions[group] = {};
      }
      conditions[group][conditionName] = conditionDetails;
    }
    return conditions;
  });

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.allEventsResource.error(), "event handlers");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.eventHandlerModulesResource.error(), "event handler modules");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.availableEventsResource.error(), "available events");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.modulePositionsResource.error(), "module positions");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.moduleActionsResource.error(), "module actions");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.moduleConditionsResource.error(), "module conditions");
    });
  }
}
