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

import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { lastValueFrom, Observable, of, throwError } from "rxjs";
import { catchError } from "rxjs/operators";
import { NotificationService } from "../notification/notification.service";
import { ConfirmationDialogComponent } from "../../components/shared/confirmation-dialog/confirmation-dialog.component";

export type EventHandler = {
  id: string;
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
  id: "",
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

export type EventCondition = {
  desc: string;
  type: string;
  group?: string;
  value?: any[];
}

export type ActionOptionDetails = {
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

export interface EventServiceInterface {
  selectedHandlerModule: WritableSignal<string | null>;
  readonly allEventsResource: HttpResourceRef<PiResponse<EventHandler[]> | undefined>;
  eventHandlers: Signal<EventHandler[] | undefined>;

  saveEventHandler(event: Record<string, any>): Observable<PiResponse<number, any> | undefined>;

  enableEvent(eventId: string): Promise<Object | undefined>;

  disableEvent(eventId: string): Promise<Object | undefined>;

  deleteEvent(eventId: string): Observable<PiResponse<number, any>>;

  deleteWithConfirmDialog(event: EventHandler, dialog: any, afterDelete?: () => void): void;

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

@Injectable({
  providedIn: "root"
})
export class EventService implements EventServiceInterface {
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly http: HttpClient = inject(HttpClient);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly notificationService = inject(NotificationService);

  readonly eventBaseUrl = environment.proxyUrl + "/event";
  selectedHandlerModule: WritableSignal<string | null> = signal(null);

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
    if (this.allEventsResource.value()) {
      return this.allEventsResource.value()?.result?.value;
    }
    return [] as unknown as EventHandler[];
  });

  // -------------------------------------
  // Edit functionality for event handlers
  // -------------------------------------

  saveEventHandler(event: Record<string, any>): Observable<PiResponse<number, any> | undefined> {
    const headers = this.authService.getHeaders();
    let params = { ...event } as any;
    if (!params.id) {
      delete params.id;
    }
    return this.http.post<PiResponse<number, any>>(
      this.eventBaseUrl,
      params,
      { headers }
    ).pipe(
      catchError((error) => {
        console.error("Failed to save event handler.", error.error);
        const message = error.error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to save event handler. " + message);
        return of(undefined);
      })
    );
  }

  enableEvent(eventId: string) {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post(
      this.eventBaseUrl + "/enable/" + eventId,
      {},
      { headers: headers }
    ).pipe(
      catchError((error) => {
        console.log("Failed to enable event handler:", error);
        this.allEventsResource.reload();
        this.notificationService.openSnackBar("Failed to enable event handler!");
        return of(undefined);
      })
    ));
  }

  disableEvent(eventId: string) {
    const headers = this.authService.getHeaders();
    return lastValueFrom(this.http.post(
      this.eventBaseUrl + "/disable/" + eventId,
      {},
      { headers: headers }
    ).pipe(
      catchError((error) => {
        console.log("Failed to disable event handler:", error);
        this.allEventsResource.reload();
        this.notificationService.openSnackBar("Failed to disable event handler!");
        return of(undefined);
      })
    ));
  }

  deleteEvent(eventId: string): Observable<PiResponse<number, any>> {
    const headers = this.authService.getHeaders();

    return this.http.delete<PiResponse<number, any>>(
      this.eventBaseUrl + "/" + eventId,
      { headers }
    ).pipe(
      catchError((error) => {
        console.error("Failed to delete event handler.", error);
        const message = error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete event handler. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteWithConfirmDialog(event: EventHandler, dialog: any, afterDelete?: () => void) {
    dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [event.name],
          title: "Delete Event Handler",
          type: "eventHandler",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result: any) => {
          if (result.confirmed) {
            this.deleteEvent(event.id).subscribe({
              next: (response: PiResponse<number, any>) => {
                this.notificationService.openSnackBar("Successfully deleted event handler.");
                if (afterDelete) {
                  afterDelete();
                }
              },
              error: (err) => {
                // error already handled
              }
            });
          }
        }
      });
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
      url: this.eventBaseUrl + "/positions/" + this.selectedHandlerModule(),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  modulePositions = computed(() => {
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
      url: this.eventBaseUrl + "/actions/" + this.selectedHandlerModule(),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  moduleActions = computed(() => {
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
      url: this.eventBaseUrl + "/conditions/" + this.selectedHandlerModule(),
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  moduleConditions = computed(() => {
    const resource = this.moduleConditionsResource.value();
    if (resource) {
      return resource.result?.value || {};
    }
    return {};
  });

  moduleConditionsByGroup = computed(() => {
    const conditions: Record<string, any> = {};
    for (const [conditionName, conditionDetails] of Object.entries(this.moduleConditions())) {
      const group = conditionDetails.group || "miscellaneous";
      if (!(group in conditions)) {
        conditions[group] = {};
      }
      conditions[group][conditionName] = conditionDetails;
    }
    return conditions;
  });
}
