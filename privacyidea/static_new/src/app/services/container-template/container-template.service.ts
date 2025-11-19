import { computed, effect, inject, Injectable, linkedSignal, signal, WritableSignal } from "@angular/core";
import { HttpClient, httpResource } from "@angular/common/http";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { ROUTE_PATHS } from "../../route_paths";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { deepCopy } from "../../utils/deep-copy.utils";
import { catchError, throwError } from "rxjs";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { ContainerTemplate } from "../container/container.service";
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
  http = inject(HttpClient);
  containerTemplateBaseUrl = environment.proxyUrl + "/container/templates";
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
    return {
      url: `${this.containerTemplateBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  templates: WritableSignal<ContainerTemplate[]> = linkedSignal({
    source: this.templatesResource.value,
    computation: (templatesResource, previous) => templatesResource?.result?.value?.templates ?? previous?.value ?? []
  });

  templateTokentypesResource = httpResource<PiResponse<TemplateTokenTypes>>(() => {
    // if (
    //   (this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_CREATE &&
    //     this.contentService.routeUrl() !== ROUTE_PATHS.TOKENS_CONTAINERS_TEMPLATES) ||
    //   !this.authService.actionAllowed("container_template_list")
    // ) {
    //   return undefined;
    // }
    return {
      url: environment.proxyUrl + `/container/template/tokentypes`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

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

  isEditMode: WritableSignal<boolean> = linkedSignal({
    source: () => ({
      routeUrl: this.contentService.routeUrl(),
      selectedTemplateOriginal: this._selectedTemplateOriginal(),
      templatesResource: this.templatesResource.value()
    }),
    computation: (source, previous) => {
      if (
        source.templatesResource !== previous?.source.templatesResource ||
        source.selectedTemplateOriginal !== previous?.source.selectedTemplateOriginal ||
        !source.routeUrl.includes("templates")
      ) {
        return false;
      }
      return previous?.value ?? false;
    }
  });

  selectedTemplate = linkedSignal({
    source: () => this._selectedTemplateOriginal(),
    computation: (selectedTemplateOriginal) => deepCopy(selectedTemplateOriginal)
  });
  private _selectedTemplateOriginal = signal<ContainerTemplate | null>(null);

  isTemplateEdited = computed(() => {
    return JSON.stringify(this.selectedTemplate()) !== JSON.stringify(this._selectedTemplateOriginal());
  });

  selectTemplateByName(name: string) {
    const template = this.templates()?.find((p) => p.name === name);
    if (template) {
      this._selectedTemplateOriginal.set(deepCopy(template));
    }
  }
  selectTemplate(template: ContainerTemplate) {
    this._selectedTemplateOriginal.set(deepCopy(template));
  }

  initializeNewTemplate() {
    this._selectedTemplateOriginal.set(deepCopy(ContainerTemplateService.emptyContainerTemplate));
    this.isEditMode.set(true);
  }

  static readonly emptyContainerTemplate: ContainerTemplate = {
    container_type: "",
    default: false,
    name: "",
    template_options: {
      options: undefined,
      tokens: []
    }
  };

  deselectNewTemplate() {
    if (this._selectedTemplateOriginal()?.name === ContainerTemplateService.emptyContainerTemplate.name) {
      this._selectedTemplateOriginal.set(null);
    }
  }

  deselectTemplate(name: string) {
    if (this._selectedTemplateOriginal()?.name === name) {
      this._selectedTemplateOriginal.set(null);
    }
  }

  updateSelectedTemplate(template: Partial<ContainerTemplate>) {
    const newTemplate = { ...this.selectedTemplate(), ...template } as ContainerTemplate;
    this.selectedTemplate.set(deepCopy(newTemplate));
  }

  saveTemplateEditsAsNew() {
    const template = this.selectedTemplate();
    if (template) {
      this.http
        .post<PiResponse<ContainerTemplate>>(this.containerTemplateBaseUrl, template)
        .pipe(
          catchError((error) => {
            console.error("Failed to save new template:", error);
            const message = error.error?.result?.error?.message || "";
            this.notificationService.openSnackBar("Failed to save new template. " + message);
            return throwError(() => error);
          })
        )
        .subscribe();
    }
  }

  saveTemplateEdits() {
    const template = this.selectedTemplate();
    if (!template) return;
    this.http
      .put<PiResponse<ContainerTemplate>>(this.containerTemplateBaseUrl + template.name, template)
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
          console.log("Template edits successfully saved:", response);
          this.templatesResource.reload();
          this.notificationService.openSnackBar("Successfully saved template edits.");
        }
      });
  }

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

  cancelEditMode() {
    this.selectedTemplate.set(deepCopy(this._selectedTemplateOriginal()));
    this.isEditMode.set(false);
  }

  templateIsSelected(templateNameOriginal: string = ""): boolean {
    const selectedTemplate = this._selectedTemplateOriginal();
    return selectedTemplate !== null && selectedTemplate.name === templateNameOriginal;
  }

  isEditingTemplate(name: string): boolean {
    return this.isEditMode() && this._selectedTemplateOriginal()?.name === name;
  }

  setDefaultTemplate(toggleTemplate: ContainerTemplate, isDefault: boolean) {
    const url =
      environment.proxyUrl + `/container/${toggleTemplate.container_type}/template/${toggleTemplate.name}/setdefault`;
    this.http
      .post<PiResponse<any>>(url, { ...toggleTemplate, default: isDefault }, { headers: this.authService.getHeaders() })
      .pipe(
        catchError((error) => {
          console.error("Failed to set default template:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to set default template. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: (response) => {
          console.log("Default template successfully set:", response);
          this.templatesResource.reload();
          this.notificationService.openSnackBar(`Successfully set "${toggleTemplate.name}" as default template.`);
        }
      });
  }
}
