import { HttpClient, httpResource, HttpResourceRef } from "@angular/common/http";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService } from "../auth/auth.service";
import { computed, effect, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { catchError, Observable, throwError } from "rxjs";

type ResolverType = "ldapresolver" | "sqlresolver" | "passwdresolver" | "scimresolver";

export interface ResolverData {}

export type Resolvers = { [key: string]: Resolver };

export interface Resolver {
  censor_keys: string[];
  data: ResolverData;
  resolvername: string;
  type: ResolverType;
}

export interface LDAPResolverData extends ResolverData {
  ldapuri: string;
  ldapbase: string;
  authtype: string;
  binddn: string;
  bindpw: string;
  timeout: number;
  cache_timeout: number;
  sizelimit: number;
  loginnameattribute: string;
  ldapsearchfilter: string;
  ldapfilter: string;
  multivalueattributes: string;
  userinfo: string;
  uidtype: string;
  noreferrals: boolean;
  noschemas: boolean;
  editable: boolean;
  start_tls: boolean;
  tls_verify: boolean;
  tls_version: string;
}

export interface SQLResolverDara extends ResolverData {
  database: string;
  driver: string;
  server: string;
  port: number;
  user: string;
  password: string;
  table: string;
  map: string;
}

export interface PasswdResolverData extends ResolverData {
  filename: string;
}

export interface SCIMResolverData extends ResolverData {
  scimurl: string;
  user: string;
  password: string;
  verifyssl: boolean;
  timeout: number;
  cache_timeout: number;
  loginnameattribute: string;
  userinfo: string;
  editable: boolean;
}

export interface ResolverServiceInterface {
  selectedResolverName: WritableSignal<string>;
  postResolverTest(): Observable<any>;
  postResolver(resolverName: string, data: any): Observable<any>;
  deleteResolver(resolverName: string): Observable<any>;
}

@Injectable({
  providedIn: "root"
})
export class ResolverService implements ResolverServiceInterface {
  readonly resolverBaseUrl = environment.proxyUrl + "/resolver/";
  private readonly authService = inject(AuthService);
  private readonly http: HttpClient = inject(HttpClient);

  selectedResolverName = signal<string>("");

  postResolverTest() {
    return this.http.post(this.resolverBaseUrl + "test", {}, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error("Error during resolver test:", error);
        return throwError(() => error);
      })
    );
  }
  resolversResource = httpResource<PiResponse<Resolvers>>({
    url: this.resolverBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  });

  resolvers = computed<Resolver[]>(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    return resolvers ? Object.values(resolvers) : [];
  });

  resolverOptions = computed(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    return resolvers ? Object.keys(resolvers) : [];
  });
  selectedResolverResource = httpResource<PiResponse<any>>(() => {
    const resolverName = this.selectedResolverName();
    if (resolverName === "") {
      return undefined;
    }
    return {
      url: this.resolverBaseUrl + resolverName,
      method: "GET",
      headers: this.authService.getHeaders()
    };
  });

  postResolver(resolverName: string, data: any) {
    return this.http.post(this.resolverBaseUrl + resolverName, data, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error(`Error during posting resolver ${resolverName}:`, error);
        return throwError(() => error);
      })
    );
  }

  deleteResolver(resolverName: string) {
    return this.http.delete(this.resolverBaseUrl + resolverName, { headers: this.authService.getHeaders() }).pipe(
      catchError((error) => {
        console.error(`Error during deleting resolver ${resolverName}:`, error);
        return throwError(() => error);
      })
    );
  }
}
