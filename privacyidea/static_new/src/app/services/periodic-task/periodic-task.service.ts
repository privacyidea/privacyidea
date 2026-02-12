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

import { HttpResourceRef, HttpClient, httpResource } from "@angular/common/http";
import { WritableSignal, Injectable, inject, signal } from "@angular/core";
import { Observable, lastValueFrom, catchError, of, throwError, forkJoin } from "rxjs";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { SimpleConfirmationDialogComponent } from "../../components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthServiceInterface, AuthService } from "../auth/auth.service";
import { ContentServiceInterface, ContentService } from "../content/content.service";
import { DialogReturnData, DialogService, DialogServiceInterface } from "../dialog/dialog.service";
import { NotificationService } from "../notification/notification.service";

export type PeriodicTask = {
  id: string;
  name: string;
  active: boolean;
  interval: string;
  nodes: string[];
  taskmodule: string;
  retry_if_failed: boolean;
  last_update: string;
  ordering: number;
  options: Record<string, any>;
  last_runs: Record<string, any>;
};

export const EMPTY_PERIODIC_TASK: PeriodicTask = {
  id: "",
  name: "",
  active: true,
  interval: "",
  nodes: [],
  taskmodule: "SimpleStats",
  retry_if_failed: false,
  last_update: "",
  ordering: 0,
  options: {},
  last_runs: {}
};

export const TASK_KEY_MAPPING: Record<string, string> = {
  id: "ID",
  name: "Name",
  active: "Active",
  interval: "Interval",
  nodes: "Nodes",
  taskmodule: "Task Module",
  retry_if_failed: "Retry If Failed",
  last_update: "Last Update",
  ordering: "Ordering",
  options: "Options",
  last_runs: "Last Runs"
};

export type PeriodicTaskOption = {
  name: string;
  description: string;
  type: string;
  required?: boolean;
  value?: string;
};

export const EMPTY_PERIODIC_TASK_OPTION: PeriodicTaskOption = {
  name: "",
  description: "",
  type: "",
  value: ""
};

export type PeriodicTaskModule = "SimpleStats" | "EventCounter";
export const PERIODIC_TASK_MODULES: PeriodicTaskModule[] = ["SimpleStats", "EventCounter"];
export const PERIODIC_TASK_MODULE_MAPPING: Record<PeriodicTaskModule, string> = {
  SimpleStats: "Simple Statistics",
  EventCounter: "Event Counter"
};

export interface PeriodicTaskServiceInterface {
  periodicTasksResource: HttpResourceRef<PiResponse<PeriodicTask[]> | undefined>;
  periodicTaskModuleResource: HttpResourceRef<PiResponse<PeriodicTaskModule[]> | undefined>;
  moduleOptions: WritableSignal<Record<string, Record<string, PeriodicTaskOption>>>;
  enablePeriodicTask(taskId: string): Promise<any>;
  disablePeriodicTask(taskId: string): Promise<any>;
  deletePeriodicTask(taskId: string): Observable<PiResponse<number, any>>;
  deleteWithConfirmDialog(task: PeriodicTask): Promise<PiResponse<number, any> | undefined>;
  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, any> | undefined>;
  fetchAllModuleOptions(): void;
}

