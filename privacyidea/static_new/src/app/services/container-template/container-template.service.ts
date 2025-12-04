import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { catchError, last, lastValueFrom, shareReplay, throwError } from "rxjs";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { ContainerService, ContainerServiceInterface, ContainerTemplate } from "../container/container.service";
import { environment } from "../../../environments/environment";

export interface ContainerTemplateServiceInterface {
  availableContainerTypes: Signal<string[]>;
  canSaveTemplate(template: ContainerTemplate): boolean;
  containerTemplateBaseUrl: string;
  deleteTemplate(name: string): void;
  emptyContainerTemplate: ContainerTemplate;
  getTokenTypesForContainerType(containerType: string): string[];
  postTemplateEdits(template: ContainerTemplate): Promise<boolean>;
  templates: WritableSignal<ContainerTemplate[]>;
  templatesResource: HttpResourceRef<PiResponse<{ templates: ContainerTemplate[] }, unknown> | undefined>;
  templateTokenTypes: Signal<TemplateTokenTypes>;
  templateTokenTypesResource: HttpResourceRef<PiResponse<TemplateTokenTypes, unknown> | undefined>;
}

export interface TemplateTokenTypes {
  [key: string]: TemplateTokenType;
}

export interface TemplateTokenType {
  description: string;
  token_types: string[];
}

@Injectable({
  providedIn: "root"
})
export class ContainerTemplateService implements ContainerTemplateServiceInterface {
  readonly emptyContainerTemplate: ContainerTemplate = {
    container_type: "",
    default: false,
    name: "",
    template_options: {
      options: undefined,
      tokens: []
    }
  };

  authService: AuthServiceInterface = inject(AuthService);
  availableContainerTypes = computed(() => {
    return Object.keys(this.templateTokenTypes());
  });
  containerService: ContainerServiceInterface = inject(ContainerService);
  containerTemplateBaseUrl = environment.proxyUrl + "/container/templates";
  contentService: ContentServiceInterface = inject(ContentService);
  http = inject(HttpClient);

  notificationService: NotificationServiceInterface = inject(NotificationService);
  templatesResource = httpResource<PiResponse<{ templates: ContainerTemplate[] }>>(() => {
    // Do not load templates if the action is not allowed.
    if (!this.authService.actionAllowed("container_template_list")) {
      return undefined;
    }
    // Only load templates on the container create route.
    if (!this.contentService.onTokensContainersCreate() && !this.contentService.onTokensContainersTemplates()) {
      return undefined;
    }

    let params: any = {};
    if (this.containerService.selectedContainerType()) {
      params = {
        container_type: this.containerService.selectedContainerType()!.containerType
      };
    }

    return {
      url: `${this.containerTemplateBaseUrl}`,
      method: "GET",
      params: params,
      headers: this.authService.getHeaders()
    };
  });

  templates: WritableSignal<ContainerTemplate[]> = linkedSignal({
    source: () => this.templatesResource.value(),
    computation: (templatesResource, previous) => templatesResource?.result?.value?.templates ?? previous?.value ?? []
  });

  templateTokenTypes = computed<TemplateTokenTypes>(() => {
    return this.templateTokenTypesResource.value()?.result?.value ?? {};
  });

  templateTokenTypesResource = httpResource<PiResponse<TemplateTokenTypes>>(() => {
    if (!this.authService.actionAllowed("container_template_list")) {
      return undefined;
    }
    if (!this.contentService.onTokensContainersCreate() && !this.contentService.onTokensContainersTemplates()) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + `/container/template/tokentypes`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  canSaveTemplate(template: ContainerTemplate): boolean {
    if (template.name.trim().length === 0) {
      return false;
    }
    if (template.container_type.trim().length === 0) {
      return false;
    }
    if (template.template_options.tokens.length === 0) {
      return false;
    }
    return true;
  }

  deleteTemplate(name: string) {
    if (!this.authService.actionAllowed("container_template_delete")) {
      this.notificationService.openSnackBar("You are not allowed to delete container templates.");
      return;
    }
    this.http
      .delete<PiResponse<any>>(`${environment.proxyUrl}/container/template/${name}`, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        catchError((error) => {
          console.warn("Failed to delete template:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete template. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: () => {
          this.templatesResource.reload();
          this.notificationService.openSnackBar("Successfully deleted template.");
        }
      });
  }

  getTokenTypesForContainerType(containerType: string): string[] {
    const tokenTypeEntry = this.templateTokenTypes()[containerType];
    return tokenTypeEntry ? tokenTypeEntry.token_types : [];
  }

  async postTemplateEdits(template: ContainerTemplate): Promise<boolean> {
    const url = environment.proxyUrl + `/container/${template.container_type}/template/${template.name}`;
    const request = this.http
      .post<PiResponse<any>>(url, template, { headers: this.authService.getHeaders() })
      .pipe(shareReplay(1));
    request
      .pipe(
        catchError((error) => {
          console.warn("Failed to save template edits:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to save template edits. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: () => {
          this.templatesResource.reload();
          this.notificationService.openSnackBar(`Successfully saved template edits.`);
        }
      });
    return lastValueFrom(request.pipe(last()))
      .then(() => true)
      .catch(() => false);
  }
}
