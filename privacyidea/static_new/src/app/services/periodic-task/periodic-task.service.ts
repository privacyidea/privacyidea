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

import { HttpClient, HttpResourceRef, httpResource } from "@angular/common/http";
import { Injectable, WritableSignal, effect, inject, signal, untracked } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { SimpleConfirmationDialogComponent } from "@components/shared/dialog/confirmation-dialog/confirmation-dialog.component";
import { environment } from "@env/environment";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { DialogService, DialogServiceInterface } from "@services/dialog/dialog.service";
import { NotificationService } from "@services/notification/notification.service";
import { Observable, catchError, forkJoin, lastValueFrom, of, throwError } from "rxjs";

export interface PeriodicTask {
  id: number | null;
  name: string;
  active: boolean;
  interval: string;
  nodes: string[];
  taskmodule: string;
  retry_if_failed: boolean;
  last_update: string;
  ordering: number;
  options: Record<string, string>;
  last_runs: Record<string, string>;
}

export const EMPTY_PERIODIC_TASK: PeriodicTask = {
  id: null,
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

export interface PeriodicTaskOption {
  name: string;
  description: string;
  type: string;
  required?: boolean;
  value?: string;
}

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
  enablePeriodicTask(taskId: number): Promise<PiResponse<number, never> | undefined>;
  disablePeriodicTask(taskId: number): Promise<PiResponse<number, never> | undefined>;
  deletePeriodicTask(taskId: number): Observable<PiResponse<number, never>>;
  deleteWithConfirmDialog(task: PeriodicTask): Promise<PiResponse<number, never> | undefined>;
  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, never> | undefined>;
  fetchAllModuleOptions(): void;
}

@Injectable()
export class PeriodicTaskService implements PeriodicTaskServiceInterface {
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  private readonly dialogService: DialogServiceInterface = inject(DialogService);
  private readonly http: HttpClient = inject(HttpClient);
  private readonly notificationService = inject(NotificationService);

  private periodicTaskBaseUrl = environment.proxyUrl + "/periodictask/";

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.periodicTasksResource.error(), "periodic tasks");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.periodicTaskModuleResource.error(), "periodic task modules");
    });
    effect(() => {
      const modules = this.periodicTaskModuleResource.value()?.result?.value;
      if (!modules?.length) return;
      untracked(() => this.fetchAllModuleOptions());
    });
  }

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
    if (!this.contentService.onConfigurationPeriodicTasks()) {
      return undefined;
    }
    return {
      url: this.periodicTaskBaseUrl + "taskmodules/",
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  enablePeriodicTask(taskId: number) {
    const headers = this.authService.getHeaders();
    return lastValueFrom(
      this.http.post<PiResponse<number, never>>(this.periodicTaskBaseUrl + "enable/" + encodeURIComponent(taskId), {}, { headers: headers }).pipe(
        catchError(() => {
          this.periodicTasksResource.reload();
          this.notificationService.error("Failed to enable periodic task!");
          return of(undefined);
        })
      )
    );
  }

  disablePeriodicTask(taskId: number) {
    const headers = this.authService.getHeaders();
    const response$ = this.http
      .post<PiResponse<number, never>>(this.periodicTaskBaseUrl + "disable/" + encodeURIComponent(taskId), {}, { headers: headers })
      .pipe(
        catchError(() => {
          this.periodicTasksResource.reload();
          this.notificationService.error("Failed to disable periodic task!");
          return of(undefined);
        })
      );
    return lastValueFrom(response$);
  }

  deletePeriodicTask(taskId: number): Observable<PiResponse<number, never>> {
    const headers = this.authService.getHeaders();

    return this.http
      .delete<PiResponse<number, never>>(this.periodicTaskBaseUrl + encodeURIComponent(taskId), { headers })
      .pipe(
        catchError((error) => {
          console.error("Failed to delete periodic task.", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.error("Failed to delete periodic task. " + message);
          return throwError(() => error);
        })
      );
  }

  async deleteWithConfirmDialog(task: PeriodicTask): Promise<PiResponse<number, never> | undefined> {
    const confirmation = await lastValueFrom(
      this.dialogService
        .openDialog({
          component: SimpleConfirmationDialogComponent,
          data: {
            title: $localize`Delete Periodic Task`,
            items: [task.name],
            itemType: $localize`periodic task`,
            confirmAction: { label: $localize`Delete`, value: true, type: "destruct" }
          }
        })
        .afterClosed()
    );
    if (!confirmation) {
      return;
    }
    try {
      if (task.id == null) {
        this.notificationService.error("Failed to delete periodic task: Missing ID.");
        return;
      }
      const response = await lastValueFrom(this.deletePeriodicTask(task.id));
      if (response?.result?.value !== undefined) {
        this.notificationService.success("Successfully deleted periodic task.");
      }
      return response;
    } catch {
      // error already handled in deletePeriodicTask
    }
    return undefined;
  }

  convertNodesArrayToString(nodes: string[] | string | null | undefined): string {
    if (Array.isArray(nodes)) {
      return nodes.join(",");
    } else if (typeof nodes === "string") {
      return nodes;
    }
    return "";
  }

  savePeriodicTask(task: PeriodicTask): Observable<PiResponse<number, never> | undefined> {
    const headers = this.authService.getHeaders();
    const { id, ...rest } = task;
    const params = {
      ...rest,
      nodes: this.convertNodesArrayToString(task.nodes),
      ...(id != null ? { id } : {})
    };
    return this.http.post<PiResponse<number, never>>(this.periodicTaskBaseUrl, params, { headers }).pipe(
      catchError((error) => {
        console.error("Failed to save periodic task.", error.error);
        const message = error.error.result?.error?.message || "";
        this.notificationService.error("Failed to save periodic task. " + message);
        return of(undefined);
      })
    );
  }

  moduleOptions = signal<Record<string, Record<string, PeriodicTaskOption>>>({});

  fetchAllModuleOptions() {
    const modules: string[] = this.periodicTaskModuleResource.value()?.result?.value ?? PERIODIC_TASK_MODULES;
    const alreadyLoaded = Object.keys(this.moduleOptions());
    const missing = modules.filter((m) => !alreadyLoaded.includes(m));
    if (!missing.length) return;

    const requests = missing.map((module) =>
      this.http.get<PiResponse<Record<string, PeriodicTaskOption>>>(
        this.periodicTaskBaseUrl + "options/" + encodeURIComponent(module),
        { headers: this.authService.getHeaders() }
      )
    );

    forkJoin(requests).subscribe({
      next: (responses) => {
        const newOptions: Record<string, Record<string, PeriodicTaskOption>> = {};
        responses.forEach((response, idx) => {
          const options = response.result?.value ?? {};
          Object.keys(options).forEach((key) => {
            options[key].name = key;
          });
          newOptions[missing[idx]] = options;
        });
        this.moduleOptions.update((existing) => ({ ...existing, ...newOptions }));
      },
      error: () => {
        this.notificationService.error("Failed to fetch module options.");
      }
    });
  }
}