@Injectable({
  providedIn: "root"
})
export class PeriodicTaskService implements PeriodicTaskServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly http: HttpClient = inject(HttpClient);
  private readonly notificationService = inject(NotificationService);

  private periodicTaskBaseUrl = environment.proxyUrl + "/periodictask/";

  periodicTasksResource = httpResource<PiResponse<PeriodicTask[]>>(() => {
    if (
      this.contentService.routeUrl() !== ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS ||
      !this.authService.actionAllowed("periodictask_read")
    ) {
      return undefined;
    }
    return {
      url: this.periodicTaskBaseUrl,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  periodicTaskModuleResource = httpResource<PiResponse<PeriodicTaskModule[]>>(() => {
    if (this.contentService.routeUrl() !== ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS) {
      return undefined;
    }
    return {
      url: this.periodicTaskBaseUrl + "taskmodules/",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  enablePeriodicTask(taskId: string) {
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post(this.periodicTaskBaseUrl + "enable/" + taskId, {}, { headers: headers }).pipe(
        catchError((error) => {
          this.periodicTasksResource.reload();
          this.notificationService.openSnackBar("Failed to enable periodic task!");
          return of(undefined);
        })
      )
    );
  }

  disablePeriodicTask(taskId: string) {
    const headers = this.authService.getHeaders();
    const response$ = this.http.post(this.periodicTaskBaseUrl + "disable/" + taskId, {}, { headers: headers }).pipe(
      catchError((error) => {
        this.periodicTasksResource.reload();
        this.notificationService.openSnackBar("Failed to disable periodic task!");
        return of(undefined);
      })
    );
    return lastValueFrom(response$);
  }

  deletePeriodicTask(taskId: string): Observable<PiResponse<number, any>> {
    const headers = this.authService.getHeaders();

    return this.http.delete<PiResponse<number, any>>(this.periodicTaskBaseUrl + taskId, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to delete periodic task.", error);
        const message = error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete periodic task. " + message);
        return throwError(() => error);
      })
    );
  }

  async deleteWithConfirmDialog(task: PeriodicTask): Promise<PiResponse<number, any> | undefined> {
    const confirmation = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Periodic Task`,
            items: [task.name],
            itemType: $localize`periodic task`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" },
            cancelAction: { label: $localize`Cancel`, value: false, type: "cancel" }
          }
        })
        .afterClosed()
    );
    if (!confirmation) {
      return;
    }
    try {
      const response = await lastValueFrom(this.deletePeriodicTask(task.id));
      if (response?.result?.value !== undefined) {
        this.notificationService.openSnackBar("Successfully deleted periodic task.");
      }
      return response;
    } catch (error) {
      // error already handled in deletePeriodicTask
    }
    return undefined;
  }

  convertNodesArrayToString(nodes: any): string {
    // Ensure params.nodes is a comma-separated string.
    if (Array.isArray(nodes)) {
      nodes = nodes.join(",");
    } else if (typeof nodes === "string") {
      // already a string, do nothing
    } else if (nodes == null) {
      nodes = "";
    } else {
      // Unexpected type, log a warning and set to empty string
      console.warn("Unexpected type for params.nodes in savePeriodicTask:", nodes);
      nodes = "";
    }
    return nodes;
  }

  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, any> | undefined> {
    const headers = this.authService.getHeaders();
    let params = { ...task } as any;
    if (!params.id) {
      delete params.id;
    }
    params.nodes = this.convertNodesArrayToString(params.nodes);
    return this.http.post<PiResponse<number, any>>(this.periodicTaskBaseUrl, params, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to save periodic task.", error.error);
        const message = error.error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to save periodic task. " + message);
        return of(undefined);
      })
    );
  }

  moduleOptions = signal<Record<string, Record<string, PeriodicTaskOption>>>({});

  fetchAllModuleOptions() {
    const requests = PERIODIC_TASK_MODULES.map((module) =>
      this.http.get<PiResponse<Record<string, PeriodicTaskOption>>>(this.periodicTaskBaseUrl + "options/" + module, {
        headers: this.authService.getHeaders()
      })
    );

    forkJoin(requests).subscribe({
      next: (responses) => {
        const optionsDict: Record<string, Record<string, PeriodicTaskOption>> = {};
        responses.forEach((response, idx) => {
          let options = response.result?.value ?? {};
          Object.keys(options).forEach((key) => {
            options[key].name = key;
          });
          optionsDict[PERIODIC_TASK_MODULES[idx]] = options;
        });
        this.moduleOptions.set(optionsDict);
      },
      error: () => {
        this.notificationService.openSnackBar("Failed to fetch module options.");
      }
    });
  }
}
