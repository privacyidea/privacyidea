import { HttpErrorResponse, httpResource, HttpResourceRef } from "@angular/common/http";
import {
  computed,
  effect,
  inject,
  Injectable,
  Signal,
  signal,
  WritableSignal
} from "@angular/core";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { LocalService, LocalServiceInterface } from "../local/local.service";
import {
  NotificationService,
  NotificationServiceInterface
} from "../notification/notification.service";
import { ContentService, ContentServiceInterface } from "../content/content.service";
import { ROUTE_PATHS } from "../../app.routes";

export type Realms = Map<string, Realm>;

export interface Realm {
  default: boolean;
  id: number;
  option: string;
  resolver: RealmResolvers;
}

export type RealmResolvers = Array<RealmResolver>;

export interface RealmResolver {
  name: string;
  node: string;
  type: string;
  priority: any;
}

export interface RealmServiceInterface {
  selectedRealms: WritableSignal<string[]>;
  realmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  realmOptions: Signal<string[]>;
  defaultRealmResource: HttpResourceRef<PiResponse<Realms> | undefined>;
  defaultRealm: Signal<string>;
}

@Injectable({
  providedIn: "root"
})
export class RealmService implements RealmServiceInterface {
  private readonly localService: LocalServiceInterface = inject(LocalService);
  private readonly notificationService: NotificationServiceInterface = inject(NotificationService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly contentService: ContentServiceInterface = inject(ContentService);
  selectedRealms = signal<string[]>([]);

  realmResource = httpResource<PiResponse<Realms>>(() => {
    if (
      this.authService.role() === "user" ||
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS) &&
        ![
          ROUTE_PATHS.TOKENS,
          ROUTE_PATHS.USERS,
          ROUTE_PATHS.TOKENS_CONTAINERS_CREATE,
          ROUTE_PATHS.TOKENS_ENROLLMENT
        ].includes(this.contentService.routeUrl()))
    ) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + "/realm/",
      method: "GET",
      headers: this.localService.getHeaders()
    };
  });
  realmOptions = computed(() => {
    const realms = this.realmResource.value()?.result?.value;
    return realms ? Object.keys(realms) : [];
  });

  defaultRealmResource = httpResource<PiResponse<Realms>>(() => {
    if (
      this.authService.role() === "user" ||
      (!this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_DETAILS) &&
        !this.contentService.routeUrl().startsWith(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS) &&
        ![
          ROUTE_PATHS.TOKENS,
          ROUTE_PATHS.USERS,
          ROUTE_PATHS.TOKENS_CONTAINERS_CREATE,
          ROUTE_PATHS.TOKENS_ENROLLMENT
        ].includes(this.contentService.routeUrl()))
    ) {
      return undefined;
    }
    return {
      url: environment.proxyUrl + "/defaultrealm",
      method: "GET",
      headers: this.localService.getHeaders()
    };
  });
  defaultRealm = computed<string>(() => {
    const data = this.defaultRealmResource.value();
    if (data?.result?.value) {
      return Object.keys(data.result?.value)[0] ?? "";
    }
    return "";
  });

  constructor() {
    effect(() => {
      if (this.realmResource.error()) {
        const realmError = this.realmResource.error() as HttpErrorResponse;
        console.error("Failed to get realms.", realmError.message);
        const message = realmError.error?.result?.error?.message || realmError.message;
        this.notificationService.openSnackBar("Failed to get realms. " + message);
      }
    });

    effect(() => {
      if (this.defaultRealmResource.error()) {
        const defaultRealmError = this.defaultRealmResource.error() as HttpErrorResponse;
        console.error("Failed to get default realm.", defaultRealmError.message);
        const message =
          defaultRealmError.error?.result?.error?.message || defaultRealmError.message;
        this.notificationService.openSnackBar("Failed to get default realm. " + message);
      }
    });
  }
}
