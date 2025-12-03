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
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { inject, Injectable, signal, WritableSignal } from "@angular/core";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { ROUTE_PATHS } from "../../route_paths";
import { forkJoin, lastValueFrom, Observable, of, throwError } from "rxjs";
import { catchError } from "rxjs/operators";
import { NotificationService } from "../notification/notification.service";
import { ConfirmationDialogComponent } from "../../components/shared/confirmation-dialog/confirmation-dialog.component";
import { BulkResult } from "../token/token.service";

export type PeriodicTask = {
  "id": string;
  "name": string;
  "active": boolean;
  "interval": string;
  "nodes": string[];
  "taskmodule": string;
  "retry_if_failed": boolean;
  "last_update": string;
  "ordering": number;
  "options": Record<string, any>;
  "last_runs": Record<string, any>
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
  deleteWithConfirmDialog(task: PeriodicTask, dialog: any, afterDelete?: () => void): void;
  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, any> | undefined>;
  fetchAllModuleOptions(): void;
}

@Injectable({
  providedIn: "root"
})
export class PeriodicTaskService implements PeriodicTaskServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly http: HttpClient = inject(HttpClient);
  private readonly notificationService = inject(NotificationService);

  private periodicTaskBaseUrl = environment.proxyUrl + "/periodictask/";

  periodicTasksResource = httpResource<PiResponse<PeriodicTask[]>>(() => {
    if (this.contentService.routeUrl() !== ROUTE_PATHS.CONFIGURATION_PERIODIC_TASKS || !this.authService.actionAllowed("periodictask_read")) {
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
    return lastValueFrom(this.http.post(
      this.periodicTaskBaseUrl + "enable/" + taskId,
      {},
      { headers: headers }
    ).pipe(
      catchError((error) => {
        console.log("Failed to enable periodic task:", error);
        this.periodicTasksResource.reload();
        this.notificationService.openSnackBar("Failed to enable periodic task!");
        return of(undefined);
      })
    ));
  }

  disablePeriodicTask(taskId: string) {
    const headers = this.authService.getHeaders();
    const response$ = this.http.post(
      this.periodicTaskBaseUrl + "disable/" + taskId,
      {},
      { headers: headers }
    ).pipe(
      catchError((error) => {
        console.log("Failed to disable periodic task:", error);
        this.periodicTasksResource.reload();
        this.notificationService.openSnackBar("Failed to disable periodic task!");
        return of(undefined);
      })
    );
    return lastValueFrom(response$);
  }

  deletePeriodicTask(taskId: string): Observable<PiResponse<number, any>> {
    const headers = this.authService.getHeaders();

    return this.http.delete<PiResponse<number, any>>(
      this.periodicTaskBaseUrl + taskId,
      { headers }
    ).pipe(
      catchError((error) => {
        console.error("Failed to delete periodic task.", error);
        const message = error.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete periodic task. " + message);
        return throwError(() => error);
      })
    );
  }

  deleteWithConfirmDialog(task: PeriodicTask, dialog: any, afterDelete?: () => void) {
    dialog
      .open(ConfirmationDialogComponent, {
        data: {
          serialList: [task.name],
          title: "Delete Periodic Task",
          type: "periodicTask",
          action: "delete",
          numberOfTokens: 1
        }
      })
      .afterClosed()
      .subscribe({
        next: (result: any) => {
          if (result) {
            this.deletePeriodicTask(task.id).subscribe({
              next: (response: PiResponse<number, any>) => {
                this.notificationService.openSnackBar("Successfully deleted periodic task.");
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

  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, any> | undefined> {
    const headers = this.authService.getHeaders();
    let params = { ...task } as any;
    if (!params.id) {
      delete params.id;
    }
    params.nodes = Array.isArray(params.nodes) ? params.nodes.join(",") : params.nodes;
    return this.http.post<PiResponse<number, any>>(
      this.periodicTaskBaseUrl,
      params,
      { headers }
    ).pipe(
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
    const requests = PERIODIC_TASK_MODULES.map(module =>
      this.http.get<PiResponse<Record<string, PeriodicTaskOption>>>(
        this.periodicTaskBaseUrl + "options/" + module,
        { headers: this.authService.getHeaders() }
      )
    );

    forkJoin(requests).subscribe({
      next: (responses) => {
        const optionsDict: Record<string, Record<string, PeriodicTaskOption>> = {};
        responses.forEach((response, idx) => {
          let options = response.result?.value ?? {};
          Object.keys(options).forEach(key => {
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
