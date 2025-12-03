import { computed, inject, Injectable, linkedSignal, Signal, WritableSignal } from "@angular/core";
import { environment } from "../../../environments/environment";
import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { PiResponse } from "../../app.component";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { NotificationService, NotificationServiceInterface } from "../notification/notification.service";
import { catchError, lastValueFrom, throwError } from "rxjs";

export type Machineresolvers = {
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
  AUTHTYPE: string;
  TLS_VERIFY: boolean;
  START_TLS: boolean;
  LDAPURI: string;
  TLS_CA_FILE: string;
  LDAPBASE: string;
  BINDDN: string;
  BINDPW: string;
  TIMEOUT: string;
  SIZELIMIT: string;
  SEARCHFILTER: string;
  IDATTRIBUTE: string;
  IPATTRIBUTE: string;
  HOSTNAMEATTRIBUTE: string;
  NOREFERRALS: boolean;
}

export interface LdapMachineresolver extends Machineresolver {
  type: "ldap";
  data: LdapMachineresolverData;
}

export interface MachineresolverServiceInterface {
  readonly allMachineresolverTypes: string[];
  readonly machineresolvers: Signal<Machineresolver[]>;

  postMachineresolver(resolver: Machineresolver): Promise<string | null>;
  postTestMachineresolver(resolver: Machineresolver): Promise<string | null>;
  deleteMachineresolver(name: string): Promise<string | null>;
}

@Injectable({
  providedIn: "root"
})
export class MachineresolverService implements MachineresolverServiceInterface {
  readonly allMachineresolverTypes: string[] = ["hosts", "ldap"];
  readonly machineresolverBaseUrl = environment.proxyUrl + "/machineresolver/";

  readonly authService: AuthServiceInterface = inject(AuthService);
  readonly contentService: ContentServiceInterface = inject(ContentService);
  readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  readonly http: HttpClient = inject(HttpClient);

  readonly machineresolverResource = httpResource<PiResponse<Machineresolvers>>(() => {
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

  async postTestMachineresolver(resolver: Machineresolver): Promise<string | null> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to update machineresolvers.");
      return Promise.resolve("not-allowed");
    }
    const url = `${this.machineresolverBaseUrl}test`;
    const request = this.http.post<PiResponse<any>>(url, resolver.data, { headers: this.authService.getHeaders() });
    return lastValueFrom(request)
      .then(() => null)
      .catch((error) => {
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to update machineresolver. " + message);
        return "post-failed";
      });
  }

  async postMachineresolver(resolver: Machineresolver): Promise<string | null> {
    if (!this.authService.actionAllowed("mresolverwrite")) {
      this.notificationService.openSnackBar("You are not allowed to update machineresolvers.");
      return Promise.resolve("not-allowed");
    }
    const url = `${this.machineresolverBaseUrl}${resolver.resolvername}`;
    const request = this.http.post<PiResponse<any>>(url, resolver.data, { headers: this.authService.getHeaders() });

    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully updated machineresolver.`);
        this.machineresolverResource.reload();
        return null;
      })
      .catch((error) => {
        console.warn("Failed to update machineresolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to update machineresolver. " + message);
        return "post-failed";
      });
  }

  async deleteMachineresolver(name: string): Promise<string | null> {
    if (!this.authService.actionAllowed("mresolverdelete")) {
      this.notificationService.openSnackBar("You are not allowed to delete machineresolvers.");
      return Promise.resolve("not-allowed");
    }
    const request = this.http.delete<PiResponse<any>>(`${this.machineresolverBaseUrl}${name}`, {
      headers: this.authService.getHeaders()
    });
    return lastValueFrom(request)
      .then(() => {
        this.notificationService.openSnackBar(`Successfully deleted machineresolver: ${name}.`);
        this.machineresolverResource.reload();
        return null;
      })
      .catch((error) => {
        console.warn("Failed to delete machineresolver:", error);
        const message = error.error?.result?.error?.message || "";
        this.notificationService.openSnackBar("Failed to delete machineresolver. " + message);
        return "post-failed";
      });
  }
}
