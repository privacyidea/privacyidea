import { computed, effect, inject, Injectable, linkedSignal, WritableSignal } from "@angular/core";
import { HttpClient, httpResource } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { catchError, last, lastValueFrom, throwError } from "rxjs";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { ContainerService, ContainerServiceInterface, ContainerTemplate } from "../container/container.service";
import { environment } from "../../../environments/environment";

export interface ContainerTemplateServiceInterface {
  // Add method and property signatures here
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
  canSaveTemplate(): boolean {
    // Simplified for now
    // TODO: Add more validation checks
    return true;
  }
  http = inject(HttpClient);
  containerTemplateBaseUrl = environment.proxyUrl + "/container/templates";
  containerService: ContainerServiceInterface = inject(ContainerService);
  contentService: ContentServiceInterface = inject(ContentService);
  authService: AuthServiceInterface = inject(AuthService);
  notificationService: NotificationServiceInterface = inject(NotificationService);

  constructor() {
    effect(() => {
      console.log("availableContainerTypes changed:", this.availableContainerTypes());
    });
    effect(() => {
      console.log("templateTokentypesResource changed:", this.templateTokentypesResource.value());
    });
  }

  templatesResource = httpResource<PiResponse<{ templates: ContainerTemplate[] }>>(() => {
    if (
      (this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_CREATE &&
        this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES) ||
      !this.authService.actionAllowed("container_template_list")
    ) {
      return undefined;
    }
    let params = {};
    if (this.containerService.selectedContainerType()) {
      params = {
        container_type: this.containerService.selectedContainerType()?.containerType
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
    source: this.templatesResource.value,
    computation: (templatesResource, previous) => templatesResource?.result?.value?.templates ?? previous?.value ?? []
  });

  templateTokentypesResource = httpResource<PiResponse<TemplateTokenTypes>>(() => ({
    url: environment.proxyUrl + `/container/template/tokentypes`,
    method: "GET",
    headers: this.authService.getHeaders()
  }));

  templateTokenTypes = computed<TemplateTokenTypes>(() => {
    return this.templateTokentypesResource.value()?.result?.value ?? {};
  });

  availableContainerTypes = computed(() => {
    return Object.keys(this.templateTokenTypes());
  });

  getTokenTypesForContainerType(containerType: string): string[] {
    const tokenTypeEntry = this.templateTokenTypes()[containerType];
    return tokenTypeEntry ? tokenTypeEntry.token_types : [];
  }

  readonly emptyContainerTemplate: ContainerTemplate = {
    container_type: "",
    default: false,
    name: "",
    template_options: {
      options: undefined,
      tokens: []
    }
  };

  // postAddNewTemplate(newTemplate: ContainerTemplate) {
  //   if (!newTemplate) {
  //     console.error("No template provided to postAddNewTemplate.");
  //     return;
  //   }
  //   this.http
  //     .post<PiResponse<ContainerTemplate>>(this.containerTemplateBaseUrl, newTemplate)
  //     .pipe(
  //       catchError((error) => {
  //         console.error("Failed to save new template:", error);
  //         const message = error.error?.result?.error?.message || "";
  //         this.notificationService.openSnackBar("Failed to save new template. " + message);
  //         return throwError(() => error);
  //       })
  //     )
  //     .subscribe();
  // }

  deleteTemplate(name: string) {
    this.http
      .delete<PiResponse<any>>(this.containerTemplateBaseUrl + name)
      .pipe(
        catchError((error) => {
          console.error("Failed to delete template:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete template. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: (response) => {
          console.log("Template successfully deleted:", response);
          this.templatesResource.reload();
          this.notificationService.openSnackBar("Successfully deleted template.");
        }
      });
  }

  async postTemplateEdits(template: ContainerTemplate): Promise<boolean> {
    console.log("Posting template edits for template:", template);
    const url = environment.proxyUrl + `/container/${template.container_type}/template/${template.name}`;
    const request$ = this.http.post<PiResponse<any>>(url, template, { headers: this.authService.getHeaders() });
    request$
      .pipe(
        catchError((error) => {
          console.error("Failed to save template edits:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to save template edits. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: (response) => {
          console.log("Default template edits successfully saved:", response);
          this.templatesResource.reload();
          this.notificationService.openSnackBar(`Successfully saved template edits.`);
        }
      });
    return lastValueFrom(request$.pipe(last()))
      .then(() => true)
      .catch(() => false);
  }
}
