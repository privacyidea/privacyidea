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

import { computed, effect, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { catchError, lastValueFrom, throwError } from "rxjs";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { ContainerService, ContainerServiceInterface, ContainerTemplate } from "../container/container.service";
import { environment } from "../../../environments/environment";

export interface TemplateTokenType {
  description: string;
  token_types: string[];
}

export interface TemplateTokenTypes {
  [key: string]: TemplateTokenType;
}

export interface ContainerTemplateServiceInterface {
  containerTemplateBaseUrl: string;
  emptyContainerTemplate: ContainerTemplate;
  templates: WritableSignal<ContainerTemplate[]>;
  templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined>;
  templateTokenTypes: Signal<TemplateTokenTypes>;
  templateTokenTypesResource: HttpResourceRef<PiResponse<TemplateTokenTypes, unknown> | undefined>;
  availableContainerTypes: Signal<string[]>;

  canSaveTemplate(template: ContainerTemplate): boolean;

  copyTemplate(template: ContainerTemplate, newName: string): Promise<boolean>;

  deleteTemplate(name: string): Promise<void>;

  deleteTemplates(name: string[]): Promise<void>;

  getTokenTypesForContainerType(containerType: string): string[];

  postTemplateEdits(template: ContainerTemplate): Promise<boolean>;
}

@Injectable({
  providedIn: "root"
})
export class ContainerTemplateService implements ContainerTemplateServiceInterface {
  // --- Constants & Data ---
  readonly containerTemplateBaseUrl = environment.proxyUrl + "/container/templates";
  readonly emptyContainerTemplate: ContainerTemplate = {
    container_type: "",
    default: false,
    name: "",
    template_options: {
      tokens: []
    }
  };

  // --- Services ---
  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly containerService: ContainerServiceInterface = inject(ContainerService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly http = inject(HttpClient);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  // --- Resources ---

  constructor() {
    effect(() => {
      this.notificationService.handleResourceError(this.templatesResource.error(), "container templates");
    });
    effect(() => {
      this.notificationService.handleResourceError(this.templateTokenTypesResource.error(), "template token types");
    });
  }
  readonly templatesResource = httpResource<PiResponse<{ templates: ContainerTemplate[] }>>(() => {
    if (!this.authService.actionAllowed("container_template_list")) return undefined;
    if (!this.contentService.onTokensContainersCreate() && !this.contentService.onTokensContainersTemplates())
      return undefined;

    let params: any = {};
    if (this.containerService.selectedContainerType()) {
      params = { container_type: this.containerService.selectedContainerType()!.containerType };
    }

    return {
      url: `${this.containerTemplateBaseUrl}`,
      method: "GET",
      params: params,
      headers: this.authService.getHeaders()
    };
  });

  readonly templateTokenTypesResource = httpResource<PiResponse<TemplateTokenTypes>>(() => {
    if (!this.authService.actionAllowed("container_template_list")) return undefined;
    if (!this.contentService.onTokensContainersCreate() && !this.contentService.onTokensContainersTemplates())
      return undefined;

    return {
      url: environment.proxyUrl + `/container/template/tokentypes`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  // --- Signals & Computed ---
  readonly templates: WritableSignal<ContainerTemplate[]> = linkedSignal({
    source: () => this.templatesResource.hasValue() ? this.templatesResource.value() : undefined,
    computation: (templatesResource, previous) => templatesResource?.result?.value?.templates ?? previous?.value ?? []
  });

  readonly templateTokenTypes = computed<TemplateTokenTypes>(() => {
    if (!this.templateTokenTypesResource.hasValue()) return {};
    return this.templateTokenTypesResource.value()?.result?.value ?? {};
  });

  readonly availableContainerTypes = computed(() => {
    return Object.keys(this.templateTokenTypes());
  });

  // --- Public Methods ---
  canSaveTemplate(template: ContainerTemplate): boolean {
    if (template.name.trim().length === 0) return false;
    if (!/^[a-zA-Z0-9._-]*$/.test(template.name)) return false;
    if (template.container_type.trim().length === 0) return false;
    if (template.template_options.tokens.length === 0) return false;
    return true;
  }

  copyTemplate(template: ContainerTemplate, newName: string): Promise<boolean> {
    const newTemplate: ContainerTemplate = {
      ...template,
      name: newName,
      default: false
    };
    return this.postTemplateEdits(newTemplate);
  }

  async deleteTemplate(name: string) {
    if (!this.authService.actionAllowed("container_template_delete")) {
      this.notificationService.openSnackBar("You are not allowed to delete container templates.");
      throw new Error("Permission denied");
    }

    try {
      await lastValueFrom(this._performDeleteRequest(name));
      this.templatesResource.reload();
      this.notificationService.openSnackBar("Successfully deleted template.");
    } catch (error: any) {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.openSnackBar("Failed to delete template. " + message);
      throw error;
    }
  }

  async deleteTemplates(names: string[]) {
    if (!this.authService.actionAllowed("container_template_delete")) {
      this.notificationService.openSnackBar("You are not allowed to delete container templates.");
      throw new Error("Permission denied");
    }

    try {
      for (const n of names) {
        await lastValueFrom(this._performDeleteRequest(n));
      }
      this.templatesResource.reload();
      this.notificationService.openSnackBar("Successfully deleted templates.");
    } catch (error: any) {
      const message = error.error?.result?.error?.message || "";
      this.notificationService.openSnackBar("Failed to delete templates. " + message);
      throw error;
    }
  }

  getTokenTypesForContainerType(containerType: string): string[] {
    const tokenTypeEntry = this.templateTokenTypes()[containerType];
    return tokenTypeEntry ? tokenTypeEntry.token_types : [];
  }

  async postTemplateEdits(template: ContainerTemplate): Promise<boolean> {
    const url = environment.proxyUrl + `/container/${encodeURIComponent(template.container_type)}/template/${encodeURIComponent(template.name)}`;
    try {
      await lastValueFrom(this.http.post<PiResponse<any>>(url, template, { headers: this.authService.getHeaders() }));
      this.templatesResource.reload();
      this.notificationService.openSnackBar(`Successfully saved template edits.`);
      return true;
    } catch (error: any) {
      console.warn("Failed to save template edits:", error);
      const message = error.error?.result?.error?.message || "";
      this.notificationService.openSnackBar("Failed to save template edits. " + message);
      return false;
    }
  }

  // --- Private Methods ---
  private _performDeleteRequest(name: string) {
    return this.http
      .delete<PiResponse<any>>(`${environment.proxyUrl}/container/template/${encodeURIComponent(name)}`, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        catchError((error) => {
          console.warn("Failed to delete template:", error);
          return throwError(() => error);
        })
      );
  }
}
