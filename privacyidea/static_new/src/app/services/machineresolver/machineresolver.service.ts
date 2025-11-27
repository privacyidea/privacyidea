import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { catchError, lastValueFrom, throwError } from "rxjs";

export type MachineresolversObject = {
  [key: string]: Machineresolver;
};
export interface MachineresolverData {
  resolver: string;
  type: string;
}

export interface Machineresolver {
  resolvername: string;
  type: string;
  data: MachineresolverData;
}

export interface HostsMachineresolverData extends MachineresolverData {
  filename: string;
  type: "hosts";
}

export interface HostsMachineresolver extends Machineresolver {
  type: "hosts";
  data: HostsMachineresolverData;
}

export interface LdapMachineresolverData extends MachineresolverData {
  type: "ldap";
  data: {
    // For now, we don't know the ldap specific fields.
    type: "ldap";
  };
}

export interface LdapMachineresolver extends Machineresolver {
  type: "ldap";
  data: LdapMachineresolverData;
}

export interface MachineresolverServiceInterface {
  readonly allMachineresolverTypes: string[];

  readonly machineresolvers: Signal<Machineresolver[]>;

  createMachineresolver(resolver: Machineresolver): Promise<boolean>;
  updateMachineresolver(resolver: Machineresolver): Promise<boolean>;
  deleteMachineresolver(name: string): void;
}

@Injectable({
  providedIn: "root"
})
export class MachineresolverService implements MachineresolverServiceInterface {
  readonly allMachineresolverTypes: string[] = ["hosts", "ldap"];
  readonly machineresolverBaseUrl = environment.proxyUrl + "/machineresolver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly http: HttpClient = inject(HttpClient);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);

  readonly machineresolverResource = httpResource<PiResponse<MachineresolversObject>>(() => {
    if (!this.authService.actionAllowed("mresolverread")) {
      this.notificationService.openSnackBar("You are not allowed to read machineresolvers.");
      return undefined;
    }
    return {
      url: `${this.machineresolverBaseUrl}`,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  readonly machineresolvers = computed<Machineresolver[]>(() => {
    const res = this.machineresolverResource.value();
    return res?.result?.value ? Object.values(res.result.value) : [];
  });

  async createMachineresolver(resolver: Machineresolver): Promise<boolean> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to create machineresolvers.");
      return false;
    }
    const url = `${this.machineresolverBaseUrl}${resolver.resolvername}`;
    const body = {
      type: resolver.type,
      data: resolver.data
    };
    const request = this.http.post<PiResponse<any>>(url, body, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully created machineresolver.`);
        this.machineresolverResource.reload();
        return true;
      })
      .catch((error) => {
        console.warn("Failed to create machineresolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to create machineresolver. " + message);
        return false;
      });
  }

  async updateMachineresolver(resolver: Machineresolver): Promise<boolean> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to update machineresolvers.");
      return false;
    }
    const url = `${this.machineresolverBaseUrl}${resolver.resolvername}`;
    const request = this.http.put<PiResponse<any>>(url, resolver.data, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully updated machineresolver.`);
        this.machineresolverResource.reload();
        return true;
      })
      .catch((error) => {
        console.warn("Failed to update machineresolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to update machineresolver. " + message);
        return false;
      });
  }

  deleteMachineresolver(name: string) {
    if (!this.authService.actionAllowed("mresolverdelete")) {
      this.notificationService.openSnackBar("You are not allowed to delete machineresolvers.");
      return;
    }
    this.http
      .delete<PiResponse<any>>(`${this.machineresolverBaseUrl}${name}`, {
        headers: this.authService.getHeaders()
      })
      .pipe(
        catchError((error) => {
          console.warn("Failed to delete machineresolver:", error);
          const message = error.error?.result?.error?.message || "";
          this.notificationService.openSnackBar("Failed to delete machineresolver. " + message);
          return throwError(() => error);
        })
      )
      .subscribe({
        next: (response) => {
          console.log("Machineresolver successfully deleted:", response);
          this.machineresolverResource.reload();
          this.notificationService.openSnackBar("Successfully deleted machineresolver.");
        }
      });
  }
}
